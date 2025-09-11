import asyncio
import json
import six
import websocket
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
        """
        Assigns the callback methods to the SmartWebSocket instance and monkey-patches
        the subscribe method to use the correct token.
        """
        self.sws._on_open = self._on_open
        self.sws._on_message = self._on_message
        self.sws._on_error = self._on_error
        self.sws._on_close = self._on_close

        # Monkey-patch the subscribe method to use the JWT token instead of the feed token.
        # The new API expects the JWT for subscription messages, not just for auth.
        def new_subscribe(task, token_string):
            request = {
                "task": task,
                "channel": token_string,
                "token": self.auth_token,  # Use JWT token
                "user": self.sws.client_code,
                "acctid": self.sws.client_code
            }
            self.sws.ws.send(six.b(json.dumps(request)))
            logger.info(f"Sent MODIFIED subscription request for task '{task}' with JWT token.")
            return True

        self.sws.subscribe = new_subscribe

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
        This method takes direct control of instantiating the WebSocketApp to inject
        required headers and fix callback issues in the underlying library.
        """
        self._setup_callbacks()
        logger.info("Attempting to connect to AngelOne WebSocket...")

        try:
            # The new AngelOne WebSocket API requires four headers for authentication.
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "x-api-key": self.api_key,
                "x-client-code": self.client_id,
                "x-feed-token": self.feed_token
            }

            # Define a correctly-behaving on_close handler to bypass the library's buggy one.
            def on_close_handler(ws, close_status_code, close_msg):
                # The library's internal __on_close sets this flag. Replicate it.
                self.sws.HB_THREAD_FLAG = True
                # Now call our own _on_close method with the correct signature.
                self._on_close(ws, close_status_code, close_msg)

            # Instantiate WebSocketApp directly, providing the correct URL, headers, and callbacks.
            # We still use the library's wrappers for open, message, and error to retain
            # its internal logic (like heartbeats and message parsing).
            # We must use the name-mangled versions to access the private methods
            # of the SmartWebSocket instance from outside its class.
            self.sws.ws = websocket.WebSocketApp(
                'wss://smartapisocket.angelone.in/smart-stream',
                header=headers,
                on_open=self.sws._SmartWebSocket__on_open,
                on_message=self.sws._SmartWebSocket__on_message,
                on_error=self.sws._SmartWebSocket__on_error,
                on_close=on_close_handler # Use our fixed handler
            )

            # The run_forever() method is blocking.
            # We run it in a separate thread to avoid blocking the main asyncio event loop.
            await asyncio.to_thread(self.sws.ws.run_forever)

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}", exc_info=True)

    async def disconnect(self):
        """Disconnects the WebSocket client."""
        if self.is_connected:
            logger.info("Disconnecting from WebSocket...")
            self.sws.close()
