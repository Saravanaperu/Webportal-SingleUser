import asyncio
import uuid
from app.core.logging import logger
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

class AngelWsClient:
    """
    Asynchronous WebSocket client for AngelOne's market data feed,
    wrapping the synchronous smartapi-python library.
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
        """Callback function to handle incoming WebSocket messages."""
        logger.debug(f"Received WebSocket data: {message}")
        # The callback is running in a different thread managed by the websocket library.
        # To pass the data to the main asyncio event loop, we use `call_soon_threadsafe`.
        asyncio.get_running_loop().call_soon_threadsafe(self.data_queue.put_nowait, message)

    def _on_open(self, wsapp):
        """Callback function for when the WebSocket connection is opened."""
        logger.info("AngelOne WebSocket connection opened.")
        self._is_connected = True

    def _on_error(self, wsapp, error):
        """Callback function to handle WebSocket errors."""
        logger.error(f"AngelOne WebSocket error: {error}")
        self._is_connected = False

    def _on_close(self, wsapp):
        """Callback function for when the WebSocket connection is closed."""
        logger.warning("AngelOne WebSocket connection closed.")
        self._is_connected = False

    async def connect(self):
        """
        Connects to the WebSocket in a separate thread to avoid blocking the event loop.
        """
        if self._is_connected:
            logger.warning("WebSocket is already connected.")
            return

        logger.info("Attempting to connect to AngelOne WebSocket...")
        try:
            self.sws = SmartWebSocketV2(self.auth_token, self.api_key, self.client_id, self.feed_token)

            # Assign callbacks
            self.sws.on_data = self._on_data
            self.sws.on_open = self._on_open
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close

            # The `connect` method is blocking, so we run it in a separate thread.
            await asyncio.to_thread(self.sws.connect)

            # Short sleep to allow the connection to establish before proceeding
            await asyncio.sleep(2)
            if not self._is_connected:
                raise ConnectionError("Failed to establish WebSocket connection.")

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}", exc_info=True)
            self.sws = None

    async def subscribe_to_instruments(self, token_list: list[dict]):
        """
        Subscribes to market data for a list of instruments.
        `token_list` should be a list of dicts, e.g., [{"exchangeType": 1, "tokens": ["2885"]}]
        """
        if not self.sws or not self._is_connected:
            logger.warning("Cannot subscribe, WebSocket is not connected.")
            return

        correlation_id = str(uuid.uuid4())
        action = 1  # 1 for subscribe
        mode = 1    # 1 for LTP

        logger.info(f"Subscribing to instruments with tokens: {token_list}")
        # The `subscribe` method is synchronous.
        self.sws.subscribe(correlation_id, mode, token_list)

    async def receive_data(self):
        """
        An async generator to yield messages from the data queue.
        """
        if not self.sws:
            logger.error("WebSocket client is not initialized.")
            return

        while self._is_connected:
            try:
                data = await self.data_queue.get()
                yield data
            except asyncio.CancelledError:
                logger.info("Data receiving task was cancelled.")
                break
        logger.warning("Exiting data receiving loop.")

    async def close(self):
        """Closes the WebSocket connection."""
        if self.sws and self._is_connected:
            logger.info("Closing WebSocket connection.")
            self.sws.close_connection()
            self._is_connected = False
