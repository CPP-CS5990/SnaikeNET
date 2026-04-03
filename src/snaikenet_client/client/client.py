import asyncio
import json

from loguru import logger

from snaikenet_client.client.client_event_handler import (
    SnaikenetClientEventHandler,
    DefaultSnaikenetClientEventHandler,
)
from snaikenet_client.types import ClientDirection
from snaikenet_protocol.protocol import ClientCodec, UdpMsgType


class SnaikenetClient:
    _send_interval: float
    _udp_transport: asyncio.DatagramTransport
    _server_host: str
    _server_tcp_port: int
    _server_udp_port: int | None = None
    _client_uuid: str | None = None
    _direction: ClientDirection | None = None
    _send_task: asyncio.Task | None = None
    _event_handler: SnaikenetClientEventHandler

    def __init__(
        self,
        server_tcp_port: int = 8888,
        server_host: str = "localhost",
        send_interval_ms: int = 50,
        event_handler: SnaikenetClientEventHandler
        | None = DefaultSnaikenetClientEventHandler(),
    ):
        self._send_interval = send_interval_ms / 1000.0
        self._server_host = server_host
        self._server_tcp_port = server_tcp_port
        self._event_handler = event_handler

    async def start(self):
        loop = asyncio.get_running_loop()
        # Attempt to connect to server until successful
        while not hasattr(self, "_udp_transport") or self._udp_transport.is_closing():
            try:
                await self.connect()
            except ConnectionError as e:
                logger.error(f"Failed to connect to server: {e}")

        self._send_task = loop.create_task(self._send_direction_loop())

    async def connect(self):
        # TCP Registration:
        logger.debug(
            f"Attempting to connect to server at {self._server_host}:{self._server_tcp_port} via TCP for registration"
        )
        reader, writer = await asyncio.open_connection(
            self._server_host, self._server_tcp_port
        )
        logger.debug(
            f"Sending registration message to server at {self._server_host}:{self._server_tcp_port}"
        )
        writer.write(ClientCodec.new_connection_initial_tcp_message())
        await writer.drain()

        response = await asyncio.wait_for(reader.read(500), timeout=5.0)
        response_json = json.loads(response.decode("utf-8").strip())

        if response_json.get("status") != "ok":
            logger.error(
                f"Failed to connect to server: {response_json.get('error', 'Unknown error')}"
            )
            raise ConnectionError(
                f"Failed to connect to server: {response_json.get('error', 'Unknown error')}"
            )

        uuid = response_json.get("uuid")
        if uuid is not None:
            self._client_uuid = uuid
            logger.info(f"Server responded with UUID {uuid}")
        else:
            logger.error("Failed to connect to server: No UUID received")
            raise ConnectionError("Failed to connect to server: No UUID received")

        udp_port = response_json.get("udp_port")
        if udp_port is not None:
            logger.info(f"Server responded with UDP port {udp_port} for hole punching")
            loop = asyncio.get_running_loop()
            await loop.create_datagram_endpoint(
                lambda: self._UdpProtocol(self),
                remote_addr=(self._server_host, udp_port),
            )
            self._server_udp_port = udp_port
        else:
            logger.error(
                "Failed to connect to server: No UDP port received for hole punching"
            )
            raise ConnectionError(
                "Failed to connect to server: No UDP port received for hole punching"
            )

        # UDP hole punching:
        logger.debug(
            f"Sending UDP hole-punching datagram to server at {self._server_host}:{self._server_udp_port} with UUID {self._client_uuid}"
        )
        for _ in range(
            5
        ):  # Send multiple times to increase chances of successful hole punching
            await asyncio.sleep(0.1)
            self._udp_transport.sendto(
                ClientCodec.hole_punch_udp_message(self._client_uuid),
            )

        logger.debug(
            f"Waiting for UDP hole-punching response from server at {self._server_host}:{self._server_tcp_port} via TCP"
        )
        response = await asyncio.wait_for(reader.readline(), timeout=5.0)
        response_json = json.loads(response.decode("utf-8").strip())

        if response_json.get("status") == "registered":
            logger.info(
                f"Successfully connected to server with UUID {self._client_uuid}"
            )
            self._server_udp_port = udp_port
        else:
            logger.error(
                f"Failed to connect to server: {response_json.get('error', 'Unknown error')}"
            )
            raise ConnectionError(
                f"Failed to connect to server: {response_json.get('error', 'Unknown error')}"
            )

    async def _send_direction_loop(self):
        try:
            while True:
                await asyncio.sleep(self._send_interval)
                self._send_direction()
        except asyncio.CancelledError:
            logger.info("Direction send loop cancelled")

    def _send_direction(self):
        if self._direction is None:
            return
        if self._udp_transport.is_closing():
            return

        logger.debug(
            f"Sending direction {self._direction} to server at {self._server_host}:{self._server_udp_port} via UDP"
        )
        self._udp_transport.sendto(ClientCodec.encode_direction(self._direction))

    def set_direction(self, direction: ClientDirection):
        self._direction = direction

    def get_client_id(self) -> str | None:
        return self._client_uuid

    class _UdpProtocol(asyncio.DatagramProtocol):
        def __init__(self, client: "SnaikenetClient"):
            self._client = client

        def connection_made(self, transport: asyncio.DatagramTransport):
            logger.info(
                "UDP connection established with server binding to local port {}".format(
                    transport.get_extra_info("sockname")[1]
                )
            )
            self._client._udp_transport = transport

        def datagram_received(self, data: bytes, addr: tuple[str, int]):
            logger.debug(f"Received UDP message from {addr}: {data.hex()}")
            try:
                match(UdpMsgType.peek_msg_type(data)):
                    case UdpMsgType.GAME_START:
                        self._client._event_handler.on_game_start(
                            ClientCodec.decode_game_start(data)
                        )
                    case UdpMsgType.GAME_RESTART:
                        self._client._event_handler.on_game_restart()
                    case UdpMsgType.GAME_STATE_FRAME_UPDATE:
                        self._client._event_handler.on_game_state_update(
                            ClientCodec.decode_player_game_state(data)
                        )
                    case UdpMsgType.GAME_ABOUT_TO_START:
                        self._client._event_handler.on_game_about_to_start(
                            ClientCodec.decode_game_about_to_start(data)
                        )
                    case UdpMsgType.GAME_END:
                        self._client._event_handler.on_game_end()

            except ValueError as _:
                logger.error(
                    f"Failed to decode game state frame from server: {data.hex()}"
                )
                return

    async def stop(self):
        if self._send_task:
            self._send_task.cancel()
        if hasattr(self, "_udp_transport"):
            self._udp_transport.close()
