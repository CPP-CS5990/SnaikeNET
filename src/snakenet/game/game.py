from enum import Enum
from loguru import logger
import numpy as np
from snakenet.game.player import SnakePlayer
import threading
import uuid
import time

type Location = tuple[int, int]
type GridSize = tuple[int, int]

class Game:
    game_state: _GameState
    _start_event: threading.Event
    _stop_signal: bool = False

    def __init__(self, grid_size: GridSize):
        self._start_event = threading.Event()
        self.game_state = _GameState(grid_size)

    def tick(self):
        pass

    def start_game(self):
        logger.debug("Start event received, starting game loop...\n")
        if self.game_state.initialize_game_state():
            self._start_event.set()
            

    def stop_game(self):
        logger.debug("Stop event received, stopping game loop...\n")
        self._start_event.set() # Set the event to unblock the game loop if it's waiting
        self._stop_signal = True
        self.cleanup()
        
    def cleanup(self):
        logger.debug("Cleaning up game resources...\n")
        # Implement any necessary cleanup logic here (e.g., saving game state, closing connections, etc.)

    def not_stopped(self) -> bool:
        return not self._stop_signal

    def wait_for_game_start(self):
        logger.debug("Waiting for start event...\n")
        self._start_event.wait()

    def restart_game(self):
        self = Game(self.game_state.grid_size)
        self._start_event.clear()
        pass

class _TileType(Enum):
    EMPTY = 0
    FOOD = 1
    SNAKE = 2

class TileData:
    tile_type: _TileType
    player_id: str | None

    def __init__(self, tile_type: _TileType = _TileType.EMPTY, player_id: str | None = None):
        self.tile_type = tile_type
        self.player_id = player_id

type PlayerID = str

class _GameState:
    _player_ids: list[PlayerID] = []
    players: dict[PlayerID, SnakePlayer] = {}
    grid_size: GridSize
    grid: list[list[TileData]]

    def __init__(self, grid_size: GridSize):
        self.grid_size = grid_size
        self.grid = [[TileData(tile_type=_TileType.EMPTY, player_id=None) for _ in range(grid_size[1])] for _ in range(grid_size[0])]

    # Adds a new player to the game state
    def add_new_player(self) -> PlayerID:
        player_id = str(uuid.uuid4())
        self._player_ids.append(player_id)
        return player_id

    def delete_player(self, player_id: str) -> bool:
        if player_id not in self.players:
            return False
        del self.players[player_id]
        return True

    # Run right before the game loop starts to initialize the game state
    # Can't run immediately because the game state is going to depend on
    # the number of players that have joined, and we want to allow players 
    # to join before the game starts
    def initialize_game_state(self) -> bool:
        if len(self._player_ids) == 0:
            logger.warning("No players have joined the game, cannot initialize game state.\n")
            return False

        self._initialize_player_positions()
        return True
        # get player positions and create a set of available food locations

    def _initialize_player_positions(self):
        num_players = len(self._player_ids)
        grid_size_padded = (int(self.grid_size[0] * 0.65), int(self.grid_size[1] * 0.65))
        logger.debug(f"Initializing player positions for {num_players} players on a grid of size {self.grid_size} (padded size: {grid_size_padded})...\n")
        center_x = int((self.grid_size[0] - 1) / 2)
        center_y = int((self.grid_size[1] - 1) / 2)
        logger.debug(f"Grid center: ({center_x}, {center_y})\n")
        num_players_per_layer = 6
        number_of_layers = (num_players + num_players_per_layer - 1) / num_players_per_layer
        logger.info(f"Number of players: {num_players}, number of layers needed: {number_of_layers}\n")
        distance_from_center = np.sqrt(((grid_size_padded[0] / 2)-1) ** 2 + ((grid_size_padded[1] / 2)-1) ** 2) / number_of_layers
        distance_stride = distance_from_center
        logger.debug(f"Number of layers: {number_of_layers}, initial distance from center: {distance_from_center}\n")
        for i, player_id in enumerate(self._player_ids):
            if i % num_players_per_layer == 0 and i != 0: # Every n players, we need to move to the next layer
                distance_from_center += distance_stride
            angle = ((1 + 2*i) * np.pi) / num_players_per_layer
            logger.debug(f"Angle for player {i}: {angle:.2f} radians\n")
            x = int(np.round((center_x + distance_from_center * np.cos(angle))))
            y = int(np.round((center_y + distance_from_center * np.sin(angle))))
            self.players[player_id] = SnakePlayer(((int(np.round(x)), int(np.round(y)))))

def create_game_thread_instance(game: Game, tick_interval: float) -> threading.Thread:
    def game_loop():
        logger.info("Game thread started, waiting for start signal...\n")
        game.wait_for_game_start()

        logger.info("Start signal received, entering game loop...\n")
        tick = 0
        start_time = time.time()
        while game.not_stopped():
            threading.Event().wait(tick_interval)
            tick += 1
            logger.debug(f"Tick... {tick} (Elapsed time: {time.time() - start_time:.2f}s)\n")
            logger.debug(f"Ticks per second: {tick / (time.time() - start_time):.2f}\n")
            game.tick()
        # game.cleanup() # TODO: Implement any necessary cleanup logic when the game loop ends
        logger.info("Game thread exiting...\n")

    return threading.Thread(target=game_loop)
