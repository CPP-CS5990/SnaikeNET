import pytest

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.types import ClientDirection
from snaikenet_server.game.types import Direction
from snaikenet_server.server.server import SnaikenetServer
import asyncio


# Test for server-client registration over TCP and UDP hole punching
@pytest.mark.asyncio
async def test_client_tcp_registration():
    # Create and start server
    server = SnaikenetServer(tcp_port=0, udp_port=0)
    await server.start()
    asyncio.create_task(server.server_forever())
    print(f"Server started at {server.get_host()}:{server.get_tcp_port()}")

    # Create and start client
    client = SnaikenetClient(
        server_host=server.get_host(), server_tcp_port=server.get_tcp_port()
    )
    # Client will attempt to connect to server and register over TCP, then receive UDP port for hole punching. We just need to start the client and wait for it to complete the registration process.
    await client.start()
    print(f"Client ID: {client.get_client_id()}")
    print(f"Server Client IDs: {server.get_client_ids()}")
    assert client.get_client_id() in server.get_client_ids()

    await client.stop()
    await server.stop()


# Test for client sending direction updates and server receiving them correctly
@pytest.mark.asyncio
async def test_client_send_and_receive_direction():
    _client_id = None
    _direction = None
    loop = asyncio.get_running_loop()
    received_direction_future = loop.create_future()
    received_client_id_future = loop.create_future()

    def on_received_direction(client_id: str, direction: Direction):
        if received_client_id_future.done() or received_direction_future.done():
            return
        received_direction_future.set_result(direction)
        received_client_id_future.set_result(client_id)

    # Create and start server
    server = SnaikenetServer(
        on_received_direction=on_received_direction, tcp_port=0, udp_port=0
    )
    await server.start()
    asyncio.create_task(server.server_forever())
    print(f"Server started at {server.get_host()}:{server.get_udp_port()}")

    # Create and start client
    client = SnaikenetClient(
        server_host=server.get_host(), server_tcp_port=server.get_tcp_port()
    )
    # Client will attempt to connect to server and register over TCP, then receive UDP port for hole punching. We just need to start the client and wait for it to complete the registration process.
    await client.start()

    # Client sends direction updates every 50ms. We just need to set the direction and the client object will handle the rest.
    client.set_direction(ClientDirection.NORTH)

    rec_client_id = await asyncio.wait_for(received_client_id_future, timeout=5.0)
    rec_direction = await asyncio.wait_for(received_direction_future, timeout=5.0)

    assert rec_client_id == client.get_client_id()
    assert rec_direction == Direction.NORTH

    # Client sends direction updates every 50ms. We just need to set the direction and the client object will handle the rest.
    client.set_direction(ClientDirection.SOUTH)

    received_client_id_future = loop.create_future()
    received_direction_future = loop.create_future()

    rec_client_id = await asyncio.wait_for(received_client_id_future, timeout=5.0)
    rec_direction = await asyncio.wait_for(received_direction_future, timeout=5.0)

    assert rec_client_id == client.get_client_id()
    assert rec_direction == Direction.SOUTH

    await client.stop()
    await server.stop()
