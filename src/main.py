# Game Server Initialization:
# Parse program arguments
# Create a Game State object
# Create a UDP server to listen for player connections and messages (mock for now)
#   - operate on game state object
# Create a command interface for server administration and debugging (allows us to start/stop the game, add/remove players, etc.)
# - (Later) Create an HTTP server to expose the command interface via a REST API (for remote administration and integration with other services)

# Events:
# When new player makes a connection, they are assigned an ID and are added to the game state
# When the connection is closed, the player is removed
# When the game starts, the server sends the initial game state to all players
# - If a player is killed
#   - The method of death is determined
#   - Whoever caused the death is credited with a kill (if applicable)
#   - The server sends a message to the player that they have been killed and removes them from the game state
#   - Each segment of the snake is removed from the board and becomes an available food location

# Game start initialization:
# - Place players at random starting positions on the board (everyone starts with a length of 1)
# - Place initial food items at random locations on the board
# - If headless is disabled, render the initial game state with pygame

# On game reset:
# - Clear player data and reset game state
# - Do not reset player connections, just reset the game state and send the new state to all players

# Game Loop (runs at a fixed tick rate):
# - Move players
#   - Check that direction is valid (not directly opposite of current direction)
#       - If invalid, ignore the direction change and keep moving in the current direction
# - Check for collisions
# - Handle collisions
#   - If player collides with food, grow from the head and add new food to the board
#   - If player collides with wall, die
#   - If player collides with another player, die
#   - If player collides with itself, die
# - Calculate viewport for all players
# - Send viewport to all players
# - If headless is disabled, render game state with pygame

# On the UDP Server, we will listen for messages from players:
# 
import uuid
import sys
from parse_args import parse_args
from player import SnakePlayer
import threading
from loguru import logger
import asyncio
import random
import pygame

from server_commands import GameServerCommandInterface
from fastapi_server_commands import FastAPIServerCommands

type Location = tuple[int, int]
type GridSize = tuple[int, int]

class Game():
    players: dict[str, SnakePlayer]
    food_locations: set[Location]
    _start_event: threading.Event
    _available_food_locations: set[Location] # TODO: Probably change to list, evaluate later

    def __init__(self):
        self._start_event = threading.Event()
        self.players = {}  # Dictionary to store player information
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

    def add_player(self):
        self.players[str(uuid.uuid4())] = SnakePlayer(initial_position=(0, 0))  # TODO: Set initial position based on game logic

    def remove_player(self, player_id: str) -> SnakePlayer | None:
        return self.players.pop(player_id, None)

    def start_game(self):
        self._start_event.set()

    def stop_game(self):
        # TODO: Implement
        pass

    def restart_game(self):
        # TODO: Implement
        pass

def create_game_thread_instance(game_state: Game):
    def game_thread(): 
        logger.info("Game thread started, waiting for start signal...\n")
        game_state._start_event.wait()

        logger.info("Start signal received, entering game loop...\n")
        while True:
            # sleep for a fixed tick rate (e.g., 100ms)

            game_state.move_players()

    return threading.Thread(target=game_thread)

def create_console_thread_instance(command_interface: GameServerCommandInterface):
    def console_thread():
        # Always run and listen for console commands
        command_interface.help_message() # Show available commands on startup
        while True:
            command = input()
            # Process console commands here
            logger.info(f"Received command: {command}\n")
            command_interface.execute_command(command)

    return threading.Thread(target=console_thread)

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/game.log", rotation="1 MB", level="DEBUG") # Log to file as well, with rotation

if __name__ == "__main__":
    setup_logger()
    args = parse_args() 

    game_state = Game()
        # Implement reset logic here

    command_interface = GameServerCommandInterface(
        start_game=game_state.start_game,
        stop_server=game_state.stop_game,
        restart_game=game_state.restart_game,
    )

    # Create thread instances
    game_thread_instance = create_game_thread_instance(game_state)
    console_thread_instance = create_console_thread_instance(command_interface)

    # Create FastAPI server instance with command interface
    if False: # TODO: Implement when HTTP server is ready
        fastapi_command_interface = FastAPIServerCommands(command_interface)

    # Start threads
    game_thread_instance.start()
    console_thread_instance.start()

    game_thread_instance.join()
    console_thread_instance.join()
    

