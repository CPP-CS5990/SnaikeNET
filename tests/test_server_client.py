import pytest

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection
from snaikenet_server.game.game_state import PlayerView
from snaikenet_server.game.grid import TileType
from snaikenet_server.game.types import Direction
from snaikenet_server.server.server import SnaikenetServer
import asyncio

from snaikenet_server.server.server_event_handler import SnaikenetServerEventHandler


# Test for server-client registration over TCP and UDP hole punching
@pytest.mark.asyncio
async def test_client_tcp_registration():
    # Create and start server
    server = SnaikenetServer(tcp_port=0, udp_port=0)
    await server.start()
    asyncio.create_task(server.serve_forever())
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
    loop = asyncio.get_running_loop()

    class _TestDirectionUpdate(SnaikenetServerEventHandler):
        _received_direction_future: asyncio.Future
        _received_client_id_future: asyncio.Future

        def __init__(self):
            self.reset_futures()

        def reset_futures(self):
            self._received_direction_future = loop.create_future()
            self._received_client_id_future = loop.create_future()

        def futures_done(self) -> bool:
            return (
                self._received_direction_future.done()
                and self._received_client_id_future.done()
            )

        def on_new_client_connect(self, client_id: str, spectator: bool = False):
            pass

        def on_client_disconnect(self, client_id: str):
            pass

        def on_receive_direction(self, client_id: str, direction: Direction):
            if (
                self._received_client_id_future.done()
                or self._received_direction_future.done()
            ):
                return
            self._received_direction_future.set_result(direction)
            self._received_client_id_future.set_result(client_id)

        async def wait_for_futures(self, timeout: float = 5.0) -> tuple[str, Direction]:
            result = (
                await asyncio.wait_for(
                    self._received_client_id_future, timeout=timeout
                ),
                await asyncio.wait_for(
                    self._received_direction_future, timeout=timeout
                ),
            )
            return result

    event_handler = _TestDirectionUpdate()
    # Create and start server
    server = SnaikenetServer(event_handler=event_handler, tcp_port=0, udp_port=0)
    await server.start()
    asyncio.create_task(server.serve_forever())
    print(f"Server started at {server.get_host()}:{server.get_udp_port()}")

    # Create and start client
    client = SnaikenetClient(
        server_host=server.get_host(), server_tcp_port=server.get_tcp_port()
    )
    # Client will attempt to connect to server and register over TCP, then receive UDP port for hole punching. We just need to start the client and wait for it to complete the registration process.
    await client.start()

    # Client sends direction updates every 50ms. We just need to set the direction and the client object will handle the rest.
    client.set_direction(ClientDirection.NORTH)

    received_client_id, received_direction = await event_handler.wait_for_futures()
    event_handler.reset_futures()

    assert received_client_id == client.get_client_id()
    assert received_direction == Direction.NORTH

    # Client sends direction updates every 50ms. We just need to set the direction and the client object will handle the rest.
    client.set_direction(ClientDirection.SOUTH)

    received_client_id, received_direction = await event_handler.wait_for_futures()

    assert received_client_id == client.get_client_id()
    assert received_direction == Direction.SOUTH
    event_handler.reset_futures()

    await client.stop()
    await server.stop()


@pytest.mark.asyncio
async def test_server_broadcast():
    loop = asyncio.get_running_loop()
    # Create and start server
    server = SnaikenetServer(tcp_port=0, udp_port=0)
    await server.start()
    asyncio.create_task(server.serve_forever())
    print(f"Server started at {server.get_host()}:{server.get_tcp_port()}")

    class _TestBroadcastEventHandler(SnaikenetClientEventHandler):
        def on_game_about_to_start(self, seconds_until_start: int):
            pass

        def on_game_end(self):
            pass

        def on_game_restart(self):
            pass

        def on_game_start(self, viewport_size: tuple[int, int]):
            pass

        _received_broadcast_future: asyncio.Future[ClientGameStateFrame]

        def on_game_state_update(self, frame: ClientGameStateFrame):
            if self._received_broadcast_future.done():
                return
            self._received_broadcast_future.set_result(frame)

        def __init__(self):
            self._received_broadcast_future = loop.create_future()

        async def wait_for_broadcast(
            self, timeout: float = 5.0
        ) -> ClientGameStateFrame:
            result = await asyncio.wait_for(
                self._received_broadcast_future, timeout=timeout
            )
            return result

        def reset_future(self):
            self._received_broadcast_future = loop.create_future()

    event_handler = _TestBroadcastEventHandler()
    # Create and start client
    client = SnaikenetClient(
        server_host=server.get_host(),
        server_tcp_port=server.get_tcp_port(),
        event_handler=event_handler,
    )
    await client.start()
    client_id = client.get_client_id()

    assert client_id is not None

    # Server broadcasts a message to all clients
    player_view = PlayerView(
        viewport_size=(3, 3),
        viewport=bytes(
            [
                TileType.SNAKE,
                TileType.EMPTY,
                TileType.FOOD,
                TileType.EMPTY,
                TileType.SNAKE,
                TileType.EMPTY,
                TileType.FOOD,
                TileType.EMPTY,
                TileType.SNAKE,
            ]
        ),
        kills=0,
        is_alive=True,
        length=1,
        is_spectating=False,
    )

    await server.broadcast_game_state_frames({client_id: player_view}, 0)

    broadcast = await event_handler.wait_for_broadcast()
    event_handler.reset_future()

    assert broadcast.sequence_number == 0
    assert broadcast.player_length == 1
    assert broadcast.is_alive == True

    player_view.is_alive = False

    await server.broadcast_game_state_frames({client_id: player_view}, 1)
    broadcast = await event_handler.wait_for_broadcast()
    event_handler.reset_future()

    assert broadcast.sequence_number == 1
    assert broadcast.player_length == 1
    assert broadcast.is_alive == False

    # We would need to implement a way for the client to receive broadcast messages in order to test this properly. For now, we will just assume that if the code reaches this point without errors, the broadcast was successful.

    await client.stop()
    await server.stop()


