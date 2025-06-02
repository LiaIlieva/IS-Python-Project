import pygame
import math

ZOMBIE_SPRITE_PATH = "Game_models/Monsters/Zombie/Zombie.png"
CULTIST_SPRITE_PATH = "Game_models/Monsters/Cultist.png"
INITIAL_PLAYER_SPRITE_PATH = "Game_models/Characters/Player.png"
OTHER_PLAYER_1_SPRITE_PATH = "Game_models/Characters/other_player1.png"
OTHER_PLAYER_2_SPRITE_PATH = "Game_models/Characters/other_player2.png"

class Entity:
    def __init__(self, sprite_sheet_path, x, y, speed, frame_width, frame_height, scale_factor=2, max_health=100, load_sprites=True):
        # Load the sprite sheet
        if load_sprites:
            self.sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scale_factor = scale_factor

        # Extract frames from the sprite sheet
        if load_sprites:
            self.frames = self.extract_frames()
        self.current_frame = 0
        self.animation_speed = 0.1  # Adjust for slower or faster animation
        self.animation_timer = 0

        # Entity properties
        self.width = self.frame_width * scale_factor
        self.height = self.frame_height * scale_factor
        self.x = x
        self.y = y
        self.speed = speed
        self.facing_left = False  # Track the direction the entity is facing

        # Health system
        self.max_health = max_health
        self.current_health = max_health

        # Font for health display
        if load_sprites:
            self.font = pygame.font.Font(None, 24)  # Default font, size 24

        # Weapon system
        self.weapon = None  # Default to no weapon

    def extract_frames(self):
        """Extract individual frames from the sprite sheet."""
        frames = []
        sheet_width, sheet_height = self.sprite_sheet.get_size()
        for y in range(0, sheet_height, self.frame_height):
            for x in range(0, sheet_width, self.frame_width):
                if x + self.frame_width <= sheet_width and y + self.frame_height <= sheet_height:
                    frame = self.sprite_sheet.subsurface((x, y, self.frame_width, self.frame_height))
                    frame = pygame.transform.scale(
                        frame,
                        (self.frame_width * self.scale_factor, self.frame_height * self.scale_factor)
                    )
                    frames.append(frame)
        return frames

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def update_animation(self, dt):
        """Update the animation frame based on time."""
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def draw(self, window, camera_x, camera_y):
        if not hasattr(self, 'frames') or not self.frames:
            return  # Don't draw if no frames available

            # Get the current frame
        frame = self.frames[self.current_frame]
        if self.facing_left:
            frame = pygame.transform.flip(frame, True, False)
        window.blit(frame, (self.x - camera_x, self.y - camera_y))

        # Draw health bar and health text
        self.draw_health_bar(window, camera_x, camera_y)

    def draw_health_bar(self, window, camera_x, camera_y):
        """Draw the health bar and health text above the entity."""
        bar_width = self.width
        bar_height = 5
        health_ratio = self.current_health / self.max_health

        # Draw the health bar
        pygame.draw.rect(window, (255, 0, 0), (self.x - camera_x, self.y - camera_y - 10, bar_width, bar_height))  # Red background
        pygame.draw.rect(window, (0, 255, 0), (self.x - camera_x, self.y - camera_y - 10, bar_width * health_ratio, bar_height))  # Green foreground

        if self.current_health <= 0.1 * self.max_health:  # If health is <= 10% of max health
            text_color = (255, 0, 0)  # Red
        else:
            text_color = (0, 255, 0)  # White

        # Render the health text
        health_text = f"{self.current_health}/{self.max_health}"
        text_surface = self.font.render(health_text, True, text_color)  # White text
        text_rect = text_surface.get_rect(center=(self.x - camera_x + bar_width // 2, self.y - camera_y - 20))  # Center above the health bar
        window.blit(text_surface, text_rect)

    def take_damage(self, damage):
        """Reduce health when the entity takes damage."""
        self.current_health -= damage
        if self.current_health <= 0:
            self.current_health = 0
            self.on_death()

    def on_death(self):
        """Handle entity death (to be overridden by subclasses)."""
        print(f"{self.__class__.__name__} has died.")


class Player(Entity):
    def __init__(self, x, y, speed, sprite_path, scale_factor=1, load_sprites=True):
        super().__init__(sprite_path, x, y, speed, frame_width=65, frame_height=65, scale_factor=scale_factor, max_health=100, load_sprites=load_sprites)
        self.load_sprites = load_sprites

    def move(self, keys, dt):
        dx, dy = 0, 0
        if keys[pygame.K_a]:  # Move left
            dx = -self.speed
            self.facing_left = True
        elif keys[pygame.K_d]:  # Move right
            dx = self.speed
            self.facing_left = False
        if keys[pygame.K_w]:  # Move up
            dy = -self.speed
        if keys[pygame.K_s]:  # Move down
            dy = self.speed
        super().move(dx, dy)
        if self.load_sprites:
            self.update_animation(dt)


class Zombie(Entity):
    def __init__(self, x, y, speed=1, scale_factor=1, load_sprites=True):
        super().__init__(ZOMBIE_SPRITE_PATH, x, y, speed, frame_width=65, frame_height=65, scale_factor=scale_factor, max_health=50, load_sprites=load_sprites)
        self.attack_damage = 10  # Damage dealt by the zombie
        self.attack_cooldown = 1.0  # Cooldown time between attacks (in seconds)
        self.last_attack_time = 0  # Time of the last attack
        self.attack_range = 100  # Range within which the zombie can attack
        self.original_x = x  # Store the original x position
        self.original_y = y  # Store the original y position
        self.load_sprites = load_sprites

    def follow_player(self, player_x, player_y, dt):
        """Make the zombie follow the player unless the player is within attack range."""
        # Calculate the distance to the player
        distance = math.sqrt((self.x - player_x) ** 2 + (self.y - player_y) ** 2)

        # Stop moving if the player is within attack range
        if distance <= self.attack_range:
            return

        # Otherwise, move toward the player
        dx, dy = 0, 0
        if self.x < player_x:
            dx = self.speed
            self.facing_left = False
        elif self.x > player_x:
            dx = -self.speed
            self.facing_left = True

        if self.y < player_y:
            dy = self.speed
        elif self.y > player_y:
            dy = -self.speed

        super().move(dx, dy)
        if self.load_sprites:
            self.update_animation(dt)

    def attack_player(self, coords, current_time):
        """Attack the player if within range and cooldown has passed."""
        distance = math.sqrt((self.x - coords[0]) ** 2 + (self.y - coords[1]) ** 2)
        if distance <= self.attack_range and current_time - self.last_attack_time >= self.attack_cooldown:
            if self.weapon:
                print(f"Zombie attacks with {self.weapon.description}!")
                self.weapon.start_slash()  # Trigger weapon slash animation
            #player.take_damage(self.attack_damage)
            self.last_attack_time = current_time
            # print(f"Zombie attacked Player! Player's health: {player.current_health}")
            return True
        return False

    def on_death(self):
        """Handle zombie death and respawn."""
        print(f"{self.__class__.__name__} has died. Respawning...")
        self.x = self.original_x  # Reset to original x position
        self.y = self.original_y  # Reset to original y position
        self.current_health = self.max_health  # Reset health

    def get_rect(self):
        """Return the bounding rectangle of the zombie."""
        return pygame.Rect(self.x, self.y, self.width, self.height)


class Cultist(Entity):
    def __init__(self, x, y, speed=2, scale_factor=1, load_sprites=True):
        super().__init__(CULTIST_SPRITE_PATH, x, y, speed, frame_width=65, frame_height=65, scale_factor=scale_factor, max_health=100, load_sprites=load_sprites)
        self.attack_damage = 15  # Damage dealt by the cultist
        self.attack_cooldown = 1.5  # Cooldown time between attacks (in seconds)
        self.last_attack_time = 0  # Time of the last attack
        self.attack_range = 120  # Range within which the cultist can attack
        self.original_x = x  # Store the original x position
        self.original_y = y  # Store the original y position
        self.load_sprites = load_sprites


    def follow_player(self, player_x, player_y, dt):
        """Make the cultist follow the player unless the player is within attack range."""
        # Calculate the distance to the player
        distance = math.sqrt((self.x - player_x) ** 2 + (self.y - player_y) ** 2)

        # Stop moving if the player is within attack range
        if distance <= self.attack_range:
            return

        # Otherwise, move toward the player
        dx, dy = 0, 0
        if self.x < player_x:
            dx = self.speed
            self.facing_left = False
        elif self.x > player_x:
            dx = -self.speed
            self.facing_left = True

        if self.y < player_y:
            dy = self.speed
        elif self.y > player_y:
            dy = -self.speed

        super().move(dx, dy)
        if self.load_sprites:
            self.update_animation(dt)

    def attack_player(self, coords, current_time):
        """Attack the player if within range and cooldown has passed."""
        distance = math.sqrt((self.x - coords[0]) ** 2 + (self.y - coords[1]) ** 2)
        if distance <= self.attack_range and current_time - self.last_attack_time >= self.attack_cooldown:
            if self.weapon:
                print(f"Cultist attacks with {self.weapon.description}!")
                # Add logic for bow attack (e.g., shooting arrows)
            #player.take_damage(self.attack_damage)
            self.last_attack_time = current_time
            #print(f"Cultist attacked Player! Player's health: {player.current_health}")
            return True
        return False

    def on_death(self):
        """Handle cultist death and respawn."""
        print(f"{self.__class__.__name__} has died. Respawning...")
        self.x = self.original_x  # Reset to original x position
        self.y = self.original_y  # Reset to original y position
        self.current_health = self.max_health  # Reset health

    def get_rect(self):
        """Return the bounding rectangle of the cultist."""
        return pygame.Rect(self.x, self.y, self.width, self.height)