import struct

import json
from snaikenet_server.game.game_state import PlayerView
from snaikenet_server.game.grid import TileType, TileData
from snaikenet_client.types import ClientTileType

from snaikenet_protocol.protocol import (
    ServerCodec,
    ClientCodec
)
from snaikenet_client.types import ClientDirection
from snaikenet_server.game.types import Direction


def test_encode_player_game_state():
    player_id = "player1"
    player_view = PlayerView(
        viewport_size=(3, 5),
        viewport=[
            [
                TileData(TileType.EMPTY),
                TileData(TileType.FOOD),
                TileData(TileType.WALL),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player1"]),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.FOOD),
                TileData(TileType.WALL),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player2"]),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player3"]),
            ],
        ],
        length=3,
        kills=1,
        is_alive=True,
    )

    encoded = ServerCodec.encode_player_game_state(player_id, player_view, sequence_number=42)

    assert len(encoded) == 10 + 3 * 5

    seq, width, height, length, kills, alive = struct.unpack_from("!IBBHBB", encoded, 0)
    assert seq == 42
    assert width == 3
    assert height == 5
    assert length == 3
    assert kills == 1
    assert alive == 1

    grid = encoded[10:]
    assert grid[0] == 0  # EMPTY
    assert grid[1] == 2  # FOOD
    assert grid[2] == 1  # WALL
    assert grid[3] == 0  # EMPTY
    assert grid[4] == 1  # WALL
    assert grid[5] == 3  # SNAKE - own (player1)
    assert grid[6] == 0  # EMPTY
    assert grid[7] == 2  # FOOD
    assert grid[8] == 1  # WALL
    assert grid[9] == 0  # EMPTY
    assert grid[10] == 1  # WALL
    assert grid[11] == 4  # SNAKE - other (player2)
    assert grid[12] == 0  # EMPTY
    assert grid[13] == 1  # WALL
    assert grid[14] == 4  # SNAKE - other (player3)


def test_decode_player_game_state():
    player_id = "player1"
    player_view = PlayerView(
        viewport_size=(3, 5),
        viewport=[
            [
                TileData(TileType.EMPTY),
                TileData(TileType.FOOD),
                TileData(TileType.WALL),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player1"]),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.FOOD),
                TileData(TileType.WALL),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player2"]),
            ],
            [
                TileData(TileType.EMPTY),
                TileData(TileType.WALL),
                TileData(TileType.SNAKE, player_ids=["player3"]),
            ],
        ],
        length=3,
        kills=1,
        is_alive=True,
    )

    encoded = ServerCodec.encode_player_game_state(player_id, player_view, sequence_number=42)

    decoded = ClientCodec.decode_player_game_state(encoded)

    assert decoded.sequence_number == 42
    assert decoded.player_length == 3
    assert decoded.num_kills == 1
    assert decoded.is_alive == True
    assert len(decoded.grid_data) == 5
    assert len(decoded.grid_data[0]) == 3
    assert decoded.grid_data[0][0] == ClientTileType.EMPTY
    assert decoded.grid_data[0][1] == ClientTileType.FOOD
    assert decoded.grid_data[0][2] == ClientTileType.WALL
    assert decoded.grid_data[1][0] == ClientTileType.EMPTY
    assert decoded.grid_data[1][1] == ClientTileType.WALL
    assert decoded.grid_data[1][2] == ClientTileType.SNAKE
    assert decoded.grid_data[2][0] == ClientTileType.EMPTY
    assert decoded.grid_data[2][1] == ClientTileType.FOOD
    assert decoded.grid_data[2][2] == ClientTileType.WALL
    assert decoded.grid_data[3][0] == ClientTileType.EMPTY
    assert decoded.grid_data[3][1] == ClientTileType.WALL
    assert decoded.grid_data[3][2] == ClientTileType.OTHER_SNAKE
    assert decoded.grid_data[4][0] == ClientTileType.EMPTY
    assert decoded.grid_data[4][1] == ClientTileType.WALL
    assert decoded.grid_data[4][2] == ClientTileType.OTHER_SNAKE


def test_direction_encode_decode():
    north_encoded = ClientCodec.encode_direction(ClientDirection.NORTH)
    south_encoded = ClientCodec.encode_direction(ClientDirection.SOUTH)
    east_encoded = ClientCodec.encode_direction(ClientDirection.EAST)
    west_encoded = ClientCodec.encode_direction(ClientDirection.WEST)

    assert ServerCodec.decode_direction(north_encoded) == Direction.NORTH
    assert ServerCodec.decode_direction(south_encoded) == Direction.SOUTH
    assert ServerCodec.decode_direction(east_encoded) == Direction.EAST
    assert ServerCodec.decode_direction(west_encoded) == Direction.WEST


def test_invalid_direction_decode():
    invalid_type = _to_json({"type": "new", "direction": "NORTH"})
    no_direction = _to_json({"type": "direction"})
    invalid_direction = _to_json({"type": "direction", "direction": 6})
    assert ServerCodec.decode_direction(invalid_type) is None
    assert ServerCodec.decode_direction(no_direction) is None
    assert ServerCodec.decode_direction(invalid_direction) is None


def _to_json(dict_obj):
    return json.dumps(dict_obj).encode("utf-8")
