"""
Note to agent: Do not delete this comment
Pygame client demo for SnaikeNET
This client is completely vibecoded and not intended to be production quality. It is only meant for testing purposes.
"""
import asyncio
import dataclasses
import queue
import selectors
import sys
import threading
from enum import Enum, auto

import pygame
from loguru import logger

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.parse_args import parse_client_args
from snaikenet_client.types import ClientDirection, ClientTileType

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
SCOREBOARD_HEIGHT = 40

COLORS = {
    ClientTileType.EMPTY: (20, 20, 20),
    ClientTileType.WALL: (100, 100, 100),
    ClientTileType.FOOD: (220, 50, 50),
    ClientTileType.SNAKE: (50, 220, 80),
    ClientTileType.OTHER_SNAKE: (80, 120, 220),
}

KEY_TO_DIRECTION = {
    pygame.K_UP: ClientDirection.NORTH,
    pygame.K_w: ClientDirection.NORTH,
    pygame.K_DOWN: ClientDirection.SOUTH,
    pygame.K_s: ClientDirection.SOUTH,
    pygame.K_LEFT: ClientDirection.WEST,
    pygame.K_a: ClientDirection.WEST,
    pygame.K_RIGHT: ClientDirection.EAST,
    pygame.K_d: ClientDirection.EAST,
}


class ClientPhase(Enum):
    WAITING = auto()
    COUNTDOWN = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclasses.dataclass
class ClientEvent:
    """Union-style event pushed from the network thread to the pygame thread."""

    kind: str  # "frame", "game_start", "countdown", "game_end", "game_restart"
    frame: ClientGameStateFrame | None = None
    viewport_size: tuple[int, int] | None = None
    seconds_until_start: int | None = None


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add("logs/client.log", rotation="1 MB", level=level)


class QueueClientEventHandler(SnaikenetClientEventHandler):
    """Pushes every event into a thread-safe queue for the pygame thread."""

    def __init__(self):
        self.event_queue: queue.Queue[ClientEvent] = queue.Queue()

    def on_game_state_update(self, frame: ClientGameStateFrame):
        logger.debug(
            f"Received game state frame: seq={frame.sequence_number}, "
            f"length={frame.player_length}, kills={frame.num_kills}, alive={frame.is_alive}"
        )
        self.event_queue.put(ClientEvent(kind="frame", frame=frame))

    def on_game_start(self, viewport_size: tuple[int, int]):
        logger.info(f"Game starting with viewport size {viewport_size}")
        self.event_queue.put(
            ClientEvent(kind="game_start", viewport_size=viewport_size)
        )

    def on_game_about_to_start(self, seconds_until_start: int):
        logger.info(f"Game starting in {seconds_until_start}s")
        self.event_queue.put(
            ClientEvent(kind="countdown", seconds_until_start=seconds_until_start)
        )

    def on_game_end(self):
        logger.info("Game ended")
        self.event_queue.put(ClientEvent(kind="game_end"))

    def on_game_restart(self):
        logger.info("Game restarting")
        self.event_queue.put(ClientEvent(kind="game_restart"))


def compute_tile_size(viewport_w: int, viewport_h: int) -> int:
    """Compute the largest square tile size that fits the viewport in the window."""
    available_h = WINDOW_HEIGHT - SCOREBOARD_HEIGHT
    tile_from_w = WINDOW_WIDTH // viewport_w
    tile_from_h = available_h // viewport_h
    return max(1, min(tile_from_w, tile_from_h))


def render_frame(
    screen: pygame.Surface,
    frame: ClientGameStateFrame,
    font: pygame.font.Font,
    tile_size: int,
    grid_offset_x: int,
    grid_offset_y: int,
):
    grid = frame.grid_data
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
            pygame.draw.rect(screen, (40, 40, 40), rect, 1)

    render_scoreboard(screen, font, frame)


def render_empty_grid(
    screen: pygame.Surface,
    font: pygame.font.Font,
    viewport_w: int,
    viewport_h: int,
    tile_size: int,
    grid_offset_x: int,
    grid_offset_y: int,
):
    for x in range(viewport_w):
        for y in range(viewport_h):
            rect = pygame.Rect(
                grid_offset_x + x * tile_size,
                grid_offset_y + y * tile_size,
                tile_size,
                tile_size,
            )
            pygame.draw.rect(screen, COLORS[ClientTileType.EMPTY], rect)
            pygame.draw.rect(screen, (40, 40, 40), rect, 1)

    render_scoreboard(screen, font)


