import asyncio
import json
from typing import List, Dict
from fastapi import WebSocket

class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts messages.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """
        Accepts a new WebSocket connection and adds it to the list of active connections.
        """
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the list of active connections.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        """
        Broadcasts a JSON message to all active WebSocket connections.
        """
        async with self.lock:
            # We must iterate over a copy, as a client might disconnect during the broadcast,
            # which would modify the list we are iterating over.
            for connection in self.active_connections[:]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # If sending fails, the client has likely disconnected.
                    # We remove it from the list to avoid future errors.
                    self.disconnect(connection)

# A global instance of the manager to be used across the application
manager = WebSocketManager()
