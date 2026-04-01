from abc import ABC, abstractmethod

from snaikenet_server.game.types import Direction


class SnaikenetServerEventHandler(ABC):
    @abstractmethod
    def on_new_client_connect(self, client_id: str): ...

    @abstractmethod
    def on_client_disconnect(self, client_id: str): ...

    @abstractmethod
    def on_receive_direction(self, client_id: str, direction: Direction): ...


class DefaultSnaikenetServerEventHandler(SnaikenetServerEventHandler):
    def on_new_client_connect(self, client_id: str):
        pass

    def on_client_disconnect(self, client_id: str):
        pass

    def on_receive_direction(self, client_id: str, direction: Direction):
        pass
