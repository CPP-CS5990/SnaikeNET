import torch

from snaikenet_client.client.client_event_handler import DefaultSnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection

from snaikenet_rl_devaansh.networks import ActorCritic
from snaikenet_rl_devaansh.preprocessing import FrameStacker, NUM_TILE_TYPES
from snaikenet_rl_devaansh.rollout_buffer import RolloutBuffer
from snaikenet_rl_devaansh.ppo import PPO
from snaikenet_rl_devaansh.reward import compute_reward

N_FRAMES     = 2
ROLLOUT_SIZE = 512
ACTION_MAP   = [ClientDirection.NORTH, ClientDirection.SOUTH,
                ClientDirection.EAST,  ClientDirection.WEST]


class PPOAgentEventHandler(DefaultSnaikenetClientEventHandler):

    def __init__(self):
        self.network: ActorCritic | None = None
        self.ppo: PPO | None = None
        self.buffer = RolloutBuffer(capacity=ROLLOUT_SIZE)

        self.stacker: FrameStacker = FrameStacker(n_frames=N_FRAMES)
        self._prev_frame: ClientGameStateFrame | None = None
        self._prev_state: torch.Tensor | None = None
        self._prev_action: int | None = None
        self._prev_log_prob: float | None = None
        self._prev_value: float | None = None

        self.send_direction = None

    def on_game_start(self, viewport_size: tuple[int, int]):
        in_channels = NUM_TILE_TYPES * N_FRAMES  # 5 * 2 = 10

        if self.network is None:
            self.network = ActorCritic(in_channels=in_channels)
            self.ppo = PPO(self.network)

        self._prev_frame = None
        self._prev_state = None

    def on_game_state_update(self, frame: ClientGameStateFrame):
        if self.network is None:
            return

        if self._prev_state is None:
            curr_state = self.stacker.reset(frame)
        else:
            curr_state = self.stacker.step(frame)

        if self._prev_frame is not None:
            reward = compute_reward(self._prev_frame, frame)
            done = not frame.is_alive

            self.buffer.add(
                state    = self._prev_state,
                action   = self._prev_action,
                log_prob = self._prev_log_prob,
                reward   = reward,
                value    = self._prev_value,
                done     = done,
            )

            if self.buffer.is_full():
                with torch.no_grad():
                    _, last_value = self.network.forward(curr_state.unsqueeze(0))
                last_val = last_value.item() if frame.is_alive else 0.0
                self.ppo.update(self.buffer, last_value=last_val)

        if frame.is_alive:
            with torch.no_grad():
                action, log_prob, _, value = self.network.get_action_and_value(
                    curr_state.unsqueeze(0)
                )
            action_idx  = action.item()
            log_prob_val = log_prob.item()
            value_val    = value.item()

            if self.send_direction is not None:
                self.send_direction(ACTION_MAP[action_idx])
        else:
            action_idx, log_prob_val, value_val = 0, 0.0, 0.0

        self._prev_frame    = frame
        self._prev_state    = curr_state
        self._prev_action   = action_idx
        self._prev_log_prob = log_prob_val
        self._prev_value    = value_val

    def on_game_restart(self):
        self._prev_frame = None
        self._prev_state = None

    def on_game_end(self):
        self.on_game_restart()