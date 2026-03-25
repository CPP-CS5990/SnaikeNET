from snaikenet_server.server_commands import GameServerCommandInterface
from fastapi import FastAPI


class FastAPIServerCommands:
    def __init__(self, command_interface: GameServerCommandInterface):
        self.command_interface = command_interface
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self):
        self.app.add_api_route(
            "/start", self.command_interface.start_game, methods=["POST"]
        )
        self.app.add_api_route(
            "/stop", self.command_interface.stop_server, methods=["POST"]
        )
        self.app.add_api_route(
            "/restart", self.command_interface.restart_game, methods=["POST"]
        )
