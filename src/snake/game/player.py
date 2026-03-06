# When the snake moves, we should only need to remove the tail and add a new head in the direction of movement.
from enum import Enum


class SnakeBodySegment:
    def __init__(
        self,
        position: tuple[int, int],
        prev_segment: SnakeBodySegment | None = None,
        next_segment: SnakeBodySegment | None = None,
    ):
        self.position = position
        self.prev_segment = prev_segment
        self.next_segment = next_segment

        if prev_segment is not None:
            prev_segment.next_segment = self

        if next_segment is not None:
            next_segment.prev_segment = self

    def is_head(self) -> bool:
        return self.next_segment is None

    def is_tail(self) -> bool:
        return self.prev_segment is None

    def next(self) -> SnakeBodySegment:
        if self.next_segment is None:
            raise ValueError("This segment has no next segment")
        return self.next_segment

    def prev(self) -> SnakeBodySegment | None:
        if self.prev_segment is None:
            raise ValueError("This segment has no previous segment")
        return self.prev_segment

    def add_next(self, position: tuple[int, int]) -> SnakeBodySegment:
        self.next_segment = SnakeBodySegment(position, prev_segment=self)
        return self.next_segment


class Direction(Enum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3

class SnakePlayer:
    _head: SnakeBodySegment
    _tail: SnakeBodySegment
    _length: int
    _direction: Direction

    def __init__(self, initial_position: tuple[int, int]):
        # Begins at length 1, so the head and tail are the same tile.
        snake_segment = SnakeBodySegment(initial_position)
        self._head: SnakeBodySegment = snake_segment
        self._tail: SnakeBodySegment = snake_segment
        self._length = 1
        self._direction = Direction.WEST

    def get_head_position(self) -> tuple[int, int]:
        return self._head.position

    def get_tail_position(self) -> tuple[int, int]:
        return self._tail.position

    def get_length(self) -> int:
        return self._length

    def set_direction(self, direction: Direction):
        self._direction = direction

    def initialize_position(self, position: tuple[int, int]):
        self._head.position = position
        self._tail.position = position

    def move(self, grow: bool = False):

        match self._direction:
            case Direction.NORTH:
                new_head_position = (self._head.position[0], self._head.position[1] - 1)
            case Direction.WEST:
                new_head_position = (self._head.position[0] + 1, self._head.position[1])
            case Direction.SOUTH:
                new_head_position = (self._head.position[0], self._head.position[1] + 1)
            case Direction.EAST:
                new_head_position = (self._head.position[0] - 1, self._head.position[1])

        self._head = self._head.add_next(new_head_position)

        # If we don't grow, we need to remove the tail segment. If we do grow, we just leave the tail where it is
        # since the new head is added in front of it.
        if not grow:
            self._tail = self._tail.next()
            self._tail.prev_segment = None
        else:
            self._length += 1
