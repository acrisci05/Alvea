"""test_ws.py - Testa il WebSocket del backend Alvea."""
import subprocess, sys
try:
    import websockets
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

import asyncio
import json

async def listen():
    uri = "ws://localhost:8000/ws/live"
    print(f"Connessione a {uri} ...")
    async with websockets.connect(uri) as ws:
        print("Connesso! In attesa di dati dal firmware...\n")
        async for message in ws:
            data = json.loads(message)
            print(f"RICEVUTO: bpm={data.get('bpm')} resp={data.get('respiration_rate')} temp={data.get('skin_temperature')}")

asyncio.run(listen())