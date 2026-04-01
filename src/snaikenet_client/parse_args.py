import argparse


class ClientArgNamespace(argparse.Namespace):
    host: str
    port: int
    verbose: bool


def parse_client_args() -> ClientArgNamespace:
    parser = argparse.ArgumentParser(description="SnaikeNET Client")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host to connect to (default: localhost)",
    )
    parser.add_argument(
        "--port",
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
    args = parser.parse_args(namespace=ClientArgNamespace())
    return args
