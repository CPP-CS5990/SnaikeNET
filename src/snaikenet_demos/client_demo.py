from snaikenet_client.client.client import SnaikenetClient
import asyncio

from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection

def handle_new_frame(frame: ClientGameStateFrame):
    # Any new frames (game state updates) from the server will be received here and can be processed as needed.
    pass


async def main():
    client = SnaikenetClient(server_host="localhost", server_port=8888, on_receive_game_state_frame=handle_new_frame)
    await client.start()
    client.set_direction(ClientDirection.NORTH)

    while True:
        await asyncio.sleep(1)  # Keep the client running

if __name__ == "__main__":
    asyncio.run(main())