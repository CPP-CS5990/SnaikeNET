import pytest

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_server.server.server import SnaikenetServer

@pytest.mark.asyncio
async def test_client_tcp_registration():
    server = SnaikenetServer()
    await server.start()

    client = SnaikenetClient(server_host=server.get_host(), server_port=server.get_port())
    await client.start()

