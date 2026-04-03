from snaikenet_client.client.client import SnaikenetClient
import asyncio

from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.parse_args import parse_client_args
from snaikenet_client.types import ClientDirection
from loguru import logger
import sys


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add(
        "logs/server.log", rotation="1 MB", level=level
    )  # Log to file as well, with rotation


async def main():
    args = parse_client_args()
    setup_logger(verbose=args.verbose)

    class _MyClientEventHandler(SnaikenetClientEventHandler):
        def on_game_about_to_start(self, seconds_until_start: int):
            pass

        def on_game_end(self):
            pass

        def on_game_restart(self):
            pass

        def on_game_start(self, viewport_size: tuple[int, int]):
            pass

        def on_game_state_update(self, frame: ClientGameStateFrame):
            logger.debug(f"Received game state frame: {frame}")

    client = SnaikenetClient(
        server_host=args.host,
        server_tcp_port=args.port,
        event_handler=_MyClientEventHandler(),
    )
    await client.start()
    client.set_direction(ClientDirection.NORTH)

    while True:
        await asyncio.sleep(1)  # Keep the client running


if __name__ == "__main__":
    asyncio.run(main())