@pytest.mark.asyncio
async def test_spectator_client_registration():
    """A client connecting with spectator=True should trigger on_new_client_connect with spectator=True
    and should not be treated as a regular player."""
    loop = asyncio.get_running_loop()

    class _SpectatorEventHandler(SnaikenetServerEventHandler):
        def __init__(self):
            self._connect_future: asyncio.Future[tuple[str, bool]] = (
                loop.create_future()
            )

        def on_new_client_connect(self, client_id: str, spectator: bool = False):
            if not self._connect_future.done():
                self._connect_future.set_result((client_id, spectator))

        def on_client_disconnect(self, client_id: str):
            pass

        def on_receive_direction(self, client_id: str, direction: Direction):
            pass

    event_handler = _SpectatorEventHandler()
    server = SnaikenetServer(event_handler=event_handler, tcp_port=0, udp_port=0)
    await server.start(clean_idle_clients=False)
    asyncio.create_task(server.serve_forever())

    client = SnaikenetClient(
        server_host=server.get_host(),
        server_tcp_port=server.get_tcp_port(),
        is_spectator=True,
    )
    await client.start()

    connected_id, was_spectator = await asyncio.wait_for(
        event_handler._connect_future, timeout=5.0
    )

    assert connected_id == client.get_client_id()
    assert was_spectator is True
    assert client.get_client_id() in server.get_client_ids()

    await client.stop()
    await server.stop()


@pytest.mark.asyncio
async def test_idle_client_cleanup():
    """A client that stops sending heartbeats should be removed after client_timeout_seconds.
    A client that keeps sending heartbeats should remain connected."""
    loop = asyncio.get_running_loop()

    class _DisconnectEventHandler(SnaikenetServerEventHandler):
        def __init__(self):
            self._disconnect_future: asyncio.Future[str] = loop.create_future()

        def on_new_client_connect(self, client_id: str, spectator: bool = False):
            pass

        def on_client_disconnect(self, client_id: str):
            if not self._disconnect_future.done():
                self._disconnect_future.set_result(client_id)

        def on_receive_direction(self, client_id: str, direction: Direction):
            pass

    event_handler = _DisconnectEventHandler()
    timeout_seconds = 0.5
    server = SnaikenetServer(
        event_handler=event_handler,
        tcp_port=0,
        udp_port=0,
        client_timeout_seconds=timeout_seconds,
    )
    await server.start(clean_idle_clients=True)
    asyncio.create_task(server.serve_forever())

    # Connect two clients: one will keep heartbeating, the other will go silent
    active_client = SnaikenetClient(
        server_host=server.get_host(),
        server_tcp_port=server.get_tcp_port(),
    )
    idle_client = SnaikenetClient(
        server_host=server.get_host(),
        server_tcp_port=server.get_tcp_port(),
    )
    await active_client.start()
    await idle_client.start()

    assert active_client.get_client_id() in server.get_client_ids()
    assert idle_client.get_client_id() in server.get_client_ids()

    # Stop the idle client's heartbeat so it becomes idle
    idle_client._heartbeat_task.cancel()

    # Wait for the idle client to be cleaned up
    disconnected_id = await asyncio.wait_for(
        event_handler._disconnect_future, timeout=timeout_seconds + 2
    )

    assert disconnected_id == idle_client.get_client_id()
    assert idle_client.get_client_id() not in server.get_client_ids()
    # Active client should still be connected
    assert active_client.get_client_id() in server.get_client_ids()

    await active_client.stop()
    await idle_client.stop()
    await server.stop()
