import argparse

class ArgNamespace(argparse.Namespace):
    headless: bool
    verbose: bool

def parse_args() -> ArgNamespace:
    parser = argparse.ArgumentParser(description="Multiplayer Snake Game Server")
    parser.add_argument("--headless", "-H", action="store_true", help="Run the server in headless mode. No graphical interface will be displayed.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging for debugging purposes.")
    args = parser.parse_args(namespace=ArgNamespace())
    return args
