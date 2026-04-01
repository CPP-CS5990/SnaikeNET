from typing import Callable
from loguru import logger
import threading

COMMAND_START = "start"
COMMAND_STOP = "stop"
COMMAND_RESTART = "restart"

_HELP_MESSAGE = """
Available commands:
    - start: Start the game
    - stop: Stop the game
    - restart: Restart the game
    - help: Show this help message
"""


class GameServerCommandInterface:
    _stop_signal: bool = False

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
            "help": self.help_message,
        }

    def help_message(self):
        logger.debug(_HELP_MESSAGE)
        # We print it since instead of log because we are trying to show it to the user, not just log it for debugging purposes
        print(_HELP_MESSAGE)

    def start_game(self):
        handler = self.commands.get(COMMAND_START)
        if handler is not None and callable(handler):
            handler()
        else:
            logger.error("Start command not implemented")

    def stop_server(self):
        handler = self.commands.get(COMMAND_STOP)
        if handler is not None and callable(handler):
            handler()
        else:
            logger.error("Stop command not implemented")

    def restart_game(self):
        handler = self.commands.get(COMMAND_RESTART)
        if handler is not None and callable(handler):
            handler()
        else:
            logger.error("Restart command not implemented")

    def execute_command(self, command):
        handler = self.commands.get(command)
        if handler is not None and callable(handler):
            handler()
        else:
            logger.error(f"Unknown command: {command}")

    def not_stopped(self) -> bool:
        return not self._stop_signal

    def set_stop_signal(self):
        self._stop_signal = True


def console_loop(command_interface: GameServerCommandInterface):
    # Always run and listen for console commands
    command_interface.help_message()  # Show available commands on startup
    while command_interface.not_stopped():
        command = input()
        # Process console commands here
        logger.info(f"Received command: {command}\n")
        command_interface.execute_command(command)

    logger.info("Console thread stopping...\n")
