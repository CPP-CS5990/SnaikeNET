from enum import Enum

from loguru import logger

from snaikenet.game.list_dict import ListDict
from snaikenet.game.types import GridSize, Position, PlayerID

type GridStructure = list[list[TileData]]


class Grid:
    _grid_size: GridSize
    _grid: GridStructure
    _available_food_positions: ListDict[Position]
    _num_food_tiles: int = 0

    def __init__(self, grid_size: GridSize):
        self._grid_size = grid_size
        self._grid = [
            [TileData(tile_type=TileType.EMPTY) for _ in range(grid_size[1])]
            for _ in range(grid_size[0])
        ]
        self._available_food_positions = ListDict()

    # To award kills, a player needs to be designated as the killer,
    # there may be multiple players at any given position.
    def tile_occupied_by_other(
        self, player_id: PlayerID, position: Position
    ) -> PlayerID | None:
        players = self._grid[position[0]][position[1]].player_ids
        for other_player in players:
            if other_player != player_id:
                return other_player
        return None

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

    # Gets a viewport of the grid centered around a given position
    # When viewport goes out of bounds, it should fill the remaining tiles with TileType.WALL
    def get_viewport(
        self, center_position: Position, distance_from_center: tuple[int, int]
    ) -> GridStructure:
        viewport = []
        for x in range(
            center_position[0] - distance_from_center[0],
            center_position[0] + distance_from_center[0] + 1,
        ):
            row = []
            for y in range(
                center_position[1] - distance_from_center[1],
                center_position[1] + distance_from_center[1] + 1,
            ):
                if 0 <= x < self._grid_size[0] and 0 <= y < self._grid_size[1]:
                    row.append(self._grid[x][y])
                else:
                    wall_tile = TileData(tile_type=TileType.WALL)
                    row.append(wall_tile)
            viewport.append(row)
        logger.debug(
            f"Generated viewport for center position {center_position} with distance {distance_from_center}:\n{self.as_string(viewport)}\n"
        )
        return viewport

    def as_string(self, grid: GridStructure) -> str:
        tile_symbols = {
            TileType.EMPTY: ".",
            TileType.WALL: "#",
            TileType.FOOD: "*",
            TileType.SNAKE: "S",
        }
        rows = []
        for row in grid:
            row_str = ""
            for tile in row:
                row_str += tile_symbols[tile.tile_type]
            rows.append(row_str)
        return "\n".join(rows)


class TileType(Enum):
    EMPTY = 0
    WALL = 1
    FOOD = 2
    SNAKE = 3


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
