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
import time
import sys
from snakenet.game.game import Game
from snakenet.parse_args import parse_args
import threading
from loguru import logger

from snakenet.server_commands import GameServerCommandInterface
from snakenet.fastapi_server_commands import FastAPIServerCommands

TICK_RATE = 3
TICK_INTERVAL = 1 / TICK_RATE


def create_game_thread_instance(game: Game):
    def game_loop():
        global not_stopped
        logger.info("Game thread started, waiting for start signal...\n")
        game.wait_for_game_start()

        logger.info("Start signal received, entering game loop...\n")
        tick = 0
        start_time = time.time()
        while not_stopped:
            # sleep for a fixed tick rate (e.g., 100ms)
            threading.Event().wait(TICK_INTERVAL)
            tick += 1
            logger.debug(f"Tick... {tick} (Elapsed time: {time.time() - start_time:.2f}s)\n")
            logger.debug(f"Ticks per second: {tick / (time.time() - start_time):.2f}\n")
            game.tick()
        # game.cleanup() # TODO: Implement any necessary cleanup logic when the game loop ends
        logger.info("Game thread exiting...\n")

    return threading.Thread(target=game_loop)


def create_console_thread_instance(command_interface: GameServerCommandInterface):
    def console_thread():
        # Always run and listen for console commands
        command_interface.help_message()  # Show available commands on startup
        while not_stopped:
            command = input()
            # Process console commands here
            logger.info(f"Received command: {command}\n")
            command_interface.execute_command(command)

    return threading.Thread(target=console_thread)


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)
    logger.add("logs/game.log", rotation="1 MB", level=level)  # Log to file as well, with rotation

def main():
    global not_stopped
    not_stopped = True

    args = parse_args()
    setup_logger(args.verbose)

    game = Game((128, 128))

    def stop_server():
        global not_stopped
        not_stopped = False
        game.stop_game()

    command_interface = GameServerCommandInterface(
        start_game=game.start_game,
        stop_server=stop_server,
        restart_game=game.restart_game,
    )

    # Create thread instances
    game_thread_instance = create_game_thread_instance(game)
    console_thread_instance = create_console_thread_instance(command_interface)

    # Create FastAPI server instance with command interface
    if False:  # TODO: Implement when HTTP server is ready
        fastapi_command_interface = FastAPIServerCommands(command_interface)

    # Start threads
    game_thread_instance.start()
    console_thread_instance.start()

    game_thread_instance.join()
    logger.info("Game thread has terminated, shutting down console thread...\n")
    console_thread_instance.join()
    logger.info("Console thread has terminated, exiting program...\n")


if __name__ == "__main__":
    not_stopped = True
    main()
