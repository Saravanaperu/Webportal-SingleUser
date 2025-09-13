import asyncio
import importlib
from ..core.config import settings
from ..core.logging import logger
from ..angel_one_connector.auth import AngelAuth
from ..angel_one_connector.rest_client import AngelRestClient
from ..angel_one_connector.ws_client import AngelWsClient

class AngelOneConnector:
    """
    Main connector for AngelOne. It orchestrates the authentication,
    REST, and WebSocket clients.
    """
    def __init__(self):
        self.api_key = settings.api_key
        self.client_id = settings.client_id
        self.password = settings.password
        self.totp_secret = settings.totp_secret

        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            raise ValueError("Missing required AngelOne credentials in settings/.env file.")

        self.auth_client = AngelAuth(self.api_key, self.client_id, self.password, self.totp_secret)
        self.rest_client = None
        self.ws_client = None
        self.refresh_token = None
        self.jwt_token = None
        self.feed_token = None

    async def _perform_login_and_init_clients(self) -> bool:
        """
        Private helper to perform the login and initialize all API clients.
        This is the core logic used by both connect() and reconnect().
        """
        login_response = await asyncio.to_thread(self.auth_client.login)

        if not login_response:
            logger.error("AngelOne login failed.")
            return False

        self.refresh_token = login_response.get("refresh_token")
        self.jwt_token = login_response.get("jwt_token")
        self.feed_token = login_response.get("feed_token")
        smart_api_instance = self.auth_client.get_smart_api_instance()

        self.rest_client = AngelRestClient(smart_api_instance)

        self.ws_client = AngelWsClient(
            auth_token=self.jwt_token,
            api_key=self.api_key,
            client_id=self.client_id,
            feed_token=self.feed_token
        )
        return True

    async def connect(self) -> bool:
        """
        Connects to AngelOne for the first time on application startup.
        """
        logger.info("Connecting to AngelOne...")
        is_success = await self._perform_login_and_init_clients()
        if is_success:
            logger.info("AngelOne connector is ready.")
        return is_success

    async def reconnect(self) -> bool:
        """
        Performs a reconnection to get new session tokens.
        """
        logger.info("Reconnecting to AngelOne to refresh session...")
        is_success = await self._perform_login_and_init_clients()
        if is_success:
            logger.info("AngelOne session refreshed successfully.")
        else:
            logger.error("Failed to refresh AngelOne session.")
        return is_success

    def get_rest_client(self) -> AngelRestClient | None:
        """Returns the REST client instance."""
        return self.rest_client

    def get_ws_client(self) -> AngelWsClient | None:
        """Returns the WebSocket client instance."""
        return self.ws_client

    async def get_account_details(self) -> dict | None:
        """Fetches account balance and margin."""
        if not self.rest_client:
            return None
        return await asyncio.to_thread(self.rest_client.get_profile, self.refresh_token)

    async def get_positions(self) -> list | None:
        """Fetches open positions."""
        if not self.rest_client:
            return None
        return await asyncio.to_thread(self.rest_client.get_positions)

    async def get_orders(self) -> list | None:
        """Fetches today's orders."""
        if not self.rest_client:
            return None
        return await asyncio.to_thread(self.rest_client.get_orders)

    async def place_order(self, order_params: dict) -> dict | None:
        """Places an order."""
        if not self.rest_client:
            return None
        return await asyncio.to_thread(self.rest_client.place_order, order_params)

    async def get_candle_data(self, candle_params: dict) -> list | None:
        """Fetches historical candle data."""
        if not self.rest_client:
            return None
        return await asyncio.to_thread(self.rest_client.get_candle_data, candle_params)
    
    async def get_quote(self, symbol: str) -> dict | None:
        """Fetches live quote for a symbol."""
        if not self.rest_client:
            return None
        try:
            # Try to get live quote from broker
            return await asyncio.to_thread(self.rest_client.get_quote, symbol)
        except Exception as e:
            logger.warning(f"Failed to get quote for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, from_date: str, to_date: str, interval: str = 'ONE_MINUTE') -> list | None:
        """Fetches historical OHLC data for backtesting."""
        if not self.rest_client:
            return None
        try:
            params = {
                'symbol': symbol,
                'from_date': from_date,
                'to_date': to_date,
                'interval': interval
            }
            return await asyncio.to_thread(self.rest_client.get_historical_data, params)
        except Exception as e:
            logger.warning(f"Failed to get historical data for {symbol}: {e}")
            return None
