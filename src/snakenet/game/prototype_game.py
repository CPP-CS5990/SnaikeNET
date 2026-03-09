# AI generated prototype using the SnakeNet game engine, demonstrating a simple 2-player snake game with Pygame rendering.
# Not intended to be fully functional, moreso to test the game engine during development. For the most part, it should just
# be rendering the grid and responding to player input, but it may also print out when a player dies. It uses the GameState::get_grid_iterator method
import sys
import pygame
from snakenet.game.game import Game
from snakenet.game.grid import TileType
from snakenet.game.types import Direction, PlayerID

SCREEN_W = 1500
SCREEN_H = 1000

GRID_COLS = 50
GRID_ROWS = 30
FPS = 10

CELL_SIZE = min(SCREEN_W // GRID_COLS, SCREEN_H // GRID_ROWS)
GAME_W = GRID_COLS * CELL_SIZE
GAME_H = GRID_ROWS * CELL_SIZE
SIDEBAR_W = SCREEN_W - GAME_W

BG_COLOR = (15, 15, 20)
GRID_LINE_COLOR = (30, 30, 40)
FOOD_COLOR = (220, 50, 50)
SIDEBAR_COLOR = (20, 20, 30)

# One color per player slot
SNAKE_COLORS = [
    (80, 200, 120),  # P1 green
    (100, 140, 230),  # P2 blue
    (230, 180, 60),  # P3 gold
    (200, 100, 200),  # P4 purple
]

P1_KEYS = {
    pygame.K_w: Direction.NORTH,
    pygame.K_s: Direction.SOUTH,
    pygame.K_a: Direction.WEST,
    pygame.K_d: Direction.EAST,
}

P2_KEYS = {
    pygame.K_UP: Direction.NORTH,
    pygame.K_DOWN: Direction.SOUTH,
    pygame.K_LEFT: Direction.WEST,
    pygame.K_RIGHT: Direction.EAST,
}


def render_game(
    screen: pygame.Surface,
    game: Game,
    player_ids: list[PlayerID],
    dead_set: set[PlayerID],
    font: pygame.font.Font,
):
    gs = game.game_state
    _, gy = gs.get_grid_size()

    screen.fill(BG_COLOR)

    # Grid lines for tile borders
    for col in range(GRID_COLS + 1):
        lx = col * CELL_SIZE
        pygame.draw.line(screen, GRID_LINE_COLOR, (lx, 0), (lx, GAME_H))
    for row in range(GRID_ROWS + 1):
        ly = row * CELL_SIZE
        pygame.draw.line(screen, GRID_LINE_COLOR, (0, ly), (GAME_W, ly))

    pid_to_color = {
        pid: SNAKE_COLORS[i % len(SNAKE_COLORS)] for i, pid in enumerate(player_ids)
    }

    # Draw tiles using only get_grid_iterator
    for i, tile in enumerate(gs.get_grid_iterator()):
        x = i // gy
        y = i % gy
        px = x * CELL_SIZE
        py = y * CELL_SIZE

        if tile.tile_type == TileType.FOOD:
            rect = pygame.Rect(px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            pygame.draw.ellipse(screen, FOOD_COLOR, rect)
        elif tile.tile_type == TileType.SNAKE and tile.player_ids:
            color = pid_to_color.get(tile.player_ids[0], (200, 200, 200))
            rect = pygame.Rect(px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2)
            pygame.draw.rect(screen, color, rect)

    # Sidebar
    pygame.draw.rect(screen, SIDEBAR_COLOR, (GAME_W, 0, SIDEBAR_W, SCREEN_H))

    title = font.render("SNAKENET", True, (180, 180, 200))
    screen.blit(title, (GAME_W + 16, 16))

    y_off = 50
    small = pygame.font.SysFont("monospace", 13)
    for i, pid in enumerate(player_ids):
        color = SNAKE_COLORS[i % len(SNAKE_COLORS)]
        alive = pid not in dead_set
        status = "ALIVE" if alive else "DEAD"
        swatch_rect = pygame.Rect(GAME_W + 16, y_off + 1, 10, 10)
        pygame.draw.rect(screen, color, swatch_rect)
        label = small.render(
            f"P{i + 1}  {status}", True, color if alive else (100, 100, 100)
        )
        screen.blit(label, (GAME_W + 32, y_off))
        y_off += 22


def create_game(num_players: int = 2) -> tuple[Game, list[PlayerID]]:
    game = Game((GRID_COLS, GRID_ROWS))
    player_ids = [game.add_new_player() for _ in range(num_players)]
    game.start_game()
    return game, player_ids


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("SnakeNet Prototype")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 14)

    game, player_ids = create_game(num_players=2)
    key_maps = [P1_KEYS, P2_KEYS]
    dead_set: set[PlayerID] = set()
    alive_last_tick: set[PlayerID] = set(player_ids)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game, player_ids = create_game(num_players=2)
                    dead_set = set()
                    alive_last_tick = set(player_ids)
                else:
                    for idx, km in enumerate(key_maps):
                        if event.key in km and idx < len(player_ids):
                            player = game.game_state.get_player(player_ids[idx])
                            if player:
                                player.set_direction(km[event.key])

        game.tick()

        # Detect newly dead players (supplemental, not used for rendering)
        alive_now = {
            pid
            for pid in player_ids
            if (p := game.game_state.get_player(pid)) and not p.is_dead()
        }
        for pid in alive_last_tick - alive_now:
            idx = player_ids.index(pid)
            print(f"P{idx + 1} died!")
            dead_set.add(pid)
        alive_last_tick = alive_now

        render_game(screen, game, player_ids, dead_set, font)
        pygame.display.flip()
        clock.tick(FPS)

    game.stop_game()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
