# WARNING: This is mostly AI generated code. This is just to prototype the backend game logic with a pygame frontend. It also allows for manual testing
# No need to polish this code
import sys
import pygame
from snakenet.game.game import Game, PlayerID, GridSize, TileType
from snakenet.game.types import Direction

# Colors
BG_COLOR = (15, 15, 20)
GRID_LINE_COLOR = (30, 30, 40)
FOOD_COLOR = (220, 50, 50)
FOOD_GLOW = (255, 80, 80)
TEXT_COLOR = (200, 200, 210)
DEAD_OVERLAY = (255, 60, 60, 80)

SNAKE_PALETTES = [
    {"body": (80, 200, 120), "head": (50, 240, 100)},   # green
    {"body": (100, 140, 230), "head": (70, 120, 255)},   # blue
    {"body": (230, 180, 60), "head": (255, 210, 40)},     # gold
    {"body": (200, 100, 200), "head": (240, 120, 240)},   # purple
]

CELL_SIZE = 24
SIDEBAR_WIDTH = 220
GRID_COLS = 100
GRID_ROWS = 80
FPS = 3  # game ticks per second


def render_game(screen: pygame.Surface, game: Game, player_ids: list[PlayerID], font: pygame.font.Font):
    gs = game.game_state
    gx, gy = gs.get_grid_size()
    game_area_w = gx * CELL_SIZE
    game_area_h = gy * CELL_SIZE

    screen.fill(BG_COLOR)

    # ── Grid lines ──
    for x in range(gx + 1):
        pygame.draw.line(screen, GRID_LINE_COLOR, (x * CELL_SIZE, 0), (x * CELL_SIZE, game_area_h))
    for y in range(gy + 1):
        pygame.draw.line(screen, GRID_LINE_COLOR, (0, y * CELL_SIZE), (game_area_w, y * CELL_SIZE))

    # ── Tiles ──
    for i, tile in enumerate(gs.get_grid_iterator()):
        if tile.tile_type == TileType.FOOD:
            x, y = i % gx, i // gx
            rect = pygame.Rect(x * CELL_SIZE + 4, y * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8)
            pygame.draw.ellipse(screen, FOOD_GLOW, rect.inflate(8, 8))
            pygame.draw.ellipse(screen, FOOD_COLOR, rect)

    # ── Snakes ──
    for idx, pid in enumerate(player_ids):
        player = gs.get_player(pid)
        if player is None:
            continue
        palette = SNAKE_PALETTES[idx % len(SNAKE_PALETTES)]

        for i, (sx, sy) in enumerate(player):
            rect = pygame.Rect(sx * CELL_SIZE + 1, sy * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2)
            if i == 0:
                # Head: brighter, rounded
                color = palette["head"]
                pygame.draw.rect(screen, color, rect, border_radius=8)
                # Eyes
                cx, cy_px = rect.centerx, rect.centery
                dx, dy = player.get_direction().value
                eye_off = 4
                if dx == 0:  # vertical movement — eyes side by side
                    pygame.draw.circle(screen, (20, 20, 20), (cx - eye_off, cy_px + dy * 3), 3)
                    pygame.draw.circle(screen, (20, 20, 20), (cx + eye_off, cy_px + dy * 3), 3)
                else:  # horizontal movement — eyes stacked
                    pygame.draw.circle(screen, (20, 20, 20), (cx + dx * 3, cy_px - eye_off), 3)
                    pygame.draw.circle(screen, (20, 20, 20), (cx + dx * 3, cy_px + eye_off), 3)
            else:
                # Body: gradient fade toward tail
                t = i / max(i, 1)
                fade = 1.0 - t * 0.5
                color = tuple(int(c * fade) for c in palette["body"])
                pygame.draw.rect(screen, color, rect, border_radius=4)

    # ── Sidebar ──
    sidebar_x = game_area_w + 16
    sidebar_rect = pygame.Rect(game_area_w, 0, SIDEBAR_WIDTH, game_area_h)
    pygame.draw.rect(screen, (20, 20, 28), sidebar_rect)
    pygame.draw.line(screen, (40, 40, 55), (game_area_w, 0), (game_area_w, game_area_h), 2)

    title_surf = font.render("SNAKENET", True, (180, 180, 200))
    screen.blit(title_surf, (sidebar_x, 20))

    y_offset = 60
    small_font = pygame.font.SysFont("monospace", 14)

    for idx, pid in enumerate(player_ids):
        player = gs.get_player(pid)
        if player is None:
            continue
        palette = SNAKE_PALETTES[idx % len(SNAKE_PALETTES)]
        status = "ALIVE"
        color = palette["head"]

        # Color swatch
        pygame.draw.rect(screen, color, (sidebar_x, y_offset, 12, 12), border_radius=2)

        label = f"P{idx + 1}: {player}pts  {status}"
        label_surf = small_font.render(label, True, color)
        screen.blit(label_surf, (sidebar_x + 20, y_offset - 1))
        y_offset += 28

    # Controls
    y_offset += 20
    controls = [
        "─── CONTROLS ───",
        "P1: W A S D",
        "P2: Arrow Keys",
        "",
        "R: Restart",
        "ESC: Quit",
    ]
    for line in controls:
        surf = small_font.render(line, True, (100, 100, 120))
        screen.blit(surf, (sidebar_x, y_offset))
        y_offset += 20

    # Game over overlay
    overlay = pygame.Surface((game_area_w, game_area_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))
    big_font = pygame.font.SysFont("monospace", 48, bold=True)
    go_surf = big_font.render("GAME OVER", True, (255, 80, 80))
    go_rect = go_surf.get_rect(center=(game_area_w // 2, game_area_h // 2 - 20))
    screen.blit(go_surf, go_rect)
    restart_surf = small_font.render("Press R to restart", True, (180, 180, 180))
    r_rect = restart_surf.get_rect(center=(game_area_w // 2, game_area_h // 2 + 30))
    screen.blit(restart_surf, r_rect)


# ──────────────────────────────────────────────────────────────────────
# Key mappings
# ──────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def create_and_start_game(num_players: int = 2) -> tuple[Game, list[PlayerID]]:
    grid_size: GridSize = (GRID_COLS, GRID_ROWS)
    game = Game(grid_size)
    player_ids = [game.game_state.add_new_player() for _ in range(num_players)] # add players to game state and keep track of their IDs
    game.start_game()
    return game, player_ids


def main():
    pygame.init()

    game_area_w = GRID_COLS * CELL_SIZE
    game_area_h = GRID_ROWS * CELL_SIZE
    screen_w = game_area_w + SIDEBAR_WIDTH
    screen_h = game_area_h

    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("SnakeNet — Pygame")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 22, bold=True)

    game, player_ids = create_and_start_game(num_players=2)
    key_maps = [P1_KEYS, P2_KEYS]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game, player_ids = create_and_start_game(num_players=2)
                else:
                    # Route key presses to the correct player
                    for idx, km in enumerate(key_maps):
                        if event.key in km and idx < len(player_ids):
                            player = game.game_state.get_player(player_ids[idx])
                            if player:
                                player.set_direction(km[event.key])

        if game.is_running():
            game.tick()

        render_game(screen, game, player_ids, font)
        pygame.display.flip()
        clock.tick(FPS)

    game.stop_game()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
