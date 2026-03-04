from player import SnakePlayer
import threading
import asyncio
import random

from server_commands import GameServerCommandInterface
from fastapi_server_commands import FastAPIServerCommands

type Location = tuple[int, int]
type GridSize = tuple[int, int]


class GameState:
    def __init__(self):
        self.players = {}  # Dictionary to store player information
        self.game_started = False
        self.food_locations: set[tuple[int, int]] = (
            set()
        )  # List to store food locations
        self._available_food_locations: set[tuple[int, int]] = set()
          # Set to track available food locations

    def _initialize_available_food_locations(self, grid_size: GridSize):
        self._available_food_locations = set(
            (x, y) for x in range(grid_size[0]) for y in range(grid_size[1])
        )
        # random.shuffle(self._available_food_locations)

    def add_random_food(self, grid_size: GridSize):
        while True:
            location = (
                random.randint(0, grid_size[0] - 1),
                random.randint(0, grid_size[1] - 1),
            )
            if location not in self.food_locations:
                self.food_locations.add(location)
                break

    def remove_food(self, location: Location):
        self.food_locations.discard(location)
        self._available_food_locations.discard(location)

    def move_players(self):
        # Implement player movement logic here
        pass


class UDPServer(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()
        self.players = {}  # Dictionary to store player information

    def connection_made(self, transport):
        self.transport = transport
        print("UDP server started")

    def datagram_received(self, data, addr):
        message = data.decode()
        print(f"Received {message} from {addr}")
        # Process incoming messages from players here
        # For example, you can parse the message and update the game state accordingly


if __name__ == "__main__":

    def game_thread():
        # Wait for players to connect and initialize the game state
        while game_state.game_started == False:
            pass

        while True:
            if game_state.game_started:
                pass
            # Game logic goes here
            pass

    game_state = GameState()

    def start_game():
        game_not_started = False

    # Exit everything
    def stop():
        # Clean up resources, close sockets, etc.
        print("Stopping server...")
        exit(0)

    def reset():
        # Reset game state, clear player data, etc.
        print("Resetting game...")
        # Implement reset logic here

    command_interface = GameServerCommandInterface(
        start_game=start_game, stop_server=stop, restart_game=reset
    )

    fastapi_command_interface = FastAPIServerCommands(command_interface)

    game_thread_instance = threading.Thread(target=game_thread)

    # Handle console input in a separate thread
    # Will be used for server administration and debugging
    # Will also be used to send commands to the game thread,
    # such as starting/stopping the game, adding/removing players, etc.
    def console_thread(command_interface: GameServerCommandInterface):
        # Always run and listen for console commands
        while True:
            command = input("Enter command: ")
            # Process console commands here
            print(f"Received command: {command}")
            command_interface.execute_command(command)

    console_thread_instance = threading.Thread(
        target=console_thread, args=(command_interface,)
    )

    game_thread_instance.start()
    console_thread_instance.start()

    # UUID4 as string to SnakePlayer
    players: dict[str, SnakePlayer] = {}
