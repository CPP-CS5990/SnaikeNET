from snaikenet_client.client.client import SnaikenetClient
from snaikenet_server.server.server import SnaikenetServer


def test_client_tcp_registration():
    server = SnaikenetServer()
    server.start()

    client = SnaikenetClient(server_host=server.get_host(), server_port=server.get_port())
    client.start()

    assert client._client_uuid in server._clients