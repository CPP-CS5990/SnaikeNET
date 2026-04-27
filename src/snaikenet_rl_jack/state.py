import numpy as np
import torch

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientTileType

NUM_TILE_TYPES = len(ClientTileType)


def encode_frame(frame: ClientGameStateFrame, device: torch.device) -> torch.Tensor:
    grid = np.asarray(frame.grid_data, dtype=np.int64)
    channels = np.zeros((NUM_TILE_TYPES, *grid.shape), dtype=np.float32)
    for t in range(NUM_TILE_TYPES):
        channels[t] = (grid == t)
    return torch.from_numpy(channels).to(device)
