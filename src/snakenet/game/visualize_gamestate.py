from numpy.random import randint

from snakenet.game.game import _GameState

def main():
    import pygame
    import sys

    # Config
    grid_size = (130, 130)
    tile_px = 13
    num_players = 8

    pygame.init()
    screen = pygame.display.set_mode((grid_size[0] * tile_px, grid_size[1] * tile_px))
    pygame.display.set_caption("GameState Visualizer")

    # Setup
    state = _GameState(grid_size)
    for _ in range(num_players):
        state.add_new_player()
    state.initialize_game_state()

    # Colors
    bg = (30, 30, 30)
    grid_line = (50, 50, 50)
    player_colors = [
        (randint(255), randint(255), randint(255)) for _ in range(num_players)
    ]

    screen.fill(bg)

    # Draw grid lines
    for x in range(grid_size[0]):
        for y in range(grid_size[1]):
            rect = pygame.Rect(x * tile_px, y * tile_px, tile_px, tile_px)
            pygame.draw.rect(screen, grid_line, rect, 1)

    # Draw players
    font = pygame.font.SysFont(None, 14)
    for i, (uid, player) in enumerate(state._players.items()):
        px, py = player.get_head_position()
        color = player_colors[i % len(player_colors)]
        rect = pygame.Rect(px * tile_px, py * tile_px, tile_px, tile_px)
        pygame.draw.rect(screen, color, rect)
        label = font.render(str(i), True, (0, 0, 0))
        screen.blit(label, (px * tile_px + 4, py * tile_px + 4))

    pygame.display.flip()

    # Hold window open
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                sys.exit()


if __name__ == "__main__":
    main()