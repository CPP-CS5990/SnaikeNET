from enum import IntEnum

type ClientGridStructure = list[list[ClientTileType]]


class ClientTileType(IntEnum):
    EMPTY = 0
    WALL = 1
    FOOD = 2
    SNAKE = 3
    OTHER_SNAKE = 4  # Used for distinguishing the player's own snake from other snakes in the viewport


class ClientDirection(IntEnum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3
