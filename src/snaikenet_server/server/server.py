import asyncio
import json
from uuid import uuid4

from loguru import logger

from snaikenet_protocol import protocol
from snaikenet_server.game.game_state import PlayerView
from snaikenet_server.server.connected_clients import ConnectedClients
from snaikenet_server.server.server_event_handler import SnaikenetServerEventHandler, DefaultSnaikenetServerEventHandler


class SnaikenetServer:
    """
    Server for Snaikenet game
    TCP Registration:
        1) Client: sends registration request over TCP {"type": "new"}
        2) Server: generates UUID and ACKs back to client with UUID and UDP port to use for hole punching
        3) Client: sends a UDP datagram containing the UUID to the server's UDP port to complete registration
        4) Server: server reads NAT-mapped addr and registers the client with the UUID and NAT-mapped addr for future communication

    TCP Reconnection:
        1) Client: sends reconnection request over TCP with UUID {"type": "reconnect", "uuid": "<client_uuid>"}
        2) Server: validates UUID, responds with UDP port
        3) Client: Sends UDP datagram containing the UUID
        4) Server: updates client's NAT-mapped addr for future communication
    """

    _host: str
    _tcp_port: int
    _udp_port: int
    _connected_clients: ConnectedClients
    # Temporary storage for pending hole-punching requests: UUID -> Future that will be set with (host, port) when UDP datagram is received
    _pending_clients: dict[str, asyncio.Future[tuple[str, int]]]
    _keep_accepting_new_clients: bool
    _udp_transport: asyncio.DatagramTransport | None = None
    _tcp_server: asyncio.Server | None = None
    _event_handler: SnaikenetServerEventHandler

    def __init__(
        self,
        host="localhost",
        tcp_port=8888,
        udp_port=8888,
        event_handler: SnaikenetServerEventHandler = DefaultSnaikenetServerEventHandler(),
    ):
        self._host = host
        self._tcp_port = tcp_port
        self._udp_port = udp_port
        self._connected_clients = ConnectedClients()
        self._keep_accepting_new_clients = True
        self._pending_clients = {}
        self._event_handler = event_handler

    def get_host(self) -> str:
        return self._host

    def get_tcp_port(self) -> int:
        return self._tcp_port

    def get_udp_port(self) -> int:
        return self._udp_port

    def set_keep_accepting_new_clients(self, keep_accepting_new_clients: bool):
        self._keep_accepting_new_clients = keep_accepting_new_clients

    def broadcast_game_state_frames(
        self, client_frames: dict[str, PlayerView], sequence_number: int
    ):
        for uuid, frame in client_frames.items():
            self.broadcast_game_state_frame(uuid, frame, sequence_number)

    def broadcast_game_state_frame(
        self, client_id: str, client_frame: PlayerView, sequence_number: int
    ):
        dest = self._connected_clients.get_client_by_id(client_id)
        if dest is not None:
            self._udp_transport = self._udp_transport or None
            self._udp_transport.sendto(
                protocol.encode_player_game_state(client_id, client_frame, sequence_number),
                dest.get_addr(),
            )

    async def start(self):
        loop = asyncio.get_running_loop()

        self._tcp_server = await asyncio.start_server(
            self._handle_registration, self._host, self._tcp_port
        )
        self._tcp_port = self._tcp_server.sockets[0].getsockname()[1]
        logger.info(f"TCP server started on {self._host}:{self._tcp_port}")

        await loop.create_datagram_endpoint(
            lambda: self._UdpProtocol(self), local_addr=(self._host, self._udp_port)
        )
        self._udp_port = self._udp_transport.get_extra_info("socket").getsockname()[1]
        logger.info(f"UDP server started on {self._host}:{self._udp_port}")

    def get_clients_str(self) -> str:
        return "Clients connected: " + ", ".join(
            f"{client.get_id()} at {client.get_addr()}"
            for client in self._connected_clients.get_clients()
        )

    def get_client_ids(self) -> list[str]:
        return [client.get_id() for client in self._connected_clients.get_clients()]

    async def server_forever(self):
        if self._tcp_server is None:
            raise RuntimeError("Server not started yet")
        async with self._tcp_server:
            await self._tcp_server.serve_forever()

    async def stop(self):
        if self._udp_transport:
            logger.info("Stopping UDP server...")
            self._udp_transport.close()
        if self._tcp_server:
            logger.info("Stopping TCP server...")
            self._tcp_server.close()
            await self._tcp_server.wait_closed()
        logger.info("Snaikenet server stopped.")

    async def _handle_registration(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        peer = writer.get_extra_info("peername")
        logger.info(f"Received connection from {peer}")

        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not raw:
                return

            logger.debug(
                f"Received registration request from {peer}: {raw.decode().strip()}"
            )

            msg = json.loads(raw.decode().strip())
            req_type = msg.get("type")

            match req_type:
                case "new":
                    if not self._keep_accepting_new_clients:
                        writer.write(self._error_response("Not accepting new clients"))
                        await writer.drain()
                        return
                    client_id = str(uuid4())
                    self._connected_clients.pop_client_by_id(
                        client_id
                    )  # Clear any old registration with same UUID just in case, should be very unlikely
                    logger.debug(
                        f"New client registering with UUID {client_id} from TCP {peer}"
                    )
                case "reconnect":
                    client_id = msg.get("uuid")
                    if not self._connected_clients.has_client_id(client_id):
                        writer.write(self._error_response("Unknown UUID: Cannot reconnect"))
                        await writer.drain()
                        return

                    self._connected_clients.pop_client_by_id(client_id)
                    logger.info(
                        f"Client with UUID {client_id} is reconnecting from {peer}"
                    )
                case _:
                    writer.write(self._error_response("Invalid request type"))
                    await writer.drain()
                    return

            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._pending_clients[client_id] = fut

            writer.write(self._udp_hole_punch_request(client_id))
            logger.debug(
                f"Sending hole punch request to client {client_id} at TCP {peer}"
            )
            await writer.drain()

            try:
                external_addr: tuple[str, int] = await asyncio.wait_for(
                    fut, timeout=10.0
                )
            except asyncio.TimeoutError:
                await self._pending_clients.pop(client_id, None)

                if req_type == "new":
                    self._connected_clients.pop_client_by_id(
                        client_id
                    )  # Clear any registration for this client since hole punch failed
                logger.warning(f"Hole punch timed out for client {client_id}")
                writer.write(self._error_response("Hole punch timed out"))
                await writer.drain()
                return

            # At this point, we have already handled if this is a reconnect and cleared the old address, so we can just register the new address
            self._connected_clients.register_client(client_id, external_addr)
            if req_type == "new":
                self._event_handler.on_new_client_connect(client_id)

            logger.info(
                f"Client {client_id} hole-punched successfully with external address {external_addr}. Sending registration success response to TCP {peer}"
            )
            writer.write(self._udp_hole_punch_success_response())
            await asyncio.wait_for(writer.drain(), timeout=5.0)

        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Invalid registration request from {peer}: {e}")
            writer.write(self._error_response("Invalid registration request"))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    def _to_json(data: dict) -> bytes:
        return json.dumps(data).encode() + b"\n"

    def _error_response(self, reason: str) -> bytes:
        return self._to_json({"status": "error", "reason": reason})

    def _udp_hole_punch_request(self, client_id: str) -> bytes:
        return self._to_json(
            {"status": "ok", "uuid": client_id, "udp_port": self._udp_port}
        )

    def _udp_hole_punch_success_response(self) -> bytes:
        return self._to_json({"status": "registered"})

    class _UdpProtocol(asyncio.DatagramProtocol):
        def __init__(self, server: "SnaikenetServer"):
            self._server = server

        def connection_made(self, transport: asyncio.DatagramTransport):
            self._server._udp_transport = transport

        def datagram_received(self, data: bytes, addr: tuple[str, int]):
            msg = data.decode().strip()
            msg_json = json.loads(msg)

            msg_type = msg_json.get("type")

            if msg_type == "hole_punch":
                client_id = msg_json.get("uuid")
                # Hole-punch ping
                if client_id in self._server._pending_clients:
                    logger.info(
                        f"Received hole punch ping from {addr} for client {client_id}"
                    )
                    fut = self._server._pending_clients.pop(client_id)
                    if not fut.done():
                        fut.set_result(addr)
                    return
                elif self._server._connected_clients.has_client_id(client_id):
                    logger.debug(
                        f"Received hole punch for existing client {client_id} from {addr}. Ignoring since client is already registered."
                    )
                    return
            elif msg_type == "direction":
                if self._server._connected_clients.has_client_addr(addr):
                    client = self._server._connected_clients.get_client_by_addr(addr)
                    self._server._connected_clients.touch_client_by_id(client.get_id())
                    self._server._event_handler.on_receive_direction(
                        client.get_id(), protocol.decode_direction(data)
                    )
                else:
                    logger.debug(
                        f"Received UDP message from unknown address {addr}: {msg}"
                    )
