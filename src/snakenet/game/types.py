from enum import Enum


type Position = tuple[int, int]
type GridSize = tuple[int, int]
type PlayerID = str

class Direction(Enum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3

