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
# - Check for collisions
# - Handle collisions
#   - If player collides with food, grow from the head and add new food to the board
#   - If player collides with wall, die
#   - If player collides with another player, die
#   - If player collides with itself, die
# - Move players
#   - Check that direction is valid (not directly opposite of current direction)
#       - If invalid, ignore the direction change and keep moving in the current direction
# - Calculate viewport for all players
# - Send viewport to all players
# - If headless is disabled, render game state with pygame

# On the UDP Server, we will listen for messages from players:
#
import sys
from snaikenet.game.game import Game, create_game_thread_instance
from snaikenet.parse_args import parse_args
from loguru import logger

from snaikenet.server_commands import (
    GameServerCommandInterface,
    create_console_thread_instance,
)

TICK_RATE = 24
TICK_INTERVAL = 1 / TICK_RATE


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add(
        "logs/game.log", rotation="1 MB", level=level
    )  # Log to file as well, with rotation


def main():
    args = parse_args()
    setup_logger(args.verbose)

    game = Game((128, 128))

    def stop_server():
        game.stop_game()
        command_interface.set_stop_signal()

    command_interface = GameServerCommandInterface(
        start_game=game.start_game,
        stop_server=stop_server,
        restart_game=game.restart_game,
    )

    # Create thread instances
    game_thread_instance = create_game_thread_instance(game, TICK_INTERVAL)
    console_thread_instance = create_console_thread_instance(command_interface)

    # Create FastAPI server instance with command interface
    # if False:  # TODO: Implement when HTTP server is ready
    #     fastapi_command_interface = FastAPIServerCommands(command_interface)

    # Start threads
    game_thread_instance.start()
    console_thread_instance.start()


if __name__ == "__main__":
    main()
