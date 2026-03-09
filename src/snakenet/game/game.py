import collections
from loguru import logger

from snakenet.game.game_state import GameState
import threading
import time

from snakenet.game.types import PlayerID, GridSize


class Game:
    game_state: GameState
    _start_event: threading.Event
    _stop_signal: bool = False

    def __init__(self, grid_size: GridSize):
        self._start_event = threading.Event()
        self.game_state = GameState(grid_size)

    def tick(self):
        self.game_state.move_players()

    def add_new_player(self, player_id: PlayerID | None = None) -> PlayerID:
        player_id = self.game_state.add_new_player(player_id)
        logger.info(f"Added new player with ID: {player_id}\n")
        return player_id

    def start_game(self):
        logger.debug("Start event received, starting game loop...\n")
        if self.game_state.initialize_game_state():
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
        self.game_state.restart_game()
        self._start_event.clear()


def create_game_thread_instance(game: Game, tick_interval: float) -> threading.Thread:
    def game_loop():
        logger.info("Game thread started, waiting for start signal...\n")
        game.wait_for_game_start()

        logger.info("Start signal received, entering game loop...\n")
        tick = 0
        next_tick_time = time.perf_counter()
        tick_times = collections.deque(
            maxlen=100
        )  # Keep track of the last 100 tick times for performance monitoring
        while game.is_running():
            tick_start = time.perf_counter()
            game.tick()
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
