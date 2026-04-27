import torch
import torch.nn as nn
import torch.optim as optim

from snaikenet_rl_devaansh.networks_reference import ActorCritic
from snaikenet_rl_devaansh.rollout_buffer_reference import RolloutBuffer

class PPO:

    def __init__(
            self,
            network: ActorCritic,
            lr: float = 3e-4,
            clip_eps: float = 0.2,
            n_epochs: int = 4,
            batch_size: int = 64,
            vf_coef: float = 0.5,
            ent_coef: float = 0.01,
    ):
        self.network = network
        self.clip_eps = clip_eps
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.lr = lr
        self.vf_coef = vf_coef
        self.ent_coef = ent_coef
        self.optimizer = optim.Adam(network.parameters(), lr=lr)

    def update(self, buffer: RolloutBuffer, last_value: float):

        advantages, returns = buffer.compute_advantages(last_value)

        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        tensors =  buffer.get_tensors()
        states = tensors['states']
        actions = tensors['actions']
        old_log_probs = tensors['old_log_probs']

        n = len(states)

        for _ in range(self.n_epochs):
            indices = torch.randperm(n)

            for start in range(0, n, self.batch_size):
                batch_idx = indices[start: start + self.batch_size]

                batch_states = states[batch_idx]
                batch_actions = actions[batch_idx]
                batch_old_lp = old_log_probs[batch_idx]
                batch_adv = advantages[batch_idx]
                batch_returns = returns[batch_idx]

                _, new_log_probs, entropy, new_values = self.network.get_action_and_value(
                    batch_states, batch_actions
                )

                ratio = torch.exp(new_log_probs - batch_old_lp)
                surrogate1 = ratio * batch_adv
                surrogate2 = torch.clamp(ratio, 1 - self.clip_eps, 1 + self.clip_eps) * batch_adv
                actor_loss = -torch.min(surrogate1, surrogate2).mean()

                critic_loss = nn.functional.mse_loss(new_values, batch_returns)

                entropy_loss = -entropy.mean()

                loss = actor_loss + self.vf_coef * critic_loss + self.ent_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), max_norm = 0.5)
                self.optimizer.step()

        buffer.clear()
