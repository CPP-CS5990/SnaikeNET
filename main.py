from player import SnakePlayer
import socket
import threading
import asyncio

from server_commands import GameServerCommandInterface
from fastapi_server_commands import FastAPIServerCommands

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

game_not_started = True

def game_thread():
    # Wait for players to connect and initialize the game state
    while game_not_started:
        pass

    while True:
        # Game logic goes here
        pass

# Handle console input in a separate thread
# Will be used for server administration and debugging
# Will also be used to send commands to the game thread,
# such as starting/stopping the game, adding/removing players, etc.
def console_thread(command_interface: GameServerCommandInterface):
    while True:
        command = input("Enter command: ")
        # Process console commands here
        print(f"Received command: {command}")

def start_game():
    global game_not_started
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


if __name__ == "__main__":
    command_interface = GameServerCommandInterface(
        start_game=start_game,
        stop_server=stop,
        restart_game=reset
    )

    fastapi_command_interface = FastAPIServerCommands(command_interface)
    
    game_thread_instance = threading.Thread(target=game_thread)
    console_thread_instance = threading.Thread(target=console_thread, args=(command_interface,))

    game_thread_instance.start()
    console_thread_instance.start()

    # UUID4 as string to SnakePlayer
    players: dict[str, SnakePlayer] = {}

