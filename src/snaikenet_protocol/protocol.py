from enum import Enum

from snaikenet_server.game.game_state import PlayerView
from snaikenet_server.game.grid import TileType
from snaikenet_server.game.types import Direction
from snaikenet_client.types import ClientTileType, ClientGridStructure, ClientDirection
import struct
import json
import time
import zlib

from loguru import logger

from snaikenet_client.client_data import ClientGameStateFrame


def _to_json(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8") + b"\n"


class UdpMsgType(Enum):
    # Additional header formats shouldn't include the order since the header already specifies it, and should be in network byte order (big-endian)
    GAME_STATE_FRAME_UPDATE = (
        0x01,
        "!IHHHBBB",
    )  # sequence number, viewport width, viewport height, player length, num kills, is alive. Followed by grid data (1 byte per tile, row-major order)
    GAME_START = (0x02, "!HH")  # viewport width, viewport height
    GAME_END = (0x03, None)
    GAME_RESTART = (0x04, None)
    GAME_ABOUT_TO_START = (0x05, "!B")  # seconds until start

    def __init__(self, type_id: int, additional_header_fmt: str | None):
        self.type_id = type_id
        self.additional_header_fmt = additional_header_fmt
        self.additional_header_size = (
            struct.calcsize(additional_header_fmt) if additional_header_fmt else 0
        )

    @property
    def full_fmt(self) -> str:
        if self.additional_header_fmt is None:
            return _HEADER_MSG_TYPE_FMT
        return _HEADER_MSG_TYPE_FMT + self.additional_header_fmt.lstrip("!")

    @property
    def full_size(self) -> int:
        return struct.calcsize(self.full_fmt)

    def pack_into(self, buffer: bytearray, offset: int, *args):
        struct.pack_into(self.full_fmt, buffer, offset, self.type_id, *args)

    # Unpacking the additional header fields (not including the message type) from the data
    def unpack_from(self, data: bytes) -> tuple:
        if self.additional_header_fmt is None:
            logger.warning(f"Trying to unpack additional header for message type {self.name} which has no additional header")
            raise ValueError(f"Additional header not set")
        return struct.unpack_from(
            self.additional_header_fmt, data, _HEADER_MSG_TYPE_SIZE
        )

    @classmethod
    def peek_msg_type(cls, data: bytes, offset: int = 0) -> UdpMsgType:
        # Peek the message type from the data without fully unpacking it
        (type_id,) = struct.unpack_from(_HEADER_MSG_TYPE_FMT, data, offset)
        if type_id not in _MSG_BY_ID:
            raise ValueError(f"Unknown message type ID: {type_id}")
        return _MSG_BY_ID[type_id]


_HEADER_MSG_TYPE_FMT = "!B"  # Message type (1 byte, unsigned char)
_HEADER_MSG_TYPE_SIZE = struct.calcsize(_HEADER_MSG_TYPE_FMT)
_MSG_BY_ID: dict[int, UdpMsgType] = {m.type_id: m for m in UdpMsgType}


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
    def udp_hole_punch_success_request(client_id: str, udp_port: int) -> bytes:
        return _to_json({"status": "ok", "uuid": client_id, "udp_port": udp_port})

    @staticmethod
    def udp_hole_punch_success_response() -> bytes:
        return _to_json({"status": "registered"})

    @staticmethod
    def error_response(reason: str) -> bytes:
        return _to_json({"status": "error", "reason": reason})

    @staticmethod
    def encode_player_game_state(
        player_id: str, player_view: PlayerView, sequence_number: int
    ) -> bytes:
        header_size = UdpMsgType.GAME_STATE_FRAME_UPDATE.full_size
        header = bytearray(header_size)

        UdpMsgType.GAME_STATE_FRAME_UPDATE.pack_into(
            header,
            0,
            sequence_number,
            player_view.viewport_size[0],
            player_view.viewport_size[1],
            player_view.length,
            player_view.kills,
            1 if player_view.is_alive else 0,
            1 if player_view.is_spectating else 0,
        )

        t_grid = time.perf_counter()
        grid_bytes = bytearray(
            player_view.viewport_size[0] * player_view.viewport_size[1]
        )
        offset = 0
        for row in player_view.viewport:
            for tile in row:
                grid_bytes[offset] = tile.tile_type
                if tile.tile_type == TileType.SNAKE:
                    grid_bytes[offset] = ClientTileType.SNAKE if player_id in tile.player_ids else ClientTileType.OTHER_SNAKE
                offset += 1
        grid_ms = (time.perf_counter() - t_grid) * 1000
        logger.debug("grid serialization: {:.3f}ms", grid_ms)

        t0 = time.perf_counter()
        compressed_grid = zlib.compress(bytes(grid_bytes))
        compress_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "zlib compress: {}B -> {}B ({:.1f}%) in {:.3f}ms",
            len(grid_bytes),
            len(compressed_grid),
            len(compressed_grid) / len(grid_bytes) * 100,
            compress_ms,
        )
        return bytes(header) + compressed_grid

    @staticmethod
    def encode_game_start(viewport_size: tuple[int, int]) -> bytes:
        message = bytearray(UdpMsgType.GAME_START.full_size)
        UdpMsgType.GAME_START.pack_into(
            message,
            0,
            viewport_size[0],
            viewport_size[1],
        )
        return bytes(message)

    @staticmethod
    def encode_game_end() -> bytes:
        message = bytearray(UdpMsgType.GAME_END.full_size)
        UdpMsgType.GAME_END.pack_into(message, 0)
        return bytes(message)

    @staticmethod
    def encode_game_restart() -> bytes:
        message = bytearray(UdpMsgType.GAME_RESTART.full_size)
        UdpMsgType.GAME_RESTART.pack_into(message, 0)
        return bytes(message)

    @staticmethod
    def encode_game_about_to_start(seconds_until_start: int):
        message = bytearray(UdpMsgType.GAME_ABOUT_TO_START.full_size)
        UdpMsgType.GAME_ABOUT_TO_START.pack_into(
            message,
            0,
            seconds_until_start,
        )
        return bytes(message)


