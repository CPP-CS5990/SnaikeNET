from snaikenet_server.game.game_state import PlayerView
from snaikenet_server.game.grid import TileType
from snaikenet_server.game.types import Direction
from snaikenet_client.types import ClientTileType, ClientGridStructure, ClientDirection
import struct
import json

from snaikenet_client.client_data import ClientGameStateFrame


def _to_json(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8") + b"\n"


"""
Bytes 0-3: sequence number (4 bytes total, big-endian)
Bytes 4-5: Viewport width and height (2 bytes total)
Bytes 6-7: Player length (2 bytes total)
Bytes 8: Number of kills (1 byte)
Bytes 9: Player alive status (1 byte, 0 for dead, 1 for alive)
Bytes 10-...: Grid data (1 byte per tile, row-major order)
"""
GAME_HEADER_SIZE = 10
PLAYER_GAME_STATE_HEADER_FORMAT = "!IBBHBB"


class ServerCodec:
    @staticmethod
    def decode_direction(data_bytes: bytes) -> Direction | None:
        data = json.loads(data_bytes.decode("utf-8"))

        if data.get("type") != "direction" or "direction" not in data:
            return None

        direction = data.get("direction")
        match direction:
            case ClientDirection.NORTH.value:
                return Direction.NORTH
            case ClientDirection.SOUTH.value:
                return Direction.SOUTH
            case ClientDirection.EAST.value:
                return Direction.EAST
            case ClientDirection.WEST.value:
                return Direction.WEST
            case _:
                return None

    @staticmethod
    def encode_player_game_state(
        player_id: str, player_view: PlayerView, sequence_number: int
    ) -> bytes:
        result_size = (
            player_view.viewport_size[0] * player_view.viewport_size[1]
            + GAME_HEADER_SIZE
        )
        result = bytearray(result_size)

        struct.pack_into(
            PLAYER_GAME_STATE_HEADER_FORMAT,
            result,
            0,
            sequence_number,
            player_view.viewport_size[0],
            player_view.viewport_size[1],
            player_view.length,
            player_view.kills,
            1 if player_view.is_alive else 0,
        )

        offset = GAME_HEADER_SIZE
        # Encode the grid structure as a sequence of bytes, where each tile is represented by a single byte
        for row in player_view.viewport:
            for tile in row:
                match tile.tile_type:
                    case TileType.EMPTY:
                        result[offset] = 0
                    case TileType.WALL:
                        result[offset] = 1
                    case TileType.FOOD:
                        result[offset] = 2
                    case TileType.SNAKE:
                        result[offset] = 3 if player_id in tile.player_ids else 4
                offset += 1

        return bytes(result)

    @staticmethod
    def udp_hole_punch_success_request(client_id: str, udp_port: int) -> bytes:
        return _to_json({"status": "ok", "uuid": client_id, "udp_port": udp_port})

    @staticmethod
    def udp_hole_punch_success_response() -> bytes:
        return _to_json({"status": "registered"})

    @staticmethod
    def error_response(reason: str) -> bytes:
        return _to_json({"status": "error", "reason": reason})


class ClientCodec:
    @staticmethod
    def decode_player_game_state(game_state_bytes: bytes) -> ClientGameStateFrame:
        seq, vp_width, vp_height, player_length, num_kills, is_alive = (
            struct.unpack_from(PLAYER_GAME_STATE_HEADER_FORMAT, game_state_bytes, 0)
        )
        grid_bytes = game_state_bytes[GAME_HEADER_SIZE:]

        grid_data: ClientGridStructure = []
        for i in range(vp_width * vp_height):
            if i % vp_width == 0:
                grid_data.append([])
            tile_byte = grid_bytes[i]
            match tile_byte:
                case 0:
                    tile = ClientTileType.EMPTY
                case 1:
                    tile = ClientTileType.WALL
                case 2:
                    tile = ClientTileType.FOOD
                case 3:
                    tile = ClientTileType.SNAKE  # Own snake
                case 4:
                    tile = ClientTileType.OTHER_SNAKE  # Other snake
                case _:
                    raise ValueError(f"Invalid tile byte: {tile_byte}")
            grid_data[-1].append(tile)

        return ClientGameStateFrame(
            sequence_number=seq,
            player_length=player_length,
            num_kills=num_kills,
            is_alive=is_alive == 1,
            grid_data=grid_data,
        )

    @staticmethod
    def new_connection_initial_tcp_message():
        return _to_json({"type": "new"})

    @staticmethod
    def hole_punch_udp_message(client_uuid: str):
        return _to_json({"type": "hole_punch", "uuid": client_uuid})

    @staticmethod
    def encode_direction(direction: ClientDirection) -> bytes:
        return _to_json(
            {
                "type": "direction",
                "direction": direction.value,
            }
        )
