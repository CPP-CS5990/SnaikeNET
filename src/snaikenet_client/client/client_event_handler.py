from abc import ABC, abstractmethod
from queue import Queue

import loguru

from snaikenet_client.client_data import ClientGameStateFrame


class SnaikenetClientEventHandler(ABC):
    @abstractmethod
    def on_game_state_update(self, frame: ClientGameStateFrame): ...

    @abstractmethod
    def on_game_end(self): ...

    @abstractmethod
    def on_game_restart(self): ...

    @abstractmethod
    def on_game_start(self, viewport_size: tuple[int, int]): ...

    @abstractmethod
    def on_game_about_to_start(self, seconds_until_start: int): ...


class DefaultSnaikenetClientEventHandler(SnaikenetClientEventHandler):
    def on_game_about_to_start(self, seconds_until_start: int):
        pass

    def on_game_end(self):
        pass

    def on_game_restart(self):
        pass

    def on_game_start(self, viewport_size: tuple[int, int]):
        pass

    def on_game_state_update(self, frame: ClientGameStateFrame):
        pass