class ClientCodec:
    @staticmethod
    def peek_udp_msg_type(message_bytes: bytes) -> UdpMsgType:
        return UdpMsgType.peek_msg_type(message_bytes)

    @staticmethod
    def decode_player_game_state(message_bytes: bytes) -> ClientGameStateFrame:
        message_type = UdpMsgType.peek_msg_type(message_bytes)  # Validate message type

        if message_type != UdpMsgType.GAME_STATE_FRAME_UPDATE:
            raise ValueError(
                f"Invalid message type for game state frame: {message_type}"
            )

        header_size = UdpMsgType.GAME_STATE_FRAME_UPDATE.full_size
        seq, vp_width, vp_height, player_length, num_kills, is_alive, is_spectating = (
            UdpMsgType.GAME_STATE_FRAME_UPDATE.unpack_from(message_bytes)
        )

        compressed_grid = message_bytes[header_size:]
        t0 = time.perf_counter()
        grid_bytes = zlib.decompress(compressed_grid)
        decompress_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "zlib decompress: {}B -> {}B in {:.3f}ms",
            len(compressed_grid),
            len(grid_bytes),
            decompress_ms,
        )

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
            is_spectating=is_spectating,
        )

    @staticmethod
    def decode_game_start(message_bytes: bytes) -> tuple[int, int]:
        message_type = UdpMsgType.peek_msg_type(message_bytes)  # Validate message type

        if message_type != UdpMsgType.GAME_START:
            raise ValueError(f"Invalid message type for game start: {message_type}")

        vp_width, vp_height = UdpMsgType.GAME_START.unpack_from(message_bytes)

        return vp_width, vp_height

    @staticmethod
    def decode_game_about_to_start(message_bytes: bytes) -> int:
        message_type = UdpMsgType.peek_msg_type(message_bytes)  # Validate message type

        if message_type != UdpMsgType.GAME_ABOUT_TO_START:
            raise ValueError(
                f"Invalid message type for game about to start: {message_type}"
            )

        (seconds_until_start,) = UdpMsgType.GAME_ABOUT_TO_START.unpack_from(
            message_bytes
        )

        return seconds_until_start

    @staticmethod
    def new_connection_initial_tcp_message(spectator: bool = False) -> bytes:
        return _to_json({"type": "new", "spectator": spectator})

    @staticmethod
    def reconnect_initial_tcp_message(uuid: str):
        return _to_json({"type": "reconnect", "uuid": uuid})

    @staticmethod
    def hole_punch_udp_message(client_uuid: str) -> bytes:
        return _to_json({"type": "hole_punch", "uuid": client_uuid})

    @staticmethod
    def encode_direction(direction: ClientDirection) -> bytes:
        return _to_json(
            {
                "type": "direction",
                "direction": direction.value,
            }
        )

    @staticmethod
    def heartbeat_message():
        return _to_json({"type": "heartbeat"})
