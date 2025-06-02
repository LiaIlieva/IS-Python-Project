import pygame
import time
import sys
import asyncio

async def show_waiting_screen(win, WIDTH, HEIGHT, game_started_event):

    # Font and text settings
    font = pygame.font.SysFont("arial", 36)
    base_text = "Waiting for players"
    dot_count = 0

    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    last_update_time = time.time()

    while not game_started_event.is_set():
        win.fill(BLACK)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Update dots every 0.5 seconds
        if time.time() - last_update_time > 0.5:
            dot_count = (dot_count + 1) % 4  # cycle through 0 to 3
            last_update_time = time.time()

        # Render text
        display_text = base_text + ("." * dot_count)
        text_surface = font.render(display_text, True, WHITE)
        text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        win.blit(text_surface, text_rect)

        pygame.display.flip()
        # Yield control back to asyncio event loop
        await asyncio.sleep(0.01)  # Small delay to prevent blocking

