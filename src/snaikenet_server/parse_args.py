import argparse


class ArgNamespace(argparse.Namespace):
    headless: bool
    verbose: bool
    tcp_port: int
    udp_port: int
    host: str
    grid_size: tuple[int, int]
    viewport_distance: tuple[int, int]
    tick_rate: int


def parse_args() -> ArgNamespace:
    parser = argparse.ArgumentParser(description="Multiplayer Snake Game Server")
    parser.add_argument(
        "--headless",
        "-H",
        action="store_true",
        help="Run the server in headless mode. No graphical interface will be displayed.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging for debugging purposes.",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=8888,
        help="TCP port for client registration (default: 8888)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=8888,
        help="UDP port for game data communication (default: 8888)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host/IP address to bind the server to (default: localhost)",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        nargs=2,
        default=(64, 64),
        metavar=("W", "H"),
        help="Grid dimensions as W H (default: 64 64)",
    )
    parser.add_argument(
        "--viewport-distance",
        type=int,
        nargs=2,
        default=(20, 20),
        metavar=("X", "Y"),
        help="Viewport distance from center as X Y (default: 20 20)",
    )
    parser.add_argument(
        "--tick-rate",
        type=int,
        default=6,
        help="Game tick rate in ticks per second (default: 6)",
    )
    args = parser.parse_args(namespace=ArgNamespace())
    args.grid_size = tuple(args.grid_size)
    args.viewport_distance = tuple(args.viewport_distance)
    return args
