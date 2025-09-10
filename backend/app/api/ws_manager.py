import asyncio
import json
from typing import List
from fastapi import WebSocket
from ..core.logging import logger, ws_broadcast_logger

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Log the message to the dedicated broadcast log
        ws_broadcast_logger.info(json.dumps(message))

        if not self.active_connections:
            return
        
        async with self._lock:
            disconnected = []
            for connection in self.active_connections[:]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to client: {e}")
                    disconnected.append(connection)
            
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

manager = WebSocketManager()