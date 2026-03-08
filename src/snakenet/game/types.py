from enum import Enum


type Position = tuple[int, int]
type GridSize = tuple[int, int]
type PlayerID = str

class Direction(Enum):
    NORTH   =   ( 0, -1)
    SOUTH   =   ( 0,  1)
    EAST    =   ( 1,  0)
    WEST    =   (-1,  0)

