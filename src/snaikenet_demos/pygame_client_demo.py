import asyncio
import queue
import selectors
import sys
import threading

import pygame
from loguru import logger

from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.parse_args import parse_client_args
from snaikenet_client.types import ClientDirection, ClientTileType

TILE_SIZE = 24
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


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add("logs/client.log", rotation="1 MB", level=level)


class QueueClientEventHandler(SnaikenetClientEventHandler):
    """Pushes every frame into a thread-safe queue for the pygame thread."""

    def __init__(self):
        self.frame_queue: queue.Queue[ClientGameStateFrame] = queue.Queue()

    def on_receive_game_state_frame(self, frame: ClientGameStateFrame):
        logger.debug(
            f"Received game state frame: seq={frame.sequence_number}, length={frame.player_length}, kills={frame.num_kills}, alive={frame.is_alive}"
        )
        self.frame_queue.put(frame)


def drain_queue(q: queue.Queue[ClientGameStateFrame]) -> ClientGameStateFrame | None:
    """Return the most recent frame in the queue, discarding older ones."""
    latest = None
    while True:
        try:
            latest = q.get_nowait()
        except queue.Empty:
            break
    return latest


def render_frame(
    screen: pygame.Surface, frame: ClientGameStateFrame, font: pygame.Font
):
    grid = frame.grid_data
    screen_w = len(grid) * TILE_SIZE

    for x, col in enumerate(grid):
        for y, tile in enumerate(col):
            color = COLORS.get(tile, (0, 0, 0))
            rect = pygame.Rect(
                x * TILE_SIZE, SCOREBOARD_HEIGHT + y * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (40, 40, 40), rect, 1)

    scoreboard_rect = pygame.Rect(0, 0, screen_w, SCOREBOARD_HEIGHT)
    pygame.draw.rect(screen, (30, 30, 30), scoreboard_rect)

    status = "ALIVE" if frame.is_alive else "DEAD"
    status_color = (80, 255, 120) if frame.is_alive else (255, 60, 60)
    info = f"Tick: {frame.sequence_number}    Length: {frame.player_length}    Kills: {frame.num_kills}    {status}"
    text_surface = font.render(info, True, status_color)
    screen.blit(
        text_surface, (10, (SCOREBOARD_HEIGHT - text_surface.get_height()) // 2)
    )


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

    # Block main thread until the first frame arrives (before pygame.init)
    logger.info("Waiting for first game state frame...")
    first_frame = handler.frame_queue.get()

    grid_x = len(first_frame.grid_data)
    grid_y = len(first_frame.grid_data[0]) if grid_x else 0
    window_w = grid_x * TILE_SIZE
    window_h = grid_y * TILE_SIZE + SCOREBOARD_HEIGHT

    # Pygame runs on the main thread
    pygame.init()
    screen = pygame.display.set_mode((window_w, window_h))
    pygame.display.set_caption("SnaikeNET")
    font = pygame.font.SysFont("consolas", 18)
    clock = pygame.time.Clock()

    current_frame = first_frame
    running = True

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

        new_frame = drain_queue(handler.frame_queue)
        if new_frame is not None:
            current_frame = new_frame

        screen.fill((0, 0, 0))
        render_frame(screen, current_frame, font)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
