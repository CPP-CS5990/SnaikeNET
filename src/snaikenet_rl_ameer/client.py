from collections import deque

import torch
from torchrl.data import ReplayBuffer, LazyTensorStorage

from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection
from snaikenet_rl_ameer.training import AgentGameStateFrame, ExperienceReplayBuffer
from snaikenet_rl_ameer.reward import compute_reward
import numpy as np


class SnaikenetClientAgentEventHandler(SnaikenetClientEventHandler):
    def __init__(self, buffer_size: int, device: torch.device | None):
        super().__init__()
        self._prev_state: AgentGameStateFrame | None = None
        self._prev_action = None
        self._experience_replay_buffer: ReplayBuffer = ReplayBuffer(
            storage=LazyTensorStorage(buffer_size, device=device if device is not None else torch.device('cpu'))
        )
        self._trainer =

    def on_game_state_update(self, frame: ClientGameStateFrame):
        current_state: AgentGameStateFrame = AgentGameStateFrame(frame)
        if self._prev_state is None:
            self._prev_state = current_state
            return

        action = ClientDirection.NORTH  # TODO: PLACEHOLDER UNTIL ACTION SELECTION IS IMPLEMENTED
        reward = compute_reward(self._prev_state, current_state)

        self._experience_replay_buffer.add(ExperienceReplayBuffer(self._prev_state, action, reward, current_state))

        self._prev_state = current_state
        self._prev_action = action

    def on_game_end(self):
        pass

    def on_game_restart(self):
        pass

    def on_game_start(self, viewport_size: tuple[int, int]):
        pass

    def on_game_about_to_start(self, seconds_until_start: int):
        pass
