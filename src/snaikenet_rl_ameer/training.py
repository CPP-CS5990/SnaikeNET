import numpy as np

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection


class AgentGameStateFrame:
    def __init__(
            self,
            frame: ClientGameStateFrame
    ):
        self.is_spectating = frame.is_spectating
        self.sequence_number = frame.sequence_number
        self.player_length: int = frame.player_length
        self.num_kills: int = frame.num_kills
        self.is_alive: bool = frame.is_alive

        self.grid_data: np.typing.NDArray[np.uint8] = np.array(frame.grid_data, dtype=np.uint8)


class ExperienceReplayBuffer:
    def __init__(self, state1: AgentGameStateFrame, action: ClientDirection, reward: float, state2: AgentGameStateFrame):
        self.state1 = state1
        self.action = action
        self.reward = reward
        self.state2 = state2
