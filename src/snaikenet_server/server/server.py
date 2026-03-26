import asyncio
import json
from uuid import uuid4
from collections.abc import Callable

from loguru import logger


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
    _port: int
    # UUID -> external (host, port)
    _clients: dict[str, tuple[str, int] | None]
    # (host, port) -> UUID, for reverse lookup when receiving UDP datagrams
    _addr_to_uuid: dict[tuple[str, int], str]
    # Temporary storage for pending hole-punching requests: UUID -> Future that will be set with (host, port) when UDP datagram is received
    _pending: dict[str, asyncio.Future[tuple[str, int]]]
    _udp_transport: asyncio.DatagramTransport | None = None
    _on_received_datagram: Callable[[str, bytes]]
    _on_new_client: Callable[[str]]
    _tcp_server: asyncio.AbstractServer | None = None
    _keep_accepting_new_clients: bool

    def __init__(
        self,
        on_received_datagram: Callable[[str, bytes]] = lambda: None,
        on_new_client: Callable[[str]] = lambda: None,
        host="localhost",
        port=8888
    ):
        self._on_received_datagram = on_received_datagram
        self._on_new_client = on_new_client
        self._host = host
        self._port = port
        self._clients = {}  # Track connected clients
        self._addr_to_uuid = {}
        self._keep_accepting_new_clients = True

    def get_host(self) -> str:
        return self._host

    def get_port(self) -> int:
        return self._port

    def set_keep_accepting_new_clients(self, keep_accepting_new_clients: bool):
        self._keep_accepting_new_clients = keep_accepting_new_clients

    # Broadcast message to connected clients using their registered NAT-mapped addresses
    def broadcast(self, client_data: dict[str, bytes]):
        for uuid, data in client_data.items():
            dest = self._clients.get(uuid)
            if dest is not None:
                self._udp_transport = self._udp_transport or None

    async def start(self):
        loop = asyncio.get_running_loop()

        await loop.create_datagram_endpoint(
            lambda: self._UdpProtocol(self), local_addr=(self._host, self._port)
        )
        logger.info(f"UDP server started on {self._host}:{self._port}")

        self._tcp_server = await asyncio.start_server(
            self._handle_registration, self._host, self._port
        )
        logger.info(f"TCP server started on {self._host}:{self._port}")

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
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not raw:
                return

            msg = json.loads(raw.decode().strip())
            req_type = msg.get("type")

            match req_type:
                case "new":
                    if not self._keep_accepting_new_clients:
                        writer.write(self._error_response("Not accepting new clients"))
                        await writer.drain()
                        return
                    client_id = str(uuid4())
                    self._clients[client_id] = None
                    logger.info(
                        f"New client registered with UUID {client_id} from {peer}"
                    )
                case "reconnect":
                    client_id = msg.get("uuid")
                    if client_id not in self._clients:
                        writer.write(self._error_response("Unknown UUID"))
                        await writer.drain()
                        return

                    old_addr = self._clients[client_id]
                    if old_addr:
                        self._addr_to_uuid.pop(old_addr, None)
                        self._clients[client_id] = None

                    logger.info(
                        f"Client with UUID {client_id} is reconnecting from {peer}"
                    )
                case _:
                    writer.write(self._error_response("Invalid request type"))
                    await writer.drain()
                    return

            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._pending[client_id] = fut

            writer.write(self._udp_hole_punch_response(client_id))
            await writer.drain()

            try:
                external_addr: tuple[str, int] = await asyncio.wait_for(
                    fut, timeout=10.0
                )
            except asyncio.TimeoutError:
                await self._pending.pop(client_id, None)

                if req_type == "new":
                    self._clients[client_id] = None
                logger.warning(f"Hole punch timed out for client {client_id}")
                writer.write(self._error_response("Hole punch timed out"))
                await writer.drain()
                return

            # At this point, we have already handled if this is a reconnect and cleared the old address, so we can just register the new address
            self._clients[client_id] = external_addr
            self._addr_to_uuid[external_addr] = client_id
            if req_type == "new":
                self._on_new_client(client_id)
            logger.info(
                f"Client {client_id} hole-punched successfully with external address {external_addr}"
            )
            writer.write(
                self._udp_hole_punch_success_response(client_id, external_addr)
            )
            await writer.drain()

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

    def _udp_hole_punch_response(self, client_id: str) -> bytes:
        return self._to_json(
            {"status": "ok", "uuid": client_id, "port": self._port}
        )

    def _udp_hole_punch_success_response(
        self, client_id: str, external_addr: tuple[str, int]
    ) -> bytes:
        return self._to_json(
            {"status": "ok", "uuid": client_id, "udp_endpoint": list(external_addr)}
        )

    class _UdpProtocol(asyncio.DatagramProtocol):
        def __init__(self, server: "SnaikenetServer"):
            self._server = server

        def connection_made(self, transport: asyncio.DatagramTransport):
            self._server._udp_transport = transport

        def datagram_received(self, data: bytes, addr: tuple[str, int]):
            msg = data.decode().strip()

            # Hole-punch ping
            if msg in self._server._pending:
                fut = self._server._pending.pop(msg)
                if not fut.done():
                    fut.set_result(addr)
                return

            # Regular traffic
            if addr in self._server._addr_to_uuid:
                uuid = self._server._addr_to_uuid[addr]
                self._server._on_received_datagram(uuid, data)
                logger.debug(f"Received UDP message from {uuid} at {addr}: {msg}")
            else:
                logger.debug(f"Received UDP message from unknown address {addr}: {msg}")
