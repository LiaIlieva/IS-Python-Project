from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import math
import random

from Entities import Entity, Zombie, Cultist

rooms : Dict[str, "GameRoom"] = {}
INITIAL_PLAYER_COORD = {'x' : 0, 'y' : 0}
PLAYERS_IN_ROOM = 2
TICK_RATE = 1 / 30  # 30 updates per second
DIFICULTY_MULTIPLIER = 1.5
INITIAL_HEALTH = 100
global_dt = 0

WIDTH = 800
HEIGHT = 600
SPAWN_MARGIN = 50
MIN_DISTANCE_FROM_PLAYER = 100

SPAWN_MARGIN_PLAYER = 100
MIN_DISTANCE_BETWEEN_PLAYERS = 75

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players : Dict[str, WebSocket] = {}
        self.state : Dict[str, Dict[str, int]]= {} # for the coord of all players
        self.running = False
        self.lock = asyncio.Lock() # This prevents data races when multiple coroutines (players) try to read/write shared data at the same time
        self.loop_task = None
        self.started_at = None
        self.position_index = 0
        self.enemies : Dict[int, Zombie] = {}
        self.cultists : Dict[int, Cultist] = {}
        self.dead_players = []


    def is_ready(self):
        return len(self.players) == PLAYERS_IN_ROOM

    def get_random_spawn_location(self):
        max_attempts = 20
        for _ in range(max_attempts):
            x = random.randint(SPAWN_MARGIN, WIDTH - SPAWN_MARGIN)
            y = random.randint(SPAWN_MARGIN, HEIGHT - SPAWN_MARGIN)

            too_close = False
            for player in self.state.values():
                dx = player["x"] - x
                dy = player["y"] - y
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < MIN_DISTANCE_FROM_PLAYER:
                    too_close = True
                    break

            if not too_close:
                return x, y

        # fallback
        return WIDTH // 2, HEIGHT // 2

    async def initialize_enemies(self, difficulty_multiplier=DIFICULTY_MULTIPLIER):
        num_enemies = int(PLAYERS_IN_ROOM * difficulty_multiplier)

        for i in range(num_enemies):
            x, y = self.get_random_spawn_location()
            if i % 2 == 0:
                self.enemies[i] = (Zombie(x, y, load_sprites=False))
            else:
                self.cultists[i] = (Cultist(x, y, load_sprites=False))

    def all_enemies_killed(self):
        if self.enemies is None and self.cultists is None:
            return True
        return False

    async def remove_enemy(self, enemy_id : int, killer : str):
        if enemy_id in self.enemies:
            self.enemies.pop(enemy_id, None)
            await self.broadcast_enemy_killed(enemy_id)
            if self.all_enemies_killed():
                await self.broadcast_winner(killer)
                await self.shutdown()

    async def remove_cultist(self, cultist_id : int, killer : str):
        if cultist_id in self.enemies:
            self.cultists.pop(cultist_id, None)
            await self.broadcast_cultist_killed(cultist_id)
            if self.all_enemies_killed():
                await self.broadcast_winner(killer)
                await self.shutdown()

    async def start_game(self):
        print("starting game")
        self.running = True
        self.started_at = asyncio.get_running_loop().time()
        # initiate the Enemies
        await self.initialize_enemies()
        # send the starting Message
        start_msg = {"type": "start_game", "players": self.state,
                     "enemies": [{"id": k, "x": e.x, "y": e.y, "health": e.current_health} for k, e in self.enemies.items()],
                      "cultists": [{"id": k, "x": e.x, "y": e.y, "health": e.current_health} for k, e in self.cultists.items()]}
        for ws in self.players.values():
            try:
                await ws.send_json(start_msg)
            except:
                pass
        self.loop_task = asyncio.create_task(self.game_loop())

    def get_random_player_spawn(self):
        max_attempts = 25
        for _ in range(max_attempts):
            x = random.randint(SPAWN_MARGIN_PLAYER, WIDTH - SPAWN_MARGIN_PLAYER)
            y = random.randint(SPAWN_MARGIN_PLAYER, HEIGHT - SPAWN_MARGIN_PLAYER)

            too_close = False
            for player in self.state.values():
                dx, dy = x - player['x'], y - player['y']
                if (dx ** 2 + dy ** 2) ** 0.5 < MIN_DISTANCE_BETWEEN_PLAYERS:
                    too_close = True
                    break

            if not too_close:
                return x, y

        # fallback: center of map
        return WIDTH // 2, HEIGHT // 2

    async def add_player(self, player_id: str, player_ws: WebSocket):
        async with self.lock:
            self.players[player_id] = player_ws
            print("len layers", len(self.players))

            x, y = self.get_random_player_spawn()
            self.state[player_id] = {"x": x, "y": y, "health": INITIAL_HEALTH}

        if self.is_ready():
            await self.start_game()

    # will be invoked in the Pygame when a player is killed
    async def remove_player(self, player_id: str):
        if player_id in self.players:
            ws = self.players[player_id]
            if ws:
                await ws.close()
            self.players.pop(player_id, None)
            self.state.pop(player_id, None)


    async def get_closest_player(self, enemy):
        pl_cords = None
        min_distance = float('inf')

        for player, pos in self.state.items():
            x, y = pos["x"], pos["y"]
            dist = math.hypot(enemy.x - x, enemy.y - y)
            if dist < min_distance:
                pl_cords = player, [x, y]
                min_distance = dist

        return pl_cords

    async def broadcast_cultist_killed(self, cultist_id):
        state_msg = {"type": "cultist_killed",
                     "id": cultist_id}

        for ws in self.players.values():
            try:
                await ws.send_json(state_msg)
            except:
                pass

    async def broadcast_enemy_killed(self, e_id):
        state_msg = {"type": "enemy_killed",
                     "id": e_id }

        for ws in self.players.values():
            try:
                await ws.send_json(state_msg)
            except:
                pass

    async def broadcast_winner(self, winner : str):
        state_msg = {"type": "game_ended",
                     "winner": winner}

        for ws in self.players.values():
            try:
                await ws.send_json(state_msg)
            except:
                pass

    async def broadcast_state(self):

        state_msg = {"type": "state_update", "players": self.state,
                     "enemies": [{"id": k, "x": e.x, "y": e.y, "health": e.current_health} for k, e in self.enemies.items()],
                      "cultists": [{"id": k, "x": e.x, "y": e.y, "health": e.current_health} for k, e in self.cultists.items()]}

        for ws in self.players.values():
            try:
                await ws.send_json(state_msg)
            except:
                pass

    async def game_loop(self):
        try:
            previous_time = asyncio.get_running_loop().time()

            while self.running:
                await asyncio.sleep(TICK_RATE)

                current_time = asyncio.get_running_loop().time()
                dt = current_time - previous_time
                previous_time = current_time

                # Update enemies
                for enemy in self.enemies.values():
                    player, cords = await self.get_closest_player(enemy)
                    print("2")
                    if cords:
                        enemy.follow_player(cords[0], cords[1], dt)
                        has_attacked = enemy.attack_player(cords, current_time)
                        if has_attacked: self.state[player]["health"] -= enemy.attack_damage
                        if self.state[player]["health"] <= 0:
                            # player killed
                            self.state[player]["health"] = 0
                            self.dead_players.append(player)


                for cultist in self.cultists.values():
                    player, cords = await self.get_closest_player(cultist)
                    if cords:
                        cultist.follow_player(cords[0], cords[1], dt)

                        has_attacked = cultist.attack_player(cords, current_time)
                        if has_attacked: self.state[player]["health"] -= cultist.attack_damage
                        if self.state[player]["health"] <= 0:
                            # player killed
                            self.state[player]["health"] = 0
                            self.dead_players.append(player)

                for dead_id in self.dead_players:
                    death_msg = {"type": "player_died", "player_id": dead_id}
                    async with self.lock:
                        if self.players:
                            for ws in self.players.values():
                                try:
                                    await ws.send_json(death_msg)
                                except:
                                    pass
                        else:
                            self.running = False
                            rooms.pop(self.room_id, None)
                    await self.remove_player(dead_id)
                self.dead_players.clear()

                # Send updates to players
                async with self.lock:
                    if self.players:
                        await self.broadcast_state()
                    else:
                        self.running = False
                        rooms.pop(self.room_id, None)
        except Exception as e:
            print("Game loop error:", e)
            self.running = False

    async def shutdown(self):
        self.running = False
        if self.loop_task:
            self.loop_task.cancel()

        # Notify all players that the game has ended
        shutdown_msg = {"type": "room_closed"}
        for ws in self.players.values():
            try:
                await ws.send_json(shutdown_msg)
                await ws.close()
            except:
                pass  # Ignore if already closed or errored

        self.players.clear()
        self.state.clear()

