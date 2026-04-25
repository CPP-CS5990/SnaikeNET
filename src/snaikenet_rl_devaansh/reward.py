from snaikenet_client.client_data import ClientGameStateFrame

REWARD_FOOD   =  10.0
REWARD_KILL   =  20.0
REWARD_DEATH  = -10.0
REWARD_STEP   = -0.1

def compute_reward(prev: ClientGameStateFrame,
                   curr: ClientGameStateFrame) -> float:

    if not curr.is_alive and prev.is_alive:
        return REWARD_DEATH
    reward = REWARD_STEP

    if curr.player_length > prev.player_length:
        reward += REWARD_FOOD

    if curr.num_kills > prev.num_kills:
        reward += REWARD_KILL

    return reward

