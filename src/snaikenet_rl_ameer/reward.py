from snaikenet_client.types import ClientTileType
from snaikenet_rl_ameer.training import AgentGameStateFrame


# Get Manhattan distance of the closest food
def closest_food(frame: AgentGameStateFrame) -> float:
    food_positions: list[tuple[int, int]] = []

    height = len(frame.grid_data)
    width = len(frame.grid_data[0])

    for i in range(height):
        for j in range(width):
            if frame.grid_data[i][j] == ClientTileType.FOOD:
                food_positions.append((i, j))

    if not food_positions:
        return float('inf')  # No food available, return infinity

    center_pos = (height // 2, width // 2)

    closest = float('inf')

    for food_pos in food_positions:
        dist = distance(center_pos, food_pos)
        if dist < closest:
            closest = dist

    return closest

# Since snakes cannot move diagonally, it is more useful to know the Manhattan distance
def distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    return abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])

def compute_reward(f1: AgentGameStateFrame, f2: AgentGameStateFrame) -> float:
    reward = 0.0
    f1_closest_food = closest_food(f1)
    f2_closest_food = closest_food(f2)

    if f1_closest_food > f2_closest_food:
        reward -= 10



    return reward