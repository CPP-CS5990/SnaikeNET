from loguru import logger

from snakenet.game.game import _GameState


def test__game_state_player_initialization():
    logger.info("Testing game state player initialization...\n")
    grid_size = (101, 80)
    game_state = _GameState(grid_size)

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
            assert positions[i] != positions[j], f"Players {i + 1} and {j + 1} have the same initial position!"

