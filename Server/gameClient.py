import asyncio
import websockets
import requests
import json
import random
import uuid
import subprocess


from game_modes import show_waiting_screen
import pygame
import time
import sys
import webbrowser

import os
import threading

# sys.path.append(r"C:\Users\USER\Desktop\IS-Python-Project")


SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/game"

from Entities import Player, Zombie, Cultist
from weapons import Weapons
from UI import Inventory

from GameRooms import WIDTH, HEIGHT
from Entities import INITIAL_PLAYER_SPRITE_PATH, OTHER_PLAYER_1_SPRITE_PATH, OTHER_PLAYER_2_SPRITE_PATH
camera_x = 0
camera_y = 0

SPEED = 23


class GameClient:
    def __init__(self):
        self.player_id = None
        self.room_id = None
        self.wallet = None
        self.ws = None
        self.running = False
        self.game_started = False
        self.players_coord = {}  # {'dfdc056a-fd13-4bc2-9271-cbde55c28c21': {'x': 400, 'y': 100}}
        self.enemies_coord = []
        self.cultists_coord = []
        self.player = None                          # instance of class Player
        self.players = {}
        self.enemies = {}
        self.cultists = {}

        self.weapons = None
        self.inventory = None

    async def connect(self):
        # Step 1: Join a room
        response = requests.post(f"{SERVER_URL}/join")
        data = response.json()
        print("Join response text:", response.text)
        self.player_id = data["player_id"]
        self.room_id = data["room_id"]

        # Step 2: Connect to WebSocket
        self.ws = await websockets.connect(f"{WS_URL}/{self.room_id}/{self.player_id}")
        print(f"Connected to room {self.room_id} as {self.player_id}")

    async def receive_message(self):
        while self.running:
            try:
                async for message in self.ws:
                    print("Received message:", message)
                    data = json.loads(message)
                    # if data["type"] == "start_game":
                    #     self.players_coord = data["players"]
                    #     self.enemies_coord = data["enemies"]
                    #     self.cultists_coord = data["cultists"]
                    #     self.game_started = True
                    #     self.running = True
                    #     print("Game started!", self.players_coord)
                    #     return
                    if data["type"] == "state_update":
                        self.players_coord = data["players"]
                        self.enemies_coord = data["enemies"]
                        self.cultists_coord = data["cultists"]
                    elif data["type"] == "player_died":
                        if data["player_id"] == self.player_id:
                            self.player.on_death()
                            # show 'you died' screen
                            self.running = False
                            self.game_started = False
                            print("Connection closed")
                    elif data["type"] == "enemy_killed":
                        e_id = data["id"]
                        self.enemies.pop(e_id)
                        self.enemies_coord.pop(e_id)
                    elif data["type"] == "cultist_killed":
                        e_id = data["id"]
                        self.cultists.pop(e_id)
                        self.cultists_coord.pop(e_id)
                    elif data["type"] == "room_closed":
                        print("Problem occured! Room closed!")
                        self.running = False
                        self.game_started = False
                    elif data["type"] == "game_ended":
                        if data["winner"] == self.player_id:
                            print("Game ended! You wined!")
                        else:
                            print(fr"Game ended! Player {data["winner"]} wined!")
                        self.running = False
                        self.game_started = False

                    # check it and update the game
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                self.running = False

    async def send_movements(self, dx, dy):
        try:
            msg = json.dumps({"type": "move", "dx": dx, "dy": dy})
            await self.ws.send(msg)
            await asyncio.sleep(0.2)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed (send)")
            self.running = False
            self.game_started = False

    async def wait_for_start_game(self, game_started_event):
        while True:
            mes = await self.ws.recv()
            print("Received message:", mes)
            data = json.loads(mes)

            if data["type"] == "start_game":
                self.players_coord = data["players"]
                self.enemies_coord = data["enemies"]
                self.cultists_coord = data["cultists"]
                self.game_started = True
                self.running = True
                game_started_event.set()  # SET THE EVENT
                print("Game started!", self.players_coord)
            elif data["type"] == "room_closed":
                return

    async def get_wallet_address(self):
        WS_URL = "ws://localhost:8000"# Step 1: Start WebSocket to wait for wallet
        session_id = str(uuid.uuid4())
        ws_url = f"{WS_URL}/ws/wallet_wait/{session_id}"
        print(f"Connecting to WebSocket: {ws_url}")
        async with websockets.connect(ws_url) as websocket:
            # Step 2: Open MetaMask login page in browser
            print("Opening MetaMask login page...")
            webbrowser.open(f"{SERVER_URL}/wallet_login?session_id={session_id}")

            # Step 3: Wait for wallet from server
            print("Waiting for wallet via WebSocket...")
            message = await websocket.recv()
            data = json.loads(message)
            self.wallet = data.get("wallet")

            print("Wallet received:", self.wallet)

        # if not wallet:
        #     raise Exception("Failed to retrieve wallet address in time.")
        # self.wallet = wallet

    async def initialize_entities(self):
        for pl_id, prop in self.players_coord.items():
            x, y = prop.get("x", 0), prop.get("y", 0)
            if pl_id == self.player_id:
                self.player = Player(x=x, y=y, speed=SPEED, sprite_path=INITIAL_PLAYER_SPRITE_PATH)
            else:
                self.players[pl_id] = Player(x=x, y=y, speed=SPEED, sprite_path=OTHER_PLAYER_1_SPRITE_PATH)  # Treat as NPCs

        for e in self.enemies_coord:
            e_id, x, y = e["id"], e["x"], e["y"]
            self.enemies[e_id] = (Zombie(x=x, y=y))

        for e in self.cultists_coord:
            c_id, x, y = e["id"], e["x"], e["y"]
            self.cultists[c_id] = (Cultist(x=x, y=y))

        self.weapons = Weapons(player_width=self.player.width, player_height=self.player.height)
        self.inventory = Inventory(screen_width=WIDTH, screen_height=HEIGHT)

    async def send_damaged_enemies(self, output):
        enemies_taken_damage, cultists_taken_damage = output
        e, c = [], []
        if enemies_taken_damage:
            e = [{"id": enemy_id, "damage": damage} for enemy_id, damage in enemies_taken_damage]
        if cultists_taken_damage:
            c = [{"id": enemy_id, "damage": damage} for enemy_id, damage in cultists_taken_damage]
        try:
            msg = json.dumps({
                "type": "damaged_enemies",
                "enemies": e,
                "cultists": c
            })
            await self.ws.send(msg)
        # await asyncio.sleep(0.2)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed (send)")
            self.running = False
            self.game_started = False

    async def draw_entities(self, window, dt):

        self.weapons.update_position(self.player.x, self.player.y)
        output = self.weapons.weapons[1].update_slash(dt, self.player.x, self.player.y, self.player.facing_left, self.enemies, self.cultists)
        if output:
            await self.send_damaged_enemies(output)

        for pl_id, prop in self.players_coord.items():
            x, y, health = prop.get("x", 0), prop.get("y", 0), prop.get("health", 0)
            if pl_id == self.player_id:
                self.player.x = x
                self.player.y = y
                self.player.current_health = health
                self.player.draw(window, camera_x, camera_y)
            else:
                self.players[pl_id].x = x
                self.players[pl_id].y = y
                self.players[pl_id].current_health = health
                self.players[pl_id].draw(window, camera_x, camera_y)

        for prop in self.enemies_coord:
            i, x, y, health = prop["id"], prop["x"], prop["y"], prop["health"]
            self.enemies[i].x = x
            self.enemies[i].y = y
            self.enemies[i].current_health = health
            self.enemies[i].draw(window, camera_x, camera_y)


        for prop in self.cultists_coord:
            i, x, y, health = prop["id"], prop["x"], prop["y"], prop["health"]
            self.cultists[i].x = x
            self.cultists[i].y = y
            self.cultists[i].current_health = health
            self.cultists[i].draw(window, camera_x, camera_y)


    async def draw_lighting_effect(self, window):
        lighting_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        lighting_surface.fill((0, 0, 0, 220))
        light_radius = 200
        for i in range(light_radius, 0, -1):
            alpha = int(100 * (i / light_radius))
            pygame.draw.circle(
                lighting_surface,
                (255, 255, 0, alpha),
                (self.player.x - camera_x + self.player.width // 2, self.player.y - camera_y + self.player.height // 2),
                i
            )
        window.blit(lighting_surface, (0, 0))

    async def pygame_loop(self, window):
        global camera_x, camera_y
        print("1")
        ground_image = pygame.image.load(
            "Game_models/Ground/ground.png").convert_alpha()
        ground_width, ground_height = ground_image.get_width(), ground_image.get_height()
        await self.initialize_entities()
        # Use pygame.time.get_ticks() for timing, but no blocking tick()
        target_fps = 60
        frame_duration = 1 / target_fps
        print("1")
        while self.running:
            frame_start = asyncio.get_event_loop().time()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.game_started = False
                    if self.ws and not self.ws.closed:
                        await self.ws.close()
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.weapons.switch_weapon(0)
                        self.inventory.select_slot(0)
                    elif event.key == pygame.K_2:
                        self.weapons.switch_weapon(1)
                        self.inventory.select_slot(1)
                    elif event.key == pygame.K_3:
                        self.weapons.switch_weapon(2)
                        self.inventory.select_slot(2)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.weapons.active_weapon_index == 1:
                        self.weapons.weapons[1].start_slash()

            keys = pygame.key.get_pressed()

            # Calculate delta time since last frame
            current_ticks = pygame.time.get_ticks()
            dt = frame_duration  # Approximate fixed timestep for smooth movement
            current_time = current_ticks / 1000  # seconds since pygame start

            self.player.move(keys, dt)
            dx, dy = 0, 0
            if keys[pygame.K_a]:  # Move left
                dx = -SPEED

            elif keys[pygame.K_d]:  # Move right
                dx = SPEED

            if keys[pygame.K_w]:  # Move up
                dy = -SPEED
            if keys[pygame.K_s]:  # Move down
                dy = SPEED
            #sending move coords to server
            await self.send_movements(dx, dy)

            camera_x = self.player.x - WIDTH // 2
            camera_y = self.player.y - HEIGHT // 2

            if self.player.current_health <= 0:
                print("Game Over! The player has died.")
                self.running = False
                self.game_started = False
                await self.ws.close()
                pygame.quit()
                return

            # Draw ground tiles
            for x in range(-ground_width, WIDTH + ground_width, ground_width):
                for y in range(-ground_height, HEIGHT + ground_height, ground_height):
                    window.blit(ground_image, (x - camera_x % ground_width, y - camera_y % ground_height))

            await self.draw_entities(window, dt)
            self.weapons.draw(window, camera_x, camera_y, self.player.facing_left, self.player.x, self.player.y)

            await self.draw_lighting_effect(window)
            self.inventory.draw(window)

            pygame.display.flip()

            # Async sleep to maintain frame rate without blocking the event loop
            elapsed = asyncio.get_event_loop().time() - frame_start
            sleep_time = max(0, frame_duration - elapsed)
            await asyncio.sleep(sleep_time)

        pygame.quit()

    async def message_dispatcher(self, game_started_event):
        while True:
            try:
                message = await self.ws.recv()
                print(message)
                data = json.loads(message)

                if data["type"] == "start_game":
                    self.players_coord = data["players"]
                    self.enemies_coord = data["enemies"]
                    self.cultists_coord = data["cultists"]
                    self.game_started = True
                    self.running = True
                    game_started_event.set()
                    print("Game started!")

                elif data["type"] == "room_closed":
                    print("Room closed before game start.")
                    pygame.quit()
                    sys.exit()

                elif data["type"] == "state_update":
                    self.players_coord = data["players"]
                    self.enemies_coord = data["enemies"]
                    self.cultists_coord = data["cultists"]

                else:
                    print("Unknown message:", data)

            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed.")
                break

    async def run(self):
        # first display and connect the Metamask wallet
        await self.get_wallet_address()
        await self.connect()
        # wait to start game
        pygame.init()

        # Window settings
        win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Game Loading")

        # Create an asyncio.Event to coordinate
        game_started_event = asyncio.Event()

        # Run waiting screen and while loop concurrently
        game_start_task = asyncio.create_task(self.message_dispatcher(game_started_event))
        #game_start_task = asyncio.create_task(self.receive_message())
        waiting_screen_task = asyncio.create_task(show_waiting_screen(win, WIDTH, HEIGHT, game_started_event))

        await game_started_event.wait()  # Wait until the event is set

        # Cancel waiting screen task now that game started
        waiting_screen_task.cancel()
        try:
            await waiting_screen_task
        except asyncio.CancelledError:
            pass

        # done, pending = await asyncio.wait(
        #     [game_start_task, waiting_screen_task],
        #     return_when=asyncio.FIRST_COMPLETED  # Wait until the first task is done
        # )
        #
        # # Cancel the waiting screen task once the game starts
        # for task in pending:
        #     task.cancel()

        # Draw players on the screen
        # Start game and enable players movements (self.running)
        # start game, take broadcasted coords and draw players, asynchronically to: take, implement and send my players coords,
        # receive and implement the other players coords,
        # locally checks: if killed, if lives over --> self.running = False, player gets out => send to server json "player x killed"
        # locally checks: if a global change made (eg killed a zombie) => send to server

        pygame.display.set_caption("Dungeon Game")
        pygame_thread = asyncio.create_task(self.pygame_loop(win))
        # pygame_thread = threading.Thread(target=pygame_loop)
        # pygame_thread.start()

        #receive = asyncio.create_task(self.receive_message())
        # send = asyncio.create_task(self.send_movements(self.ws))
        # # game_logic = asyncio.create_task(async_game_logic())

        done, pending = await asyncio.wait(
            [pygame_thread, game_start_task],
            return_when=asyncio.FIRST_COMPLETED  # Wait until the first task is done
        )

        # Cancel the waiting screen task once the game starts
        for task in pending:
            task.cancel()

        # At the end: reward winner using ERC-20
        # pygame.quit()
        # sys.exit()


if __name__ == "__main__":
    client = GameClient()
    asyncio.run(client.run())
