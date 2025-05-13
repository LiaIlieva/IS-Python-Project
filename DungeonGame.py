import pygame
import sys
import os
import time
from Entities import Player, Zombie, Cultist
from weapons import Weapons
from UI import Inventory

os.chdir("d:/Downloads/Dungeon game")

# Initialize Pygame
pygame.init()
# Set up display
WIDTH, HEIGHT = 1920, 1080
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dungeon Game")

# Load ground model
ground_image = pygame.image.load("Game models/Ground/ground.png").convert_alpha()
ground_width, ground_height = ground_image.get_width(), ground_image.get_height()

# Initialize player, zombie, weapons, and inventory
player = Player(x=0, y=0, speed=5)
zombie = Zombie(x=200, y=200)
cultist = Cultist(x=300, y=300)  # Assuming you have a Cultist class defined
weapons = Weapons(player_width=player.width, player_height=player.height)
inventory = Inventory(screen_width=WIDTH, screen_height=HEIGHT)

# Camera setup
camera_x = 0
camera_y = 0

# Initialize clock for delta time
clock = pygame.time.Clock()

# Create a lighting surface
lighting_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

def draw_lighting_effect():
    """Draw the lighting effect with a fading yellow circle around the player."""
    # Fill the surface with a semi-transparent black color
    lighting_surface.fill((0, 0, 0, 220))  # RGBA: Black with 220 alpha (semi-transparent)

    # Draw a fading yellow circle around the player
    light_radius = 200  # Radius of the light
    for i in range(light_radius, 0, -1):  # Create a gradient effect
        alpha = int(100 * (i / light_radius))  # Calculate alpha based on distance
        pygame.draw.circle(
            lighting_surface,
            (255, 255, 0, alpha),  # Yellow with calculated alpha
            (player.x - camera_x + player.width // 2, player.y - camera_y + player.height // 2),
            i
        )

    # Blit the lighting surface onto the main window
    window.blit(lighting_surface, (0, 0))

# Game loop
running = True
while running:
    dt = clock.tick(60) / 1000  # Delta time in seconds (60 FPS)
    current_time = pygame.time.get_ticks() / 1000  # Current time in seconds

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Switch weapons based on key press
            if event.key == pygame.K_1:
                weapons.switch_weapon(0)
                inventory.select_slot(0)
            elif event.key == pygame.K_2:
                weapons.switch_weapon(1)
                inventory.select_slot(1)
            elif event.key == pygame.K_3:
                weapons.switch_weapon(2)
                inventory.select_slot(2)
        # Trigger sword attack
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if weapons.active_weapon_index == 1:  # Assuming the sword is at index 1
                weapons.weapons[1].start_slash()

    # Get keys
    keys = pygame.key.get_pressed()
    player.move(keys, dt)

    # Update camera position to follow the player
    camera_x = player.x - WIDTH // 2
    camera_y = player.y - HEIGHT // 2

    # Make the zombie follow the player and attack if close
    zombie.follow_player(player.x, player.y, dt)
    zombie.attack_player(player, current_time)

    cultist.follow_player(player.x, player.y, dt)  # Assuming you have a follow method for cultist
    cultist.attack_player(player, current_time)  # Assuming you have an attack method for cultista

    # Check if the player is dead
    if player.current_health <= 0:
        print("Game Over! The player has died.")
        running = False  # End the game loop

   
    # Draw the ground (repeating pattern)
    for x in range(-ground_width, WIDTH + ground_width, ground_width):
        for y in range(-ground_height, HEIGHT + ground_height, ground_height):
            window.blit(ground_image, (x - camera_x % ground_width, y - camera_y % ground_height))

    # Update weapon position
    weapons.update_position(player.x, player.y)

    # Update the slash animation
    weapons.weapons[1].update_slash(dt, player.x, player.y, player.facing_left, [zombie, cultist])

    # Draw the player, zombie, and weapons
    player.draw(window, camera_x, camera_y)
    zombie.draw(window, camera_x, camera_y)
    cultist.draw(window, camera_x, camera_y)  # Assuming you have a cultist object
    weapons.draw(window, camera_x, camera_y, player.facing_left, player.x, player.y)  # Removed player.width

    # Draw the lighting effect
    draw_lighting_effect()

    # Draw the inventory (UI) after the lighting effect
    inventory.draw(window)

    # Update the display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
sys.exit()