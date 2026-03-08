# When the snake moves, we should only need to remove the tail and add a new head in the direction of movement.
from snakenet.game.types import Direction, PlayerID, Position

class SnakeBodySegment:
    def __init__(
        self,
        position: Position,
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

    def add_next(self, position: Position) -> SnakeBodySegment:
        self.next_segment = SnakeBodySegment(position, prev_segment=self)
        return self.next_segment


class SnakePlayer:
    _head: SnakeBodySegment
    _tail: SnakeBodySegment
    _length: int
    _direction: Direction
    _player_id: PlayerID

    def __init__(self, initial_position: Position, player_id: PlayerID):
        # Begins at length 1, so the head and tail are the same tile.
        snake_segment = SnakeBodySegment(initial_position)
        self._head: SnakeBodySegment = snake_segment
        self._tail: SnakeBodySegment = snake_segment
        self._length = 1
        self._direction = Direction.WEST
        self._player_id = player_id

    def get_head_position(self) -> Position:
        return self._head.position

    def add_head(self) -> Position:
        self._head = self._head.add_next(self.get_next_head_position())
        self._length += 1
        return self._head.position

    def remove_tail(self) -> Position:
        if self._length == 0:
            raise ValueError("Cannot remove tail from an empty snake")
        old_tail_position = self._tail.position
        self._tail = self._tail.next()
        self._tail.prev_segment = None
        self._length -= 1
        return old_tail_position

    def get_tail_position(self) -> Position:
        return self._tail.position

    def get_length(self) -> int:
        return self._length

    def set_direction(self, direction: Direction):
        self._direction = direction

    def get_next_head_position(self) -> Position:
        match self._direction:
            case Direction.NORTH:
                return (self._head.position[0], self._head.position[1] - 1)
            case Direction.WEST:
                return (self._head.position[0] - 1, self._head.position[1])
            case Direction.SOUTH:
                return (self._head.position[0], self._head.position[1] + 1)
            case Direction.EAST:
                return (self._head.position[0] + 1, self._head.position[1])

