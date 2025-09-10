import asyncio
import types
from SmartApi import SmartWebSocket
from ..core.logging import logger

class AngelWsClient:
    """
    Asynchronous WebSocket client for AngelOne's market and order data feeds,
    using the official smartapi-python library.
    """

    def __init__(self, auth_token: str, api_key: str, client_id: str, feed_token: str):
        self.auth_token = auth_token
        self.api_key = api_key
        self.client_id = client_id
        self.feed_token = feed_token
        self.sws = SmartWebSocket(self.feed_token, self.client_id)
        self.market_data_queue = asyncio.Queue()
        self.order_update_queue = asyncio.Queue()
        self.is_connected = False
        self.subscription_task = "mw" # 'mw' for market watch, 'sfi' for order updates
        self.instrument_tokens = ""

    def _setup_callbacks(self):
        """Assigns the callback methods to the SmartWebSocket instance."""
        self.sws._on_open = self._on_open
        self.sws._on_message = self._on_message
        self.sws._on_error = self._on_error
        self.sws._on_close = self._on_close

    def _on_open(self, wsapp):
        logger.info("WebSocket connection opened.")
        self.is_connected = True
        logger.info(f"Subscribing to instruments with task '{self.subscription_task}' and tokens: {self.instrument_tokens}")
        self.sws.subscribe(self.subscription_task, self.instrument_tokens)

    def _on_message(self, wsapp, message):
        logger.debug(f"WebSocket message received: {message}")
        # Based on typical WebSocket designs, order updates are often pushed
        # on a separate channel or have a distinct structure.
        # We will use a simple heuristic: if it has an 'orderid' key, it's an order update.
        # This is an assumption and should be verified with the actual API.
        if isinstance(message, dict) and 'orderid' in message:
            logger.info(f"Received order update: {message}")
            self.order_update_queue.put_nowait(message)
        else:
            # Otherwise, assume it's market data (a tick).
            self.market_data_queue.put_nowait(message)

    def _on_error(self, wsapp, error):
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, wsapp, close_status_code, close_msg):
        logger.info(f"WebSocket connection closed with code: {close_status_code}, message: {close_msg}")
        self.is_connected = False

    def set_instrument_tokens(self, tokens: list[str]):
        """
        Sets the instrument tokens to be used for subscription.
        The format for the token string is 'exchange|token&exchange|token'.
        Example: "nse_cm|2885&nse_cm|1594"
        """
        self.instrument_tokens = "&".join(tokens)
        logger.info(f"Instrument tokens set for WebSocket: {self.instrument_tokens}")

    async def connect(self):
        """
        Connects to the WebSocket in a non-blocking way by running it in a separate thread.
        This method also applies monkey-patches to the SmartWebSocket instance to fix
        bugs in the smartapi-python library.
        """
        self._setup_callbacks()

        # Monkey-patch 1: Update the WebSocket URL to the correct one.
        self.sws.ROOT_URI = 'wss://smartapisocket.angelone.in/smart-stream'
        logger.info(f"Monkey-patched WebSocket URL to: {self.sws.ROOT_URI}")

        # Monkey-patch 2: Fix the on_close callback signature.
        # The smartapi-python library has a bug where its __on_close method does not
        # accept the close_status_code and close_msg arguments from the underlying
        # websocket-client library, causing a TypeError.
        def new_on_close(smart_ws_instance, ws, close_status_code, close_msg):
            # Replicate the original library's logic
            smart_ws_instance.HB_THREAD_FLAG = True
            # Call the user-defined _on_close method with the correct signature
            smart_ws_instance._on_close(ws, close_status_code, close_msg)

        self.sws.__on_close = types.MethodType(new_on_close, self.sws)
        logger.info("Monkey-patched __on_close method of SmartWebSocket instance.")


        logger.info("Attempting to connect to AngelOne WebSocket...")
        try:
            # The connect() method of SmartWebSocket is blocking.
            # We run it in a separate thread to avoid blocking the main asyncio event loop.
            await asyncio.to_thread(self.sws.connect)
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}", exc_info=True)

    async def disconnect(self):
        """Disconnects the WebSocket client."""
        if self.is_connected:
            logger.info("Disconnecting from WebSocket...")
            self.sws.close()
