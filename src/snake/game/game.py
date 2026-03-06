from enum import Enum
from loguru import logger
import numpy as np
from snake.game.player import SnakePlayer
import threading
import uuid

type Location = tuple[int, int]
type GridSize = tuple[int, int]

class Game:
    game_state: _GameState
    game_not_stopped: bool = True
    _start_event: threading.Event
    _available_food_locations: set[Location] # TODO: Probably change to list, evaluate later

    def __init__(self, grid_size: GridSize):
        self._start_event = threading.Event()

    def start_game(self):
        logger.debug("Start event received, starting game loop...\n")
        self._start_event.set()

    def stop_game(self):
        logger.debug("Stop event received, stopping game loop...\n")
        self._start_event.set() # Set the event to unblock the game loop if it's waiting

    def wait_for_game_start(self):
        logger.debug("Waiting for start event...\n")
        self._start_event.wait()

    def restart_game(self):
        # TODO: Implement
        pass

class _TileType(Enum):
    EMPTY = 0
    FOOD = 1
    SNAKE = 2

class TileData:
    tile_type: _TileType
    player_id: str | None

    def __init__(self, tile_type: _TileType = _TileType.EMPTY, player_id: str | None = None):
        self.tile_type = tile_type
        self.player_id = player_id

type PlayerID = str

class _GameState:
    players: dict[PlayerID, SnakePlayer]
    grid_size: GridSize
    grid: list[list[TileData]]

    def __init__(self, grid_size: GridSize):
        self.grid_size = grid_size
        self.players = {}
        self.grid = [[TileData(tile_type=_TileType.EMPTY, player_id=None) for _ in range(grid_size[1])] for _ in range(grid_size[0])]

    # Adds a new player to the game state. The player is initialized to 0, 0 but will be assigned at game start.
    def add_new_player(self) -> PlayerID:
        player_id = str(uuid.uuid4())
        self.players[player_id] = SnakePlayer(initial_position=(0, 0)) # TODO: Change to random position
        return player_id

    def delete_player(self, player_id: str) -> bool:
        if player_id not in self.players:
            return False
        del self.players[player_id]
        return True

    # Run right before the game loop starts to initialize the game state
    # Can't run immediately because the game state is going to depend on
    # the number of players that have joined, and we want to allow players 
    # to join before the game starts
    def initialize_game_state(self):
        self._initialize_player_positions()


    def _initialize_player_positions(self):
        num_players = len(self.players)
        grid_size_padded = (int(self.grid_size[0] * 0.6), int(self.grid_size[1] * 0.6))
        logger.debug(f"Initializing player positions for {num_players} players on a grid of size {self.grid_size} (padded size: {grid_size_padded})...\n")
        center_x = int((self.grid_size[0] - 1) / 2)
        center_y = int((self.grid_size[1] - 1) / 2)
        logger.debug(f"Grid center: ({center_x}, {center_y})\n")
        number_of_layers = (num_players + 3) // 4
        distance_from_center = np.sqrt(((grid_size_padded[0] / 2)-1) ** 2 + ((grid_size_padded[1] / 2)-1) ** 2) / number_of_layers
        distance_stride = distance_from_center
        logger.debug(f"Number of layers: {number_of_layers}, initial distance from center: {distance_from_center}\n")
        for i, player in enumerate(self.players.values()):
            if i % 4 == 0 and i != 0: # Every 4 players, we need to move to the next layer
                # TODO: calculate new distance from center
                distance_from_center += distance_stride
            angle = ((1 + 2*i) * np.pi) / 4
            logger.debug(f"Angle for player {i}: {angle:.2f} radians\n")
            x = center_x + distance_from_center * np.cos(angle)
            y = center_y + distance_from_center * np.sin(angle)
            player.initialize_position((int(np.round(x)), int(np.round(y))))

if __name__ == "__main__":
    import pygame
    import sys

    # Config
    GRID_SIZE = (30, 30)
    TILE_PX = 20
    NUM_PLAYERS = 8

    pygame.init()
    screen = pygame.display.set_mode((GRID_SIZE[0] * TILE_PX, GRID_SIZE[1] * TILE_PX))
    pygame.display.set_caption("GameState Visualizer")

    # Setup
    state = _GameState(GRID_SIZE)
    for _ in range(NUM_PLAYERS):
        state.add_new_player()
    state.initialize_game_state()

    # Colors
    BG = (30, 30, 30)
    GRID_LINE = (50, 50, 50)
    PLAYER_COLORS = [
        (255, 80, 80), (80, 255, 80), (80, 80, 255), (255, 255, 80),
        (255, 80, 255), (80, 255, 255), (255, 160, 80), (160, 80, 255),
    ]

    screen.fill(BG)

    # Draw grid lines
    for x in range(GRID_SIZE[0]):
        for y in range(GRID_SIZE[1]):
            rect = pygame.Rect(x * TILE_PX, y * TILE_PX, TILE_PX, TILE_PX)
            pygame.draw.rect(screen, GRID_LINE, rect, 1)

    # Draw players
    font = pygame.font.SysFont(None, 14)
    for i, (uid, player) in enumerate(state.players.items()):
        px, py = player.get_head_position()
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        rect = pygame.Rect(px * TILE_PX, py * TILE_PX, TILE_PX, TILE_PX)
        pygame.draw.rect(screen, color, rect)
        label = font.render(str(i), True, (0, 0, 0))
        screen.blit(label, (px * TILE_PX + 4, py * TILE_PX + 4))

    pygame.display.flip()

    # Hold window open
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                sys.exit()
