import numpy as np
import torch

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientTileType

NUM_TILE_TYPES = len(ClientTileType)      # Empty, Wall, Food, Snake, Other_Snake


def frame_to_tensor(frame: ClientGameStateFrame) -> torch.Tensor:

    """
    Converts a ClientGameStateFrame grid into a one encoded Tensor
    Returns a shape: (NUM_TILE_TYPES, H, W) = (5, H, W)
    """

    grid = frame.grid_data
    H = len(grid)
    W = len(grid[0])

    raw = np.array(grid, dtype = np.int64)

    one_hot = np.zeros((NUM_TILE_TYPES, H, W), dtype = np.float32)
    for tile_type in ClientTileType:
        one_hot[tile_type] = (raw == tile_type).astype(np.float32)

    return torch.from_numpy(one_hot)

class FrameStacker:

    """
    Keeps the last 'n_frames' observations and
    returns them stacked along the channel dimension

    output shape: (5 * n_frames, H, W)
    """

    def __init__(self, n_frames: int = 2):
        self.n_frames = n_frames
        self._frames: list[torch.Tensor] =  []

    def reset(self, first_frame: ClientGameStateFrame) -> torch.Tensor:
        """
        Call at the start of each life to fill the buffer with the first frame
        """
        t = frame_to_tensor(first_frame)
        self._frames = [t] * self.n_frames
        return self._get_stacked()

    def step(self, frame: ClientGameStateFrame) -> torch.Tensor:
        """
        Push a new frame and return  the updated stacked observation
        """
        self._frames.append(frame_to_tensor(frame))
        if len(self._frames) > self.n_frames:
            self._frames.pop(0)
        return self._get_stacked()

    def _get_stacked(self) -> torch.Tensor:
        return torch.cat(self._frames, dim = 0)
