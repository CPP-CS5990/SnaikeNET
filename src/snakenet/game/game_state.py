import uuid

import numpy as np
from loguru import logger

from snakenet.game.grid import Grid, TileData
from snakenet.game.player import SnakePlayer
from snakenet.game.types import PlayerID, GridSize, Position, Direction


class GameState:
    _players: dict[PlayerID, SnakePlayer] = {}
    _kills: dict[PlayerID, PlayerID] = {}
    _dead_players: set[PlayerID] = set()
    _living_players: set[PlayerID] = set()
    _grid: Grid
    _max_num_food: int = 1

    def __init__(self, grid_size: GridSize):
        self._grid = Grid(grid_size)

    def restart_game(self):
        self._grid = Grid(self._grid.get_grid_size())
        old_players = list(self._players.keys())
        self._players.clear()
        self._living_players.clear()
        self._dead_players.clear()
        self._kills.clear()
        for old_player_id in old_players:
            self.add_new_player(old_player_id)
        self.initialize_game_state()

    def kill_player(self, player_id: PlayerID, killer: PlayerID | None = None):
        if killer is None:
            killer = player_id
        player = self._players[player_id]
        if player:
            self._kills[player_id] = killer
            player.kill()
            self._dead_players.add(player_id)
            self._living_players.remove(player_id)
            for position in player:
                self._grid.remove_player_at(
                    position, player_id
                )  # Mark all tiles occupied by the player as empty on the grid
                self._grid.place_food_at(
                    position
                )  # Place food on all tiles occupied by the player
        else:
            logger.warning("Tried killing player that doesn't exist", player_id)

    # Adds a new player to the game state
    def add_new_player(self, player_id: PlayerID | None = None) -> PlayerID:
        if player_id is None:
            player_id = str(uuid.uuid4())
        self._players[player_id] = SnakePlayer(
            (0, 0),  # Temporary position, will be set properly in initialize_game_state
            player_id,
        )
        self._living_players.add(player_id)
        return player_id

    def set_player_direction(self, player_id: PlayerID, player_direction: Direction):
        player = self._players[player_id]
        if player:
            player.set_direction(player_direction)

    def get_player(self, player_id: PlayerID) -> SnakePlayer | None:
        return self._players.get(player_id, None)

    def get_dead_players(self) -> set[PlayerID]:
        return set(self._dead_players)

    def get_living_players(self) -> set[PlayerID]:
        return set(self._living_players)

    def delete_player(self, player_id: PlayerID) -> bool:
        if player_id not in self._players:
            return False
        while len(self._players[player_id]) > 0:
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

    # Handles player moves and kills the player if they hit a wall
    def handle_player_moves(self):
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
                self.kill_player(player_id)
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
                    f"Player {player_id} ate food at position {next_head_position} and grew to length {len(player)}.\n"
                )

            self._grid.add_player_at(
                next_head_position, player_id
            )  # Mark the new head position as occupied by the player on the grid

    def handle_collisions(self):
        # killed -> killer
        killed_players: dict[PlayerID, PlayerID] = {}

        # Detect the killing collisions
        for player_id, player in self._players.items():
            if player.is_dead():
                continue

            if player.collided_with_self():
                killed_players[player_id] = player_id
            else:
                head_position = player.get_head_position()
                other = self._grid.tile_occupied_by_other(player_id, head_position)
                if other is not None:
                    killed_players[player_id] = other

        # Kill based on the detected collisions
        for killed, killer in killed_players.items():
            self.kill_player(killed, killer)

    def handle_food_spawning(self):
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
        self._max_num_food = max(1, len(self._players) * 3)
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
