from snaikenet.game.game_state import PlayerView
from snaikenet.game.grid import GridStructure, TileType
from snaikenet.game.types import Direction
import json


def decode_direction(data: bytes) -> Direction | None:
    direction = data.decode().strip().lower()
    match direction:
        case "north":
            return Direction.NORTH
        case "south":
            return Direction.SOUTH
        case "east":
            return Direction.EAST
        case "west":
            return Direction.WEST
        case _:
            return None


def encode_direction(direction: Direction) -> bytes:
    match direction:
        case Direction.NORTH:
            return b"north"
        case Direction.SOUTH:
            return b"south"
        case Direction.EAST:
            return b"east"
        case Direction.WEST:
            return b"west"


def encode_game_state(game_state: dict[str, PlayerView]) -> dict[str, bytes]:
    encoded_game_state = {}

    for player_id, player_view in game_state.items():
        encoded_game_state[player_id] = _encode_game(player_id, player_view)

    return encoded_game_state


"""
Bytes 0-1: Viewport width and height (2 bytes total)
Bytes 2-3: Player length (2 bytes total)
Bytes 4: Number of kills (1 byte)
Bytes 5: Player alive status (1 byte, 0 for dead, 1 for alive)
Bytes 6-...: Grid data (1 byte per tile, row-major order)
"""


def _encode_game(player_id: str, player_view: PlayerView) -> bytes:
    bytesarr = bytearray()

    # Viewport size (2 bytes)
    bytesarr.append(player_view.viewport_size[0])
    bytesarr.append(player_view.viewport_size[1])

    # Player length (2 bytes)
    player_length_to_bytes = player_view.length.to_bytes(2, byteorder="big")
    bytesarr.append(player_length_to_bytes[0])
    bytesarr.append(player_length_to_bytes[1])

    # Number of kills (1 byte)
    bytesarr.append(player_view.kills)

    # Player alive status (1 byte)
    bytesarr.append(1 if player_view.is_alive else 0)

    # Encode the grid structure as a sequence of bytes, where each tile is represented by a single byte
    for row in player_view.viewport:
        for tile in row:
            if tile.tile_type == TileType.SNAKE:
                if player_id in tile.player_ids:
                    bytesarr.append(TileType.SNAKE.value)  # Player's own snake
                else:
                    bytesarr.append(
                        TileType.OTHER_SNAKE.value
                    )  # Other player's snake (could be encoded differently if needed)
            else:
                bytesarr.append(tile.tile_type.value)

    return bytes(bytesarr)