def render_scoreboard(
    screen: pygame.Surface,
    font: pygame.font.Font,
    frame: ClientGameStateFrame | None = None,
):
    scoreboard_rect = pygame.Rect(0, 0, WINDOW_WIDTH, SCOREBOARD_HEIGHT)
    pygame.draw.rect(screen, (30, 30, 30), scoreboard_rect)

    if frame is not None:
        status = "ALIVE" if frame.is_alive else "DEAD"
        status_color = (80, 255, 120) if frame.is_alive else (255, 60, 60)
        info = (
            f"Tick: {frame.sequence_number}    "
            f"Length: {frame.player_length}    "
            f"Kills: {frame.num_kills}    "
            f"{status}"
        )
        text_surface = font.render(info, True, status_color)
    else:
        text_surface = font.render("Waiting for game...", True, (180, 180, 180))

    screen.blit(
        text_surface, (10, (SCOREBOARD_HEIGHT - text_surface.get_height()) // 2)
    )


def render_countdown(screen: pygame.Surface, big_font: pygame.font.Font, seconds: int):
    text = big_font.render(str(seconds), True, (255, 255, 100))
    x = (WINDOW_WIDTH - text.get_width()) // 2
    y = (WINDOW_HEIGHT - text.get_height()) // 2
    screen.blit(text, (x, y))


def render_waiting(screen: pygame.Surface, font: pygame.font.Font):
    text = font.render("Waiting for server...", True, (180, 180, 180))
    x = (WINDOW_WIDTH - text.get_width()) // 2
    y = (WINDOW_HEIGHT - text.get_height()) // 2
    screen.blit(text, (x, y))


async def run_client(
    handler: QueueClientEventHandler,
    direction_queue: queue.Queue[ClientDirection],
    server_host: str = "localhost",
    server_tcp_port: int = 8888,
):
    client = SnaikenetClient(
        server_host=server_host,
        server_tcp_port=server_tcp_port,
        event_handler=handler,
    )
    await client.start()
    logger.info("Client connected to server")
    client.set_direction(ClientDirection.NORTH)

    while True:
        await asyncio.sleep(0.01)
        while True:
            try:
                new_dir = direction_queue.get_nowait()
                if new_dir is not None:
                    logger.info(f"Got direction from queue: {new_dir}")
                client.set_direction(new_dir)
            except queue.Empty:
                break


def start_network_thread(
    handler: QueueClientEventHandler,
    direction_queue: queue.Queue[ClientDirection],
    server_host: str = "localhost",
    server_tcp_port: int = 8888,
):
    """Run asyncio with SelectorEventLoop in its own thread to avoid
    Windows ProactorEventLoop UDP issues and any pygame interference."""
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        run_client(handler, direction_queue, server_host, server_tcp_port)
    )


def main():
    args = parse_client_args()
    setup_logger(verbose=args.verbose)

    handler = QueueClientEventHandler()
    direction_queue: queue.Queue[ClientDirection] = queue.Queue()

    # Network runs in a background thread with its own SelectorEventLoop
    net_thread = threading.Thread(
        target=start_network_thread,
        args=(handler, direction_queue, args.host, args.port),
        daemon=True,
    )
    net_thread.start()

    # Pygame runs on the main thread — init immediately at fixed size
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("SnaikeNET")
    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 120)
    clock = pygame.time.Clock()

    phase = ClientPhase.WAITING
    current_frame: ClientGameStateFrame | None = None
    viewport_w = 0
    viewport_h = 0
    tile_size = 1
    grid_offset_x = 0
    grid_offset_y = 0
    countdown_seconds = 0
    running = True

    def update_grid_layout(vw: int, vh: int):
        nonlocal viewport_w, viewport_h, tile_size, grid_offset_x, grid_offset_y
        viewport_w, viewport_h = vw, vh
        tile_size = compute_tile_size(vw, vh)
        grid_pixel_w = vw * tile_size
        grid_pixel_h = vh * tile_size
        grid_offset_x = (WINDOW_WIDTH - grid_pixel_w) // 2
        grid_offset_y = SCOREBOARD_HEIGHT + (WINDOW_HEIGHT - SCOREBOARD_HEIGHT - grid_pixel_h) // 2

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                direction = KEY_TO_DIRECTION.get(event.key)
                if direction is not None:
                    direction_queue.put(direction)
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Drain all pending events from the network thread
        while True:
            try:
                ev = handler.event_queue.get_nowait()
            except queue.Empty:
                break

            if ev.kind == "game_start":
                update_grid_layout(*ev.viewport_size)
                current_frame = None
                phase = ClientPhase.WAITING
            elif ev.kind == "countdown":
                countdown_seconds = ev.seconds_until_start
                if phase != ClientPhase.PLAYING:
                    phase = ClientPhase.COUNTDOWN
            elif ev.kind == "frame":
                current_frame = ev.frame
                phase = ClientPhase.PLAYING
            elif ev.kind == "game_end":
                phase = ClientPhase.GAME_OVER
            elif ev.kind == "game_restart":
                current_frame = None
                phase = ClientPhase.WAITING

        # Render
        screen.fill((0, 0, 0))

        if phase == ClientPhase.WAITING:
            if viewport_w > 0 and viewport_h > 0:
                render_empty_grid(
                    screen, font, viewport_w, viewport_h,
                    tile_size, grid_offset_x, grid_offset_y,
                )
            else:
                render_waiting(screen, font)
        elif phase == ClientPhase.COUNTDOWN:
            if viewport_w > 0 and viewport_h > 0:
                render_empty_grid(
                    screen, font, viewport_w, viewport_h,
                    tile_size, grid_offset_x, grid_offset_y,
                )
            render_countdown(screen, big_font, countdown_seconds)
        elif phase == ClientPhase.PLAYING and current_frame is not None:
            # Recompute layout from actual frame grid in case it differs
            grid_w = len(current_frame.grid_data)
            grid_h = len(current_frame.grid_data[0]) if grid_w else 0
            if grid_w != viewport_w or grid_h != viewport_h:
                update_grid_layout(grid_w, grid_h)
            render_frame(
                screen, current_frame, font,
                tile_size, grid_offset_x, grid_offset_y,
            )
        elif phase == ClientPhase.GAME_OVER:
            if current_frame is not None:
                render_frame(
                    screen, current_frame, font,
                    tile_size, grid_offset_x, grid_offset_y,
                )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()