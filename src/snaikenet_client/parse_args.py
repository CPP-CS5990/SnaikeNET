import argparse


class ClientArgNamespace(argparse.Namespace):
    host: str
    port: int
    verbose: bool
    reconnect_uuid: str
    spectator: bool


def parse_client_args() -> ClientArgNamespace:
    parser = argparse.ArgumentParser(description="SnaikeNET Client")
    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="localhost",
        help="Server host to connect to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8888,
        help="Server TCP port to connect to (default: 8888)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging for debugging purposes.",
    )
    parser.add_argument(
        "--reconnect-uuid",
        "-r",
        type=str,
        default=None,
        help="UUID to reconnect to the server (default: None)",
    )
    parser.add_argument(
        "--spectator",
        "-s",
        action="store_true",
        help="Connect as a spectator (default: False)",
        default=False,
    )
    args = parser.parse_args(namespace=ClientArgNamespace())
    return args
