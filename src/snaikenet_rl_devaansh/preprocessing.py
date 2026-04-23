import numpy as np
import torch

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

    return torch.from_numpy(one_hot)

class FrameStacker:
    def __init__(self, n_frames: int = 2):
        self.n_frames = n_frames
        self.frames: list[torch.Tensor] =  []

    def reset(self, first_frame: ClientGameStateFrame) -> torch.Tensor:
        t = frame_to_tensor(first_frame)
        self._frames = [t] * self.n_frames
        return self._getstacked()

    def step(self, frame: ClientGameStateFrame) -> torch.Tensor:
        self._frames.append(frame_to_tensor(frame))
        if len(self._frames) == self.n_frames:
            self._frames.pop(0)
        return self._get_stacked()

    def _get_stacked(self) -> torch.Tensor:
        return torch.cat(self._frames, dim = 0)
