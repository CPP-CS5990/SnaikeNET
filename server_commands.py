from typing import Callable

COMMAND_START = "start"
COMMAND_STOP = "stop"
COMMAND_RESTART = "restart"


class GameServerCommandInterface:
    def __init__(
        self,
        start_game: Callable[[], None] | None = None,
        stop_server: Callable[[], None] | None = None,
        restart_game: Callable[[], None] | None = None,
    ):

        self.commands = {
            "start": start_game,
            "stop": stop_server,
            "restart": restart_game,
        }

    def start_game(self):
        handler = self.commands.get(COMMAND_START)
        if handler is not None and callable(handler):
            handler()
        else:
            print("Start command not implemented")

    def stop_server(self):
        handler = self.commands.get(COMMAND_STOP)
        if handler is not None and callable(handler):
            handler()
        else:
            print("Stop command not implemented")

    def restart_game(self):
        handler = self.commands.get(COMMAND_RESTART)
        if handler is not None and callable(handler):
            handler()
        else:
            print("Restart command not implemented")

    def execute_command(self, command):
        handler = self.commands.get(command)
        if handler is not None and callable(handler):
            handler()
        else:
            print(f"Unknown command: {command}")
