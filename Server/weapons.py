import pygame
import math


class Weapon:
    def __init__(self, sprite_sheet_path, x, y, player_width, player_height, frame_width, frame_height, scale_factor=0.5, damage=10, description=""):
        # Load the sprite sheet
        self.sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        self.frames = self.load_frames(frame_width, frame_height, scale_factor)
        self.current_frame = 0
        self.animation_speed = 0.1  # Time per frame in seconds
        self.animation_timer = 0

        # Weapon attributes
        self.damage = damage
        self.description = description

        self.width = player_width
        self.height = player_height

    def load_frames(self, frame_width, frame_height, scale_factor):
        """Extract individual frames from the sprite sheet and apply scaling."""
        frames = []
        sheet_width, sheet_height = self.sprite_sheet.get_size()
        for y in range(0, sheet_height, frame_height):
            for x in range(0, sheet_width, frame_width):
                frame = self.sprite_sheet.subsurface((x, y, frame_width, frame_height))
                frame = pygame.transform.scale(
                    frame,
                    (int(frame_width * scale_factor), int(frame_height * scale_factor))
                )
                frames.append(frame)
        return frames

    def start_slash(self):
        """Start the slash animation (for melee weapons)."""
        print(f"{self.description} slash animation started!")

    def flip_image(self, facing_left):
        """Flip the weapon image based on the player's direction."""
        weapon_image = self.frames[self.current_frame]
        if facing_left:
            weapon_image = pygame.transform.flip(weapon_image, True, False)
        return weapon_image

    def draw(self, window, camera_x, camera_y, facing_left, player_x, player_y):
        """Draw the weapon in its default position."""
        weapon_image = self.flip_image(facing_left)
        if facing_left:
            weapon_x = player_x - weapon_image.get_width() - 10
            weapon_y = player_y + weapon_image.get_height() // 4
        else:
            weapon_x = player_x + weapon_image.get_width() + 10
            weapon_y = player_y + weapon_image.get_height() // 4
        window.blit(weapon_image, (weapon_x - camera_x, weapon_y - camera_y))


class Sword(Weapon):
    def __init__(self, texture_path, slash_texture_path, x, y, player_width, player_height, scale_factor=0.7, rotation_angle=0, damage=25, range=50, attack_speed=1, description=""):
        super().__init__(texture_path, x, y, player_width, player_height, 64, 64, scale_factor, damage, description)

        # Slash animation attributes
        self.slash_frames = self.load_slash_frames(slash_texture_path, 64, 64)
        self.slash_index = 0
        self.slash_active = False
        self.slash_timer = 0
        self.slash_duration = 0.2  # Duration of the slash animation in seconds

    def load_slash_frames(self, sprite_sheet_path, frame_width=64, frame_height=64):
        """Load frames from the slash sprite sheet."""
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        frames = []
        sheet_width, sheet_height = sprite_sheet.get_size()
        for y in range(0, sheet_height, frame_height):
            for x in range(0, sheet_width, frame_width):
                frame = sprite_sheet.subsurface((x, y, frame_width, frame_height))
                frames.append(frame)
        return frames

    def start_slash(self):
        """Start the slash animation."""
        if not self.slash_active:
            self.slash_active = True
            self.slash_index = 0
            self.slash_timer = 0
            print("Slash animation started!")

    def update_slash(self, dt, player_x, player_y, facing_left, enemies, cultists):
        """Update the slash animation and check for collisions."""
        if self.slash_active:
            self.slash_timer += dt
            if self.slash_timer >= self.slash_duration:
                self.slash_active = False  # End the slash animation
            else:
                # Update the current frame of the slash animation
                self.slash_index = int((self.slash_timer / self.slash_duration) * len(self.slash_frames))

                # Check for collisions with enemies
                slash_rect = self.get_slash_rect(player_x, player_y, facing_left)
                enemies_taken_damage = []
                cultists_taken_damage = []

                for k, enemy in enemies.items():
                    if slash_rect.colliderect(enemy.get_rect()):
                        print(f"Enemy hit! Damage: {self.damage}")
                        enemies_taken_damage.append([k, self.damage])
                        # enemy.take_damage(self.damage)

                for k, enemy in cultists.items():
                    if slash_rect.colliderect(enemy.get_rect()):
                        print(f"Cultist hit! Damage: {self.damage}")
                        cultists_taken_damage.append([k, self.damage])

                return enemies_taken_damage, cultists_taken_damage
        return None


    def get_slash_rect(self, player_x, player_y, facing_left):
        """Get the rectangle of the current slash frame."""
        slash_frame = self.slash_frames[self.slash_index]
        slash_width, slash_height = slash_frame.get_size()
        if facing_left:
            return pygame.Rect(player_x - self.width, player_y + self.height // 4, slash_width, slash_height)
        else:
            return pygame.Rect(player_x + self.width + 10, player_y + self.height // 4, slash_width, slash_height)

        
    def draw(self, window, camera_x, camera_y, facing_left, player_x, player_y):
        """Draw the sword or the slash animation."""
        if self.slash_active:
            # Draw the slash animation
            slash_frame = self.slash_frames[self.slash_index]
            if facing_left:
                slash_frame = pygame.transform.flip(slash_frame, True, False)
                slash_x = player_x - self.width - 10
            else:
                slash_x = player_x + self.width + 10
            slash_y = player_y + self.height // 4
            window.blit(slash_frame, (slash_x - camera_x, slash_y - camera_y))
        else:
            super().draw(window, camera_x, camera_y, facing_left, player_x, player_y)


class Bow(Weapon):
    def __init__(self, texture_path, x, y, player_width, player_height, scale_factor=0.5, rotation_angle=0, damage=15, range=300, attack_speed=1.5, description=""):
        super().__init__(texture_path, x, y, player_width, player_height, 64, 64, scale_factor, damage, description)

    # Additional functionality for the bow (e.g., shooting arrows) can be added here


class Weapons:
    def __init__(self, player_width, player_height):
        # Initialize a list of weapons
        self.weapons = [
            Bow("Game_models/Weapons/Bow.png", 0, 0, player_width, player_height, damage=15, range=300, attack_speed=1.5, description="A ranged weapon for long-distance attacks."),
            Sword("Game_models/Weapons/Sword.png",
                  "Game_models/Animations/Slash.png", 0, 0, player_width, player_height, rotation_angle=-80, damage=1, range=50, attack_speed=1.0, description="A melee weapon for close combat.")
        ]
        self.active_weapon_index = 0 

    def switch_weapon(self, index):
        """Switch to a weapon by index."""
        if 0 <= index < len(self.weapons):
            self.active_weapon_index = index

    def update_position(self, player_x, player_y):
        """Update the position of all weapons to follow the player."""
        for weapon in self.weapons:
            weapon.x = player_x
            weapon.y = player_y

    def draw(self, window, camera_x, camera_y, facing_left, player_x, player_y):
        """Draw the currently active weapon."""
        active_weapon = self.weapons[self.active_weapon_index]
        active_weapon.draw(window, camera_x, camera_y, facing_left, player_x, player_y)