import asyncio
from app.core.logging import logger
from SmartApi.smartWebSocketOrderUpdate import SmartWebSocketOrderUpdate

class AngelOrderWsClient:
    """
    Asynchronous WebSocket client for AngelOne's order update feed.
    """
    def __init__(self, auth_token: str, api_key: str, client_id: str, feed_token: str):
        self.auth_token = auth_token
        self.api_key = api_key
        self.client_id = client_id
        self.feed_token = feed_token
        self.sws = None
        self.data_queue = asyncio.Queue()
        self._is_connected = False

    def _on_data(self, wsapp, message):
        logger.debug(f"Received order update: {message}")
        asyncio.get_running_loop().call_soon_threadsafe(self.data_queue.put_nowait, message)

    def _on_open(self, wsapp):
        logger.info("AngelOne Order WebSocket connection opened.")
        self._is_connected = True
        # Unlike the market data feed, order updates don't require a subscription call.
        # The connection itself is enough to start receiving updates for the client.

    def _on_error(self, wsapp, error):
        logger.error(f"AngelOne Order WebSocket error: {error}")
        self._is_connected = False

    def _on_close(self, wsapp):
        logger.warning("AngelOne Order WebSocket connection closed.")
        self._is_connected = False

    async def connect(self):
        if self._is_connected:
            logger.warning("Order WebSocket is already connected.")
            return

        logger.info("Attempting to connect to AngelOne Order WebSocket...")
        try:
            self.sws = SmartWebSocketOrderUpdate(self.auth_token, self.api_key, self.client_id, self.feed_token)

            self.sws.on_data = self._on_data
            self.sws.on_open = self._on_open
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close

            await asyncio.to_thread(self.sws.connect)

            await asyncio.sleep(2)
            if not self._is_connected:
                raise ConnectionError("Failed to establish Order WebSocket connection.")

        except Exception as e:
            logger.error(f"Order WebSocket connection failed: {e}", exc_info=True)
            self.sws = None

    async def receive_data(self):
        if not self.sws:
            logger.error("Order WebSocket client is not initialized.")
            return

        while self._is_connected:
            try:
                data = await self.data_queue.get()
                yield data
            except asyncio.CancelledError:
                logger.info("Order data receiving task was cancelled.")
                break
        logger.warning("Exiting order data receiving loop.")

    async def close(self):
        if self.sws and self._is_connected:
            logger.info("Closing Order WebSocket connection.")
            self.sws.close_connection()
            self._is_connected = False
