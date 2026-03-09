from enum import Enum


type Position = tuple[int, int]
type GridSize = tuple[int, int]
type PlayerID = str

class Direction(Enum):
    NORTH   =   ( 0, -1)
    SOUTH   =   ( 0,  1)
    EAST    =   ( 1,  0)
    WEST    =   (-1,  0)

    def opposite(self) -> Direction:
        match self:
            case Direction.NORTH:
                return Direction.SOUTH
            case Direction.SOUTH:
                return Direction.NORTH
            case Direction.EAST:
                return Direction.WEST
            case Direction.WEST:
                return Direction.EAST
