from enum import Enum
import collections
from loguru import logger
import numpy as np
from snakenet.game.list_dict import ListDict
from snakenet.game.player import SnakePlayer
import threading
import uuid
import time

from snakenet.game.types import PlayerID, Position, GridSize


class Game:
    game_state: GameState
    _start_event: threading.Event
    _stop_signal: bool = False

    def __init__(self, grid_size: GridSize):
        self._start_event = threading.Event()
        self.game_state = GameState(grid_size)

    def tick(self):
        self.game_state.move_players()

    def add_new_player(self) -> PlayerID:
        player_id = self.game_state.add_new_player()
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
        self = Game(self.game_state.get_grid_size())
        self._start_event.clear()
        pass


class TileType(Enum):
    EMPTY = 0
    FOOD = 1
    SNAKE = 2


class TileData:
    tile_type: TileType
    player_ids: list[
        PlayerID
    ]  # Multiple players can occupy the same tile temporarily during collisions

    def __init__(self, tile_type: TileType = TileType.EMPTY):
        self.tile_type = tile_type
        self.player_ids = []

    def add_player(self, player_id: PlayerID):
        if player_id not in self.player_ids:
            self.player_ids.append(player_id)
            self.tile_type = TileType.SNAKE

    def remove_player(self, player_id: PlayerID):
        if player_id in self.player_ids:
            self.player_ids.remove(player_id)
            if len(self.player_ids) == 0:
                self.tile_type = TileType.EMPTY

    def make_food(self):
        self.tile_type = TileType.FOOD
        if len(self.player_ids) > 0:
            logger.critical(
                f"Attempting to place food on a tile that is currently occupied by players: {self.player_ids}!\n"
            )


class Collision:
    collidor: PlayerID  # player id of the collidor
    collidee: PlayerID  # player id of the collidee


class _Grid:
    _grid_size: GridSize
    _grid: list[list[TileData]]
    _available_food_positions: ListDict[Position]
    _num_food_tiles: int = 0

    def __init__(self, grid_size: GridSize):
        self._grid_size = grid_size
        self._grid = [
            [TileData(tile_type=TileType.EMPTY) for _ in range(grid_size[1])]
            for _ in range(grid_size[0])
        ]
        self._available_food_positions = ListDict()

    def remove_player_at(self, position: Position, player_id: PlayerID):
        self._grid[position[0]][position[1]].remove_player(player_id)
        self._available_food_positions.add_item(position)

    def add_player_at(self, position: Position, player_id: PlayerID):
        if self._grid[position[0]][position[1]].tile_type == TileType.FOOD:
            self.remove_food_at(position)
        self._grid[position[0]][position[1]].add_player(player_id)
        self._available_food_positions.remove_item(position)

    def remove_food_at(self, position: Position):
        if self._grid[position[0]][position[1]].tile_type == TileType.FOOD:
            self._grid[position[0]][position[1]].tile_type = TileType.EMPTY
            self._num_food_tiles -= 1
            self._available_food_positions.add_item(position)
        else:
            logger.warning(
                f"Attempting to remove food from a tile that does not contain food at position {position}!\n"
            )

    def food_at(self, position: Position) -> bool:
        return self._grid[position[0]][position[1]].tile_type == TileType.FOOD

    def place_food_at(self, position: Position):
        self._grid[position[0]][position[1]].make_food()
        self._num_food_tiles += 1
        self._available_food_positions.remove_item(position)

    def get_grid_size(self) -> GridSize:
        return self._grid_size

    def get_tile_data(self, position: Position) -> TileData:
        return self._grid[position[0]][position[1]]

    def fill_available_food_positions(self):
        for x in range(self._grid_size[0]):
            for y in range(self._grid_size[1]):
                if self._grid[x][y].tile_type == TileType.EMPTY:
                    self._available_food_positions.add_item((x, y))

    def get_random_available_food_position(self) -> Position | None:
        if len(self._available_food_positions) == 0:
            return None
        return self._available_food_positions.choose_random_item()

    def get_num_food(self) -> int:
        return self._num_food_tiles

    def __iter__(self):
        for row in self._grid:
            for tile in row:
                yield tile


