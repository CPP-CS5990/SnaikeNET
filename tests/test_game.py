from loguru import logger

from snakenet.game.game import GameState, TileType
from snakenet.game.types import Direction


def test__game_state_player_initialization():
    logger.info("Testing game state player initialization...\n")
    grid_size = (101, 80)
    game_state = GameState(grid_size)

    player_uids = []

    for i in range(5):
        player_uids.append(game_state.add_new_player())
        logger.info(f"Player {i} ID: {player_uids[i]}")
        assert len(game_state._players) == i + 1, (
            f"Expected {i + 1} players, but got {len(game_state._players)}"
        )

    game_state._initialize_player_positions()

    for i, uid in enumerate(player_uids):
        logger.info(
            f"Player {i + 1} initial position: {game_state._players[uid].get_head_position()}"
        )

    # ensure that all players are initialized to unique positions and are atleast 10 tiles apart from each other
    positions = [game_state._players[uid].get_head_position() for uid in player_uids]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            assert positions[i] != positions[j], (
                f"Players {i + 1} and {j + 1} have the same initial position!"
            )


def test__game_state_move_players():
    logger.info("Testing game state player movement...\n")
    grid_size = (101, 80)
    game_state = GameState(grid_size)

    player_uids = []

    for i in range(5):
        player_uids.append(game_state.add_new_player())
        logger.info(f"Player {i} ID: {player_uids[i]}")

    game_state._initialize_player_positions()

    # Move each player in a different direction and check their new positions
    directions: list[Direction] = [
        Direction.NORTH,
        Direction.SOUTH,
        Direction.EAST,
        Direction.WEST,
        Direction.NORTH,
    ]
    player_initial_positions = [
        game_state._players[uid].get_head_position() for uid in player_uids
    ]
    player_expected_positions = [
        (player_initial_positions[0][0], player_initial_positions[0][1] - 1),  # NORTH
        (player_initial_positions[1][0], player_initial_positions[1][1] + 1),  # SOUTH
        (player_initial_positions[2][0] + 1, player_initial_positions[2][1]),  # EAST
        (player_initial_positions[3][0] - 1, player_initial_positions[3][1]),  # WEST
        (player_initial_positions[4][0], player_initial_positions[4][1] - 1),  # NORTH
    ]
    for i, uid in enumerate(player_uids):
        game_state._players[uid]._next_direction = directions[i]
        logger.info(
            f"Player {i + 1} initial position: {game_state._players[uid].get_head_position()}"
        )

    game_state.move_players()

    player_new_positions = [
        game_state._players[uid].get_head_position() for uid in player_uids
    ]
    for i, player_new_position in enumerate(player_new_positions):
        logger.info(
            f"Player {i + 1} new position: {player_new_position}, expected position: {player_expected_positions[i]}"
        )
        assert player_new_position == player_expected_positions[i], (
            f"Player {i + 1} moved to {player_new_position}, but expected {player_expected_positions[i]}"
        )

    # ensure that all players are stil the same length and that the tail is in the correct position
    for i, uid in enumerate(player_uids):
        assert game_state._players[uid].get_length() == 1, (
            f"Player {i + 1} length changed after moving!"
        )
        assert (
            game_state._players[uid].get_tail_position()
            == game_state._players[uid].get_head_position()
        ), (
            f"Player {i + 1} tail position is not the same as head position after moving!"
        )


def test__game_state_move_players_eat_food():
    logger.info("Testing game state player movement...\n")
    grid_size = (101, 80)
    game_state = GameState(grid_size)

    player_uids = []

    for i in range(5):
        player_uids.append(game_state.add_new_player())
        logger.info(f"Player {i} ID: {player_uids[i]}")

    game_state._initialize_player_positions()

    # Move each player in a different direction and check their new positions
    directions: list[Direction] = [
        Direction.NORTH,
        Direction.SOUTH,
        Direction.EAST,
        Direction.WEST,
        Direction.NORTH,
    ]
    player_initial_positions = [
        game_state._players[uid].get_head_position() for uid in player_uids
    ]
    player_expected_positions = [
        (player_initial_positions[0][0], player_initial_positions[0][1] - 1),  # NORTH
        (player_initial_positions[1][0], player_initial_positions[1][1] + 1),  # SOUTH
        (player_initial_positions[2][0] + 1, player_initial_positions[2][1]),  # EAST
        (player_initial_positions[3][0] - 1, player_initial_positions[3][1]),  # WEST
        (player_initial_positions[4][0], player_initial_positions[4][1] - 1),  # NORTH
    ]
    for i, uid in enumerate(player_uids):
        game_state._players[uid]._next_direction = directions[i]
        logger.info(
            f"Player {i + 1} initial position: {game_state._players[uid].get_head_position()}"
        )

    # Place food in the next head position of each player. This will cause each player to eat the food and grow by 1 tile when they move.
    for i, uid in enumerate(player_uids):
        # Place food in the next head position of each player
        next_head_position = game_state._players[uid].get_next_head_position()
        game_state._grid._grid[next_head_position[0]][
            next_head_position[1]
        ].tile_type = TileType.FOOD  # Set tile type to FOOD

    game_state.move_players()

    player_new_positions = [
        game_state._players[uid].get_head_position() for uid in player_uids
    ]
    for i, player_new_position in enumerate(player_new_positions):
        logger.info(
            f"Player {i + 1} new position: {player_new_position}, expected position: {player_expected_positions[i]}"
        )
        assert player_new_position == player_expected_positions[i], (
            f"Player {i + 1} moved to {player_new_position}, but expected {player_expected_positions[i]}"
        )

    # ensure that all players are now length 2 and that the tail is in the correct position
    for i, uid in enumerate(player_uids):
        assert game_state._players[uid].get_length() == 2, (
            f"Player {i + 1} length did not increase after eating food!"
        )
        assert (
            game_state._players[uid].get_tail_position() == player_initial_positions[i]
        ), (
            f"Player {i + 1} tail position is not the same as initial position after eating food!"
        )
