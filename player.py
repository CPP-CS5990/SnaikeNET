# When the snake moves, we should only need to remove the tail and add a new head in the direction of movement.
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


UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3


class SnakePlayer:
    def __init__(self, initial_position: tuple[int, int]):
        # Begins at length 1, so the head and tail are the same tile.
        snake_segment = SnakeBodySegment(initial_position)
        self.head: SnakeBodySegment = snake_segment
        self.tail: SnakeBodySegment = snake_segment

    def move(self, direction: int, grow: bool = False):

        if direction == UP:
            new_head_position = (self.head.position[0], self.head.position[1] - 1)
        elif direction == RIGHT:
            new_head_position = (self.head.position[0] + 1, self.head.position[1])
        elif direction == DOWN:
            new_head_position = (self.head.position[0], self.head.position[1] + 1)
        elif direction == LEFT:
            new_head_position = (self.head.position[0] - 1, self.head.position[1])
        else:
            raise ValueError("Invalid direction")

        self.head = self.head.add_next(new_head_position)

        # If we don't grow, we need to remove the tail segment. If we do grow, we just leave the tail where it is
        # since the new head is added in front of it.
        if not grow:
            self.tail = self.tail.next()
            self.tail.prev_segment = None
