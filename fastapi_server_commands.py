from server_commands import COMMAND_RESTART, COMMAND_START, COMMAND_STOP, GameServerCommandInterface
from fastapi import FastAPI

class FastAPIServerCommands:
    def __init__(self, command_interface: GameServerCommandInterface):
        self.command_interface = command_interface
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self):
        commands = self.command_interface.commands
        start_handler = commands.get(COMMAND_START)
        if start_handler is not None and callable(start_handler):
            self.app.add_api_route("/start", start_handler, methods=["POST"])

        stop_handler = commands.get(COMMAND_STOP)
        if stop_handler is not None and callable(stop_handler):
            self.app.add_api_route("/stop", stop_handler, methods=["POST"])

        restart_handler = commands.get(COMMAND_RESTART)
        if restart_handler is not None and callable(restart_handler):
            self.app.add_api_route("/restart", restart_handler, methods=["POST"])
