import torch

class RolloutBuffer:

    def __init__(self, capacity: int = 512, gamma: float = 0.99, gae_lambda: float = 0.95):
        self.capacity = capacity
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self._ptr = 0
        self._full = False

        self.states: list[torch.Tensor] = []
        self.actions: list[int] = []
        self.log_probs: list[float] = []
        self.rewards: list[float] = []
        self.values: list[float] = []
        self.dones: list[bool] = []

    def add(
            self,
            state: torch.Tensor,
            action: int,
            log_prob: float,
            reward: float,
            value: float,
            done: bool,
    ):
        if len(self.states) < self.capacity:
            self.states.append(state)
            self.actions.append(action)
            self.log_probs.append(log_prob)
            self.rewards.append(reward)
            self.values.append(value)
            self.dones.append(done)
        else:
            idx = self._ptr % self.capacity
            self.states[idx] = state
            self.actions[idx] = action
            self.log_probs[idx] = log_prob
            self.rewards[idx] = reward
            self.values[idx] = value
            self.dones[idx] = done

        self._ptr += 1

    def is_full(self) -> bool:
        return self._ptr >= self.capacity

    def compute_advantages(self, last_value: float) -> tuple[torch.Tensor, torch.Tensor]:
        advantages = torch.zeros(self.capacity)
        gae = 0.0

        for t in reversed(range(self.capacity)):
            next_value = last_value if t == self.capacity - 1 else self.values[t + 1]
            next_done = 0.0 if t == self.capacity - 1 else float(self.dones[t + 1])

            delta = self.rewards[t] + self.gamma * next_value * (1 - next_done) - self.values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - next_done) * gae
            advantages[t] = gae

        returns  = advantages + torch.tensor(self.values)
        return advantages, returns

    def get_tensors(self) -> dict[str, torch.Tensor]:
        return{
            "states": torch.stack(self.states),
            "actions": torch.tensor(self.actions, dtype = torch.long),
            "log_probs": torch.tensor(self.log_probs),
            "values": torch.tensor(self.values),
        }

    def clear(self):
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()
        self._ptr = 0