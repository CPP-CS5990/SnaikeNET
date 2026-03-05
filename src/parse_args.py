import argparse

class ArgNamespace(argparse.Namespace):
    headless: bool

def parse_args() -> ArgNamespace:
    parser = argparse.ArgumentParser(description="Multiplayer Snake Game Server")
    parser.add_argument("--headless", "-H", action="store_true", help="Run the server in headless mode. No graphical interface will be displayed.")
    args = parser.parse_args(namespace=ArgNamespace())
    return args
