import collections
from loguru import logger

from snaikenet_server.game.game_state import GameState, PlayerView
from snaikenet_protocol import protocol
import threading
import time

from snaikenet_server.game.grid import GridStructure
from snaikenet_server.game.types import PlayerID, GridSize, Direction
from snaikenet_server.server.server import SnaikenetServer


class Game:
    _game_state: GameState
    _start_event: threading.Event
    _stop_signal: bool = False

    def __init__(
        self,
        grid_size: GridSize,
        viewport_distance_from_center: tuple[int, int] = (14, 14),
    ):
        self._start_event = threading.Event()
        self._game_state = GameState(grid_size, viewport_distance_from_center)

    def tick(self):
        self._game_state.handle_player_moves()
        self._game_state.handle_collisions()
        self._game_state.handle_food_spawning()

    def add_new_player(self, player_id: PlayerID | None = None) -> PlayerID:
        player_id = self._game_state.add_new_player(player_id)
        logger.info(f"Added new player with ID: {player_id}\n")
        return player_id

    def start_game(self):
        logger.debug("Start event received, starting game loop...\n")
        if self._game_state.initialize_game_state():
            self._start_event.set()
        else:
            logger.error("Failed to initialize game state, cannot start game loop.\n")

    def stop_game(self):
        logger.debug("Stop event received, stopping game loop...\n")
        self._start_event.set()  # Set the event to unblock the game loop if it's waiting
        self._stop_signal = True
        self.cleanup()

    def cleanup(self):
        logger.debug("Cleaning up game resources...\n")
        # Implement any necessary cleanup logic here (e.g., saving game state, closing connections, etc.)

    def is_running(self) -> bool:
        return not self._stop_signal

    def wait_for_game_start(self):
        logger.debug("Waiting for start event...\n")
        self._start_event.wait()

    def restart_game(self):
        self._game_state.restart_game()
        self._start_event.clear()

    def get_grid_iterator(self):
        return self._game_state.get_grid_iterator()

    def set_player_direction(self, player_id: PlayerID, direction: Direction):
        self._game_state.set_player_direction(player_id, direction)

    def get_dead_players(self) -> set[PlayerID]:
        return self._game_state.get_dead_players()

    def get_living_players(self) -> set[PlayerID]:
        return self._game_state.get_living_players()

    def get_grid_size(self) -> GridSize:
        return self._game_state.get_grid_size()

    def get_player_viewport(self, player_id: PlayerID) -> GridStructure:
        return self._game_state.get_player_viewport(player_id)

    def get_player_viewports(self) -> dict[PlayerID, GridStructure]:
        return self._game_state.get_player_viewports()

    def get_player_states(self) -> dict[PlayerID, PlayerView]:
        return self._game_state.get_player_states()

    def get_player_viewport_iterator(self, player_id: PlayerID):
        viewport = self.get_player_viewport(player_id)
        for row in viewport:
            for tile in row:
                yield tile


def create_game_thread_instance(game: Game, tick_interval: float) -> threading.Thread:
    def game_loop():
        game_lock = threading.Lock()

        def on_received_datagram(client_id: str, data: bytes):
            # Handle incoming datagram from clients (e.g., player input)
            logger.debug(f"Received datagram from client {client_id}: {data}\n")
            direction = protocol.decode_direction(data)
            if direction is not None:
                with game_lock:
                    game.set_player_direction(
                        client_id, direction
                    )  # Placeholder, replace with actual direction decoding
            else:
                logger.debug(
                    f"Received invalid datagram from client {client_id}: {data}\n"
                )

        def on_player_connected(client_id: str):
            logger.info(f"Player connected with client ID: {client_id}\n")
            with game_lock:
                game.add_new_player(client_id)

        server = SnaikenetServer(on_received_datagram, on_player_connected)
        logger.info("Game thread started, waiting for start signal...\n")
        game.wait_for_game_start()
        # Once the game starts, stop accepting new clients
        server.set_keep_accepting_new_clients(False)

        logger.info("Start signal received, entering game loop...\n")
        tick = 0
        next_tick_time = time.perf_counter()
        tick_times = collections.deque(
            maxlen=100
        )  # Keep track of the last 100 tick times for performance monitoring

        while game.is_running():
            tick_start = time.perf_counter()
            with game_lock:
                game.tick()

            player_states = game.get_player_states()
            player_states_encoded = protocol.encode_game_state(player_states)
            server.broadcast(player_states_encoded)
            tick += 1
            tick_times.append(time.perf_counter() - tick_start)

            next_tick_time += tick_interval
            sleep_duration = next_tick_time - time.perf_counter()

            if sleep_duration > 0:
                threading.Event().wait(sleep_duration)
            else:
                logger.warning(f"Tick {tick} overran by {-sleep_duration:.4f}s\n")

            if tick % 100 == 0:
                avg_tick_ms = (sum(tick_times) / len(tick_times)) * 1000
                real_tps = 1.0 / (tick_interval + (sum(tick_times) / len(tick_times)))
                logger.debug(
                    f"Tick {tick} | avg tick time: {avg_tick_ms:.2f}ms | real TPS: {real_tps:.2f}\n"
                )

        game.cleanup()
        logger.info("Game thread exiting...\n")

    return threading.Thread(target=game_loop)
