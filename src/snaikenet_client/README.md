# snaikenet_client

Python client library for connecting to a SnaikeNET server. The client handles TCP registration, UDP hole punching, heartbeats, and direction updates so you only have to write game logic.

## Core API

Everything you need lives in a few modules:

| Import | Purpose |
| --- | --- |
| `snaikenet_client.client.client.SnaikenetClient` | The connection object. Handles networking. |
| `snaikenet_client.client.client_event_handler.SnaikenetClientEventHandler` | Abstract base class. Subclass this to react to server events. |
| `snaikenet_client.types.ClientDirection`, `ClientTileType` | Enums for movement input and grid tile values. |
| `snaikenet_client.client_data.ClientGameStateFrame` | The per-tick payload you receive in `on_game_state_update`. |

### `SnaikenetClient`

```python
SnaikenetClient(
    server_tcp_port: int = 8888,
    server_host: str = "localhost",
    send_interval_ms: int = 13,          # how often your direction is re-sent via UDP
    event_handler: SnaikenetClientEventHandler = DefaultSnaikenetClientEventHandler(),
    is_spectator: bool = False,
)
```

Lifecycle:

- `await client.start(uuid=None)` - connects and spawns the heartbeat + direction-send tasks. Pass a previously-returned UUID to reconnect.
- `client.set_direction(direction: ClientDirection)` - call whenever you want to change heading. Safe from inside event handlers.
- `client.get_client_id() -> str | None` - the UUID the server assigned you (store this to support reconnects).
- `await client.stop()` - cancels background tasks and closes the UDP transport.

The client re-sends your current direction every `send_interval_ms` automatically, so your handler just needs to pick the current desired direction (no need to manage timing).

### Event handler interface

Subclass `SnaikenetClientEventHandler` and override the callbacks you care about (or subclass `DefaultSnaikenetClientEventHandler` to skip the ones you don't). `on_game_state_update` receives a `ClientGameStateFrame` once per server tick; that is where your per-frame logic belongs.

One thing worth flagging about `ClientGameStateFrame.grid_data` that is not obvious from the type alone: it is the viewport centered on your snake (not the full world), and it is indexed `[x][y]`.

### Handling `sequence_number`

Frames arrive via UDP, so packets can be dropped, reordered, or duplicated. If you last saw sequence `4` and the next frame is `6`, frame `5` is either late or lost, and you must handle this. The client library itself does not filter frames; every decoded payload is delivered to your handler verbatim.

Most implementations should treat any frame older than the most recent one as unrecoverable and ignore it. There is no retransmission mechanism, and by the time an out-of-order frame arrives, a newer snapshot has already superseded it. Track the highest sequence number you've processed and drop anything less than or equal to it:

```python
def on_game_state_update(self, frame: ClientGameStateFrame):
    if frame.sequence_number <= self.last_sequence_number:
        return  # stale or duplicate, discard
    if frame.sequence_number != self.last_sequence_number + 1:
        # one or more frames were dropped between last_sequence_number and now;
        # log it if you care, but just proceed with the newer frame
        pass
    self.last_sequence_number = frame.sequence_number
    # ...act on the frame
```

Remember to reset `last_sequence_number` to `-1` in `on_game_start`, `on_game_restart`, and `on_game_about_to_start`, since the server's tick counter resets at the start of each game. `on_game_about_to_start` is included defensively: the `on_game_restart` message can be lost in transit (it's UDP), and if that happens without a reset, the first real frame of the new game will look stale relative to the previous game's final sequence number and be discarded.

## Minimal example

```python
# my_bot.py
import asyncio
from snaikenet_client.client.client import SnaikenetClient
from snaikenet_client.client.client_event_handler import SnaikenetClientEventHandler
from snaikenet_client.client_data import ClientGameStateFrame
from snaikenet_client.types import ClientDirection, ClientTileType


class BotHandler(SnaikenetClientEventHandler):
    def __init__(self):
        self.client: SnaikenetClient | None = None
        self.current_direction = ClientDirection.NORTH
        self.last_sequence_number = -1

    def on_game_start(self, viewport_size):
        print(f"Game started, viewport {viewport_size}")
        self.last_sequence_number = -1

    def on_game_restart(self):
        print("Game restarting")
        self.last_sequence_number = -1

    def on_game_about_to_start(self, seconds_until_start):
        print(f"Starting in {seconds_until_start}s")
        # Reset here too, the on_game_restart message may have been dropped by UDP.
        self.last_sequence_number = -1

    def on_game_end(self):
        print("Game over")

    def on_game_state_update(self, frame: ClientGameStateFrame):
        # TODO(human): drop stale/duplicate frames and track dropped ones
        # using frame.sequence_number and self.last_sequence_number.

        if not frame.is_alive or self.client is None:
            return
        next_direction = self.choose_direction(frame)
        if next_direction != self.current_direction:
            self.current_direction = next_direction
            self.client.set_direction(next_direction)

    def choose_direction(self, frame: ClientGameStateFrame) -> ClientDirection:
        return self.current_direction


async def main():
    handler = BotHandler()
    client = SnaikenetClient(
        server_host="localhost",
        server_tcp_port=8888,
        event_handler=handler,
    )
    handler.client = client

    await client.start()
    client.set_direction(ClientDirection.NORTH)
    print(f"Connected as {client.get_client_id()}")

    try:
        await asyncio.Event().wait()  # keep the loop alive; client runs in background tasks
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

Run it against a local server:

```bash
uv run server              # in one terminal
uv run python my_bot.py    # in another
```

## Reconnecting

Store `client.get_client_id()` after connecting, then pass it to `start` to resume the same slot:

```python
uuid = client.get_client_id()
# ...later, after a disconnect...
new_client = SnaikenetClient(event_handler=handler)
await new_client.start(uuid=uuid)
```

## CLI argument helper

If your script takes standard host/port flags, `parse_client_args()` returns an `argparse` namespace with `host`, `port`, `verbose`, `reconnect_uuid`, and `spectator`:

```python
from snaikenet_client.parse_args import parse_client_args

args = parse_client_args()
client = SnaikenetClient(
    server_host=args.host,
    server_tcp_port=args.port,
    is_spectator=args.spectator,
)
await client.start(args.reconnect_uuid)
```