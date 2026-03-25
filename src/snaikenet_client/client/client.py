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
    _server_port: int
    _on_received_datagram: Callable[ClientGameStateFrame]
    _client_uuid: str | None = None
    _direction: ClientDirection | None = None
    _send_task: asyncio.Task | None = None

    def __init__(self, on_received_datagram: Callable[ClientGameStateFrame], server_port: int = 8888, server_host: str = 'localhost', send_interval_ms: int = 50):
        self._send_interval = send_interval_ms / 1000.0
        self._server_host = server_host
        self._server_port = server_port
        self._on_received_datagram = on_received_datagram

    async def start(self):
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self._UdpProtocol(self))

        await self.connect()

        self._send_task, _ = asyncio.create_task(self._send_direction_loop())

    async def connect(self):
        # TCP Registration:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self._server_host, self._server_port))
            sock.sendall(self._new_connection_initial_tcp())

            response = json.loads(sock.recv(1024).decode().strip())

            uuid = response.get("uuid")

            if response.get("status") != "ok":
                logger.error(f"Failed to connect to server: {response.get('error', 'Unknown error')}")
                raise ConnectionError(f"Failed to connect to server: {response.get('error', 'Unknown error')}")

            if uuid is not None:
                self._client_uuid = uuid
                logger.info(f"Server responded with UUID {uuid}")
            else:
                logger.error("Failed to connect to server: No UUID received")
                raise ConnectionError("Failed to connect to server: No UUID received")

        # UDP hole punching:
        self._udp_transport.sendto(self._client_uuid.encode(), (self._server_host, self._server_port))

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

        self._udp_transport.sendto(protocol.encode_direction(self._direction))
        pass

    def set_direction(self, direction: ClientDirection):
        self._direction = direction


    @staticmethod
    def _to_json(data: dict) -> bytes:
        return json.dumps(data).encode('utf-8')

    def _new_connection_initial_tcp(self):
        return self._to_json({
            "type": "new"
        })

    class _UdpProtocol(asyncio.DatagramProtocol):
        def __init__(self, client: 'SnaikenetClient'):
            self._client = client

        def connection_made(self, transport: asyncio.DatagramTransport):
            self._client._udp_transport = transport

        def datagram_received(self, data: bytes, addr: tuple[str, int]):
            self._client._on_received_datagram(data)
