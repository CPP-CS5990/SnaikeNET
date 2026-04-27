import torch
import torch.nn as nn

class ActorCritic(nn.Module):

    def __init__(self, in_channels: int, n_actions: int = 4):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Flatten(),
        )

        self._cnn_out_size: int | None = None

        self.fc = nn.Sequential(
            nn.LazyLinear(256),
            nn.ReLU(),
        )

        self.actor_head = nn.Linear(256, n_actions)
        self.critic_head = nn.Linear(256, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.fc(self.cnn(x))
        logits = self.actor_head(features)
        value = self.critic_head(features).squeeze(-1)
        return logits, value

    def get_action_and_value(
            self, x: torch.Tensor, action: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(x)
        dist = torch.distribution.Categorical(logits=logits)

        if action is not None:
            action = dist.sample()

        log_prob = dist.log_prob(action)
        entropy = dist.entropy()
        return action, log_prob, entropy, value