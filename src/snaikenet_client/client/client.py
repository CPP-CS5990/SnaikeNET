import asyncio
import json
import socket
from collections.abc import Callable
from loguru import logger

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection
from snaikenet_protocol import protocol


class SnaikenetClient:
    _send_interval: float
    _udp_transport: asyncio.DatagramTransport
    _server_host: str
    _server_tcp_port: int
    _server_udp_port: int | None = None
    _on_receive_game_state_frame: Callable[[ClientGameStateFrame]]
    _client_uuid: str | None = None
    _direction: ClientDirection | None = None
    _send_task: asyncio.Task | None = None

    def __init__(
        self,
        on_receive_game_state_frame: Callable[[ClientGameStateFrame]] = lambda _: None,
        server_tcp_port: int = 8888,
        server_host: str = "localhost",
        send_interval_ms: int = 50,
    ):
        self._send_interval = send_interval_ms / 1000.0
        self._server_host = server_host
        self._server_tcp_port = server_tcp_port
        self._on_receive_game_state_frame = on_receive_game_state_frame

    async def start(self):
        loop = asyncio.get_running_loop()
        await self.connect()
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
        writer.write(self._new_connection_initial_tcp())
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
                self._to_json({"type": "hole_punch", "uuid": self._client_uuid})
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
        self._udp_transport.sendto(protocol.encode_direction(self._direction))

    def set_direction(self, direction: ClientDirection):
        self._direction = direction

    def get_client_id(self) -> str | None:
        return self._client_uuid

    @staticmethod
    def _to_json(data: dict) -> bytes:
        return json.dumps(data).encode() + b"\n"

    def _new_connection_initial_tcp(self):
        return self._to_json({"type": "new"})

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
            logger.debug(f"Received UDP message from {addr}: {data.decode().strip()}")
            try:
                game_state_frame = protocol.decode_player_game_state(data)
                self._client._on_receive_game_state_frame(game_state_frame)
            except ValueError as _:
                logger.error(
                    f"Failed to decode game state frame from server: {data.decode().strip()}"
                )
                return

    async def stop(self):
        if self._send_task:
            self._send_task.cancel()
        if hasattr(self, "_udp_transport"):
            self._udp_transport.close()