class GameState:
    _players: dict[PlayerID, SnakePlayer] = {}
    _grid: _Grid
    _max_num_food: int = 1

    def __init__(self, grid_size: GridSize):
        self._grid = _Grid(grid_size)

    # Adds a new player to the game state
    def add_new_player(self) -> PlayerID:
        player_id = str(uuid.uuid4())
        self._players[player_id] = SnakePlayer(
            (0, 0),  # Temporary position, will be set properly in initialize_game_state
            player_id,
        )
        return player_id

    def get_player(self, player_id: PlayerID) -> SnakePlayer | None:
        return self._players.get(player_id, None)

    def delete_player(self, player_id: PlayerID) -> bool:
        if player_id not in self._players:
            return False
        while self._players[player_id].get_length() > 0:
            tail_position = self._players[player_id].remove_tail()
            self._grid.remove_player_at(
                tail_position, player_id
            )  # Mark the old tail position as empty on the grid
        del self._players[player_id]
        return True

    def position_outside_grid(self, position: Position) -> bool:
        grid_size_x, grid_size_y = self._grid.get_grid_size()
        return (
            position[0] < 0
            or position[0] >= grid_size_x
            or position[1] < 0
            or position[1] >= grid_size_y
        )

    def move_players(self):
        for player_id, player in self._players.items():
            if player.is_dead():
                continue
            next_head_position = player.add_head()

            # Check for collisions with walls
            if self.position_outside_grid(next_head_position):
                logger.info(
                    f"Player {player_id} collided with wall at position {next_head_position} and died.\n"
                )
                player.remove_head()
                player.kill()
                for position in player:
                    self._grid.remove_player_at(
                        position, player_id
                    )  # Mark all tiles occupied by the player as empty on the grid
                    self._grid.place_food_at(
                        position
                    )  # Place food on all tiles occupied by the player
                continue

            # There is an edge case where if multiple players move into the same food tile,
            # whichever player's move is processed first will eat the food and grow
            # Obviously, if multiple players are moving into the same tile, there will be a collision
            # but 1 player will still get to eat the food and grow which means that players new
            # tail will be collidable for the same tick
            if not self._grid.food_at(next_head_position):
                tail_position = player.remove_tail()
                self._grid.remove_player_at(
                    tail_position, player_id
                )  # Mark the old tail position as empty on the grid
            else:
                logger.info(
                    f"Player {player_id} ate food at position {next_head_position} and grew to length {player.get_length()}.\n"
                )

            self._grid.add_player_at(
                next_head_position, player_id
            )  # Mark the new head position as occupied by the player on the grid

            while self._grid.get_num_food() < self._max_num_food:
                food_position = self._grid.get_random_available_food_position()
                if food_position is not None:
                    self._grid.place_food_at(food_position)
                else:
                    logger.warning("No available positions to place new food!\n")
                    break

    def get_grid_size(self) -> GridSize:
        return self._grid.get_grid_size()

    def get_tile_data(self, position: Position) -> TileData:
        return self._grid.get_tile_data(position)

    def get_grid_iterator(self):
        return iter(self._grid)

    # Run right before the game loop starts to initialize the game state
    # Can't run immediately because the game state is going to depend on
    # the number of players that have joined, and we want to allow players
    # to join before the game starts
    def initialize_game_state(self) -> bool:
        if len(self._players) == 0:
            logger.warning(
                "No players have joined the game, cannot initialize game state.\n"
            )
            return False

        self._initialize_player_positions()
        self._initialize_food_positions()
        return True

    def _initialize_food_positions(self):
        self._grid.fill_available_food_positions()
        self._max_num_food = max(1, len(self._players) // 2)
        for _ in range(self._max_num_food):
            food_position = self._grid.get_random_available_food_position()
            if food_position is not None:
                self._grid.place_food_at(food_position)
            else:
                logger.warning("No available positions to place initial food!\n")
                break

    def _initialize_player_positions(self):
        num_players = len(self._players)
        grid_size_x, grid_size_y = self.get_grid_size()
        grid_size_padded = (
            min(grid_size_x, grid_size_y) * 0.65,
            min(grid_size_x, grid_size_y) * 0.65,
        )
        logger.debug(
            f"Initializing player positions for {num_players} players on a grid of size ({grid_size_x}, {grid_size_y}) (padded size: {grid_size_padded})...\n"
        )

        center_x = int((grid_size_x - 1) / 2)
        center_y = int((grid_size_y - 1) / 2)
        logger.debug(f"Grid center: ({center_x}, {center_y})\n")

        num_players_per_layer = 6

        number_of_layers = (
            num_players + num_players_per_layer - 1
        ) / num_players_per_layer
        logger.info(
            f"Number of players: {num_players}, number of layers needed: {number_of_layers}\n"
        )

        distance_from_center = (
            np.sqrt(
                ((grid_size_padded[0] / 2) - 1) ** 2
                + ((grid_size_padded[1] / 2) - 1) ** 2
            )
            / number_of_layers
        )
        distance_stride = distance_from_center
        logger.debug(
            f"Number of layers: {number_of_layers}, initial distance from center: {distance_from_center}\n"
        )

        for i, player_id in enumerate(self._players):
            if i % num_players_per_layer == 0 and i != 0:
                distance_from_center += distance_stride

            angle = ((1 + 2 * i) * np.pi) / num_players_per_layer
            logger.debug(f"Angle for player {i}: {angle:.2f} radians\n")

            x = int(np.round((center_x + distance_from_center * np.cos(angle))))
            y = int(np.round((center_y + distance_from_center * np.sin(angle))))

            # Update the player position in the game state and mark the grid
            self._players[player_id] = SnakePlayer((x, y), player_id)
            self._grid.add_player_at((x, y), player_id)

    def detect_collisions(self):
        pass


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
