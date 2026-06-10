# realtime.py - Gestione connessioni realtime verso client (app/dashboard web).
#
# Espone un ConnectionManager per WebSocket (push bidirezionale) e una coda
# broadcast riusabile anche per Server-Sent Events. Pattern derivato dagli
# esempi WebSocket/SSE del corso.
import asyncio
import json
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        """Invia un messaggio JSON a tutti i client WebSocket connessi."""
        dead = []
        text = json.dumps(message, default=str)
        for ws in self.active:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# Coda asincrona per il fan-out verso gli stream SSE
sse_queue: "asyncio.Queue[dict]" = asyncio.Queue()

manager = ConnectionManager()


async def publish_event(message: dict):
    """Inoltra l'evento sia ai WebSocket sia agli stream SSE."""
    await manager.broadcast(message)
    try:
        sse_queue.put_nowait(message)
    except asyncio.QueueFull:
        pass
