import pygame

class Inventory:
    def __init__(self, screen_width, screen_height):
        # Load the inventory frame texture
        self.frame_image = pygame.image.load("Game models/UI/inventory.png").convert_alpha()

        # Scale the frame to fit the desired slot size
        self.slot_size = 64  # Size of each inventory slot
        self.frame_image = pygame.transform.scale(self.frame_image, (self.slot_size, self.slot_size))

        self.frame_image.set_alpha(153)

        # Inventory layout (1 row, 3 slots for weapons)
        self.rows = 1
        self.columns = 3
        self.slots = []

        # Calculate the starting position to center the inventory on the screen
        self.start_x = (screen_width - (self.columns * self.slot_size)) // 2
        self.start_y = screen_height - (self.rows * self.slot_size) - 20

        # Generate slot positions
        for row in range(self.rows):
            for col in range(self.columns):
                x = self.start_x + col * self.slot_size
                y = self.start_y + row * self.slot_size
                self.slots.append((x, y))

        # Highlighted slot (default is the first slot)
        self.selected_slot = 0

        # Weapon textures for the inventory
        self.weapon_textures = [
            pygame.image.load("Game models/Weapons/Bow.png").convert_alpha(),
            pygame.image.load("Game models/Weapons/Sword.png").convert_alpha()
        ]

        # Scale weapon textures to fit the inventory slots
        self.weapon_textures = [
            pygame.transform.scale(texture, (self.slot_size, self.slot_size))
            for texture in self.weapon_textures
        ]

    def draw(self, window):
        # Draw each slot frame
        for i, (x, y) in enumerate(self.slots):
            if i == self.selected_slot:
                # Highlight the selected slot
                pygame.draw.rect(window, (255, 255, 0), (x - 2, y - 2, self.slot_size + 4, self.slot_size + 4), 3)
            window.blit(self.frame_image, (x, y))

            # Draw the weapon texture in the slot
            if i < len(self.weapon_textures):
                weapon_texture = self.weapon_textures[i]
                window.blit(weapon_texture, (x, y))

    def select_slot(self, index):
        # Change the selected slot
        if 0 <= index < len(self.slots):
            self.selected_slot = index