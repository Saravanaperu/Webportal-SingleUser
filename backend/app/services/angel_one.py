import os
import asyncio
from dotenv import load_dotenv
from app.core.logging import logger
from app.angel_one_connector.auth import AngelAuth
from app.angel_one_connector.rest_client import AngelRestClient
from app.angel_one_connector.ws_client import AngelWsClient
from app.angel_one_connector.angel_order_ws_client import AngelOrderWsClient

load_dotenv()

class AngelOneConnector:
    """
    Main connector for AngelOne. It orchestrates the authentication,
    REST, and WebSocket clients.
    """
    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY")
        self.client_id = os.getenv("ANGEL_CLIENT_ID")
        self.password = os.getenv("ANGEL_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET")

        if not all([self.api_key, self.client_id, self.password, self.totp_secret]):
            raise ValueError("Missing required AngelOne credentials in .env file.")

        self.auth_client = AngelAuth(self.api_key, self.client_id, self.password, self.totp_secret)
        self.rest_client = None
        self.ws_client = None
        self.order_ws_client = None
        self.refresh_token = None

    async def connect(self) -> bool:
        """
        Connects to AngelOne by logging in and initializing clients.
        """
        logger.info("Connecting to AngelOne...")

        login_response = await asyncio.to_thread(self.auth_client.login)

        if not login_response:
            logger.error("AngelOne login failed.")
            return False

        jwt_token = login_response.get("jwt_token")
        feed_token = login_response.get("feed_token")
        self.refresh_token = login_response.get("refresh_token")

        smart_api_instance = self.auth_client.get_smart_api_instance()
        self.rest_client = AngelRestClient(smart_api_instance)

        # The WebSocket client needs the auth token and other details
        self.ws_client = AngelWsClient(
            auth_token=jwt_token,
            api_key=self.api_key,
            client_id=self.client_id,
            feed_token=feed_token
        )

        self.order_ws_client = AngelOrderWsClient(
            auth_token=jwt_token,
            api_key=self.api_key,
            client_id=self.client_id,
            feed_token=feed_token
        )

        # The WebSocket connection should be managed by the service that needs it (e.g., TradingStrategy)
        # For now, we confirm the connector is ready.
        logger.info("AngelOne connector is ready.")
        return True

    def get_rest_client(self) -> AngelRestClient | None:
        """Returns the REST client instance."""
        return self.rest_client

    def get_order_ws_client(self) -> AngelOrderWsClient | None:
        """Returns the Order WebSocket client instance."""
        return self.order_ws_client

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

    def get_ws_client(self) -> AngelWsClient | None:
        """Returns the WebSocket client instance."""
        return self.ws_client
