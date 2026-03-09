# Source - https://stackoverflow.com/a/15993515
# Posted by Amber, modified by community. See post 'Timeline' for change history
# Retrieved 2026-03-08, License - CC BY-SA 4.0
import random
from typing import Generic, TypeVar

T = TypeVar("T")


class ListDict(Generic[T]):
    def __init__(self):
        self.item_to_position = {}
        self.items = []

    def add_item(self, item: T):
        if item in self.item_to_position:
            return
        self.items.append(item)
        self.item_to_position[item] = len(self.items) - 1

    def remove_item(self, item: T):
        if item not in self.item_to_position:
            return
        position = self.item_to_position.pop(item)
        last_item = self.items.pop()
        if position != len(self.items):
            self.items[position] = last_item
            self.item_to_position[last_item] = position

    def choose_random_item(self):
        return random.choice(self.items)

    def __contains__(self, item: T):
        return item in self.item_to_position

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)
