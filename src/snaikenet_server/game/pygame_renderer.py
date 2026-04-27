from __future__ import annotations

import dataclasses
import queue

import numpy as np
import pygame
from loguru import logger
from numpy.typing import NDArray

from snaikenet_server.game.grid import TileType

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

COLORS = {
    TileType.EMPTY: (20, 20, 20),
    TileType.WALL: (100, 100, 100),
    TileType.FOOD: (220, 50, 50),
    TileType.SNAKE: (50, 220, 80),
}


@dataclasses.dataclass
class RendererEvent:
    """Event pushed from the game thread to the pygame renderer thread."""

    kind: str  # "frame" | "shutdown"
    grid_data: NDArray[np.uint8] | None = None


def _compute_tile_size(grid_w: int, grid_h: int) -> int:
    return max(1, min(WINDOW_WIDTH // grid_w, WINDOW_HEIGHT // grid_h))


def _render_grid(
    screen: pygame.Surface,
    grid: NDArray[np.uint8],
    tile_size: int,
    grid_offset_x: int,
    grid_offset_y: int,
) -> None:
    for x, col in enumerate(grid):
        for y, tile in enumerate(col):
            color = COLORS.get(tile, (0, 0, 0))
            rect = pygame.Rect(
                grid_offset_x + x * tile_size,
                grid_offset_y + y * tile_size,
                tile_size,
                tile_size,
            )
            pygame.draw.rect(screen, color, rect)


def render_loop(event_queue: queue.Queue[RendererEvent]) -> None:
    """Run the pygame render loop on the calling thread.

    Drains the event queue once per frame and renders the most recent grid.
    Exits when the pygame window is closed or on receipt of a `"shutdown"`
    event from the game thread.
    """
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("SnaikeNET Server")
    clock = pygame.time.Clock()

    current_grid: NDArray[np.uint8] | None = None
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        while True:
            try:
                ev = event_queue.get_nowait()
            except queue.Empty:
                break
            if ev.kind == "frame":
                current_grid = ev.grid_data
            elif ev.kind == "shutdown":
                running = False
            else:
                logger.warning(f"Unknown renderer event kind: {ev.kind}")

        screen.fill((0, 0, 0))

        if current_grid is not None:
            grid_w, grid_h = current_grid.shape
            tile_size = _compute_tile_size(grid_w, grid_h)
            grid_pixel_w = grid_w * tile_size
            grid_pixel_h = grid_h * tile_size
            grid_offset_x = (WINDOW_WIDTH - grid_pixel_w) // 2
            grid_offset_y = (WINDOW_HEIGHT - grid_pixel_h) // 2
            _render_grid(screen, current_grid, tile_size, grid_offset_x, grid_offset_y)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
