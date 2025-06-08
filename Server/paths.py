import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
import os
# pip install "uvicorn[standard]" the public server
# uvicorn paths:app --reload
from pydantic import BaseModel      # for validating and parsing data
from fastapi import WebSocket, WebSocketDisconnect
from GameRooms import GameRoom, rooms, PLAYERS_IN_ROOM
import uuid
# uuid.uuid4() generates a universally unique identifier (UUID)
import asyncio

from contextlib import asynccontextmanager
# app = FastAPI()

TIME_TO_REMOVE_ROOM = 3000
SERVER_URL = "http://localhost:8000"
TEMP_WALLET_FILE = 'wallet.txt'

# system-level concerns
async def cleanup_rooms():
    while True:
        await asyncio.sleep(60) # 60s
        time_now = time.time()
        for id in rooms:
            if ((rooms[id].started_at and (time_now - rooms[id].started_at > TIME_TO_REMOVE_ROOM)) or
                    (rooms[id].started_at is None and (not rooms[id].players))):
                async with rooms[id].lock:
                    await rooms[id].shutdown()
                rooms.pop(id, None)


# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(cleanup_rooms())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    task = asyncio.create_task(cleanup_rooms())

    yield  # Everything before this runs at startup; everything after is on shutdown

    # Shutdown code (optional)
    task.cancel()  # Stop the task when app shuts down
app = FastAPI(lifespan=lifespan)

# returns the room_id
@app.post("/join")
async def join_player():
    player_id = str(uuid.uuid4())
    for rid in rooms:
        if len(rooms[rid].players) < PLAYERS_IN_ROOM and rooms[rid].running == False:
            print("len rooms ", len(rooms))
            return {"room_id": rid, "player_id": player_id}

    new_rid = str(uuid.uuid4())
    rooms[new_rid] = GameRoom(new_rid)
    print("len rooms ", len(rooms))
    return {"room_id": new_rid, "player_id": player_id}


@app.websocket("/ws/game/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    room = rooms.get(room_id)
    print(room)
    if not room or (player_id in room.players):
        await websocket.close(code=1003) # “Unsupported Data” / “Invalid Room”
        return

    await websocket.accept()
    print(f"Player {player_id} joined room {room_id}, room object: {room}")

    await room.add_player(player_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            print("Recieved data: ", data, "\n")
            if data["type"] == "move":
                dx = data.get("dx", 0)
                dy = data.get("dy", 0)
                async with room.lock:
                    player = room.state.get(player_id)
                    if player:
                        player["x"] += dx
                        player["y"] += dy
            elif data["type"] == "damaged_enemies":
                async with room.lock:
                    if data["enemies"]:
                        for enemy in data["enemies"]:
                            e_id, damage = enemy["id"], enemy["damage"]
                            room.enemies[e_id].current_health -= damage
                            if room.enemies[e_id].current_health <= 0:
                                # remove enemy -> killed
                                await room.remove_enemy(e_id, player_id)

                    if data["cultists"]:
                        for cultists in data["cultists"]:
                            e_id, damage = cultists["id"], cultists["damage"]
                            room.cultists[e_id].current_health -= damage
                            if room.cultists[e_id].current_health <= 0:
                                # remove cultists -> killed
                                await room.remove_cultist(e_id, player_id)

    except WebSocketDisconnect:
        await room.remove_player(player_id)


active_wallet_waiters = {}

@app.get("/wallet_login", response_class=HTMLResponse)
async def wallet_login(session_id: str):
    return HTMLResponse(f"""
        <html>
        <body>
            <script>
                async function connect() {{
                    if (typeof window.ethereum !== "undefined") {{
                        const accounts = await ethereum.request({{ method: 'eth_requestAccounts' }});
                        const address = accounts[0];
                        window.location.href = "{SERVER_URL}/wallet_response?wallet=" + address + "&session_id={session_id}";
                    }} else {{
                        document.body.innerText = "MetaMask is not installed.";
                    }}
                }}
                connect();
            </script>
        </body>
        </html>
    """)

@app.get("/wallet_response")
async def wallet_response(wallet: str, session_id: str):
    ws = active_wallet_waiters.pop(session_id, None)
    if ws:
        try:
            await ws.send_json({"wallet": wallet})
            await ws.close()
        except Exception as e:
            print(f"Failed to send wallet to session {session_id}: {e}")
    else:
        print(f"No active websocket for session {session_id}")
    return PlainTextResponse(f"Wallet {wallet} received.")

@app.websocket("/ws/wallet_wait/{session_id}")
async def wallet_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_wallet_waiters[session_id] = websocket
    try:
        # Just park the socket, no need to wait for client data
        await asyncio.Event().wait()  # Keeps the socket open indefinitely
    except WebSocketDisconnect:
        active_wallet_waiters.pop(session_id, None)


# -> get a json with all game NFTs
@app.get("/get_game_nft")
async def get_game_nft():
    pass
# buy game NFT - get weapon_type_id, wallet address
@app.post("/buy_game_nft")
async def buy_game_nft(weapon_type_id, wallet_address):
    pass
# -> get a json with all listed NFTs
@app.get("/get_listed_nft")
async def get_listed_nft():
    pass
# buy another player's NFT - get weapon_id, wallet address
@app.post("/buy_listed_nft")
async def buy_listed_nft(weapon_id, wallet_address):
    pass
# -> get a json with player's NFTs
@app.get("/get_player_nft")
async def get_player_nft(wallet_address):
    pass
# sale back - get weapon_id, wallet address
@app.post("/sale_back")
async def sale_back(weapon_id, wallet_address):
    pass
# list for sale - get weapon_id, wallet address
@app.post("/list_for_sale")
async def list_for_sale(weapon_id, wallet_address):
    pass
