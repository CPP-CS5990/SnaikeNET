from abc import ABC, abstractmethod

import loguru

from snaikenet_client.client_data import ClientGameStateFrame


class SnaikenetClientEventHandler(ABC):
    @abstractmethod
    def on_receive_game_state_frame(self, frame: ClientGameStateFrame): ...


class DefaultSnaikenetClientEventHandler(SnaikenetClientEventHandler):
    def on_receive_game_state_frame(self, frame: ClientGameStateFrame):
        loguru.logger.warning("Not implemented: on_receive_game_state_frame")
        pass