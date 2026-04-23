import numpy as np
import torch
from torch.nn.functional import one_hot

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientTileType

NUM_TILE_TYPES = len(ClientTileType)


def frame_to_tensor(frame: ClientGameStateFrame) -> torch.Tensor:
    grid = frame.grid_data
    H = len(grid)
    W = len(grid[0])

    raw = np.array(grid, dtype = np.int64)

    one_hot = np.zeros((NUM_TILE_TYPES, H, W), dtype = np.float32)
    for title_type in ClientTileType:
        one_hot[title_type] = (raw == title_type).astype(np.float32)