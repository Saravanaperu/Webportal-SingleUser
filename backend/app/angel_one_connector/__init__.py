import asyncio
from .auth import AngelAuth
from .rest_client import AngelRestClient
from .ws_client import AngelWsClient
from ..core.config import settings
from ..core.logging import logger

class AngelOneConnector:
    """
    Main connector class that integrates authentication, REST, and WebSocket clients.
    """
    def __init__(self):
        logger.info("Initializing AngelOne Connector...")
        self.auth = AngelAuth(
            api_key=settings.api_key,
            client_id=settings.client_id,
            password=settings.password,
            totp_secret=settings.totp_secret
        )
        self.rest_client = None
        self.ws_client = None

    async def connect(self):
        """
        Establishes connection to AngelOne, including authentication and WebSocket setup.
        """
        logger.info("Connecting to AngelOne...")
        try:
            session_info = await self.auth.login()
            if not session_info:
                logger.critical("AngelOne login failed.")
                return False

            jwt_token = session_info.get("jwt_token")
            feed_token = session_info.get("feed_token")

            self.rest_client = AngelRestClient(jwt_token)
            # This needs auth_token which is the jwt_token
            self.ws_client = AngelWsClient(auth_token=jwt_token, api_key=settings.api_key, client_id=settings.client_id, feed_token=feed_token)

            # Start the WebSocket connection in the background
            asyncio.create_task(self.ws_client.connect())

            logger.info("Successfully connected to AngelOne.")
            return True
        except Exception as e:
            logger.error(f"Error during AngelOne connection: {e}", exc_info=True)
            return False

    # Delegate methods to the rest_client
    async def get_account_details(self):
        if self.rest_client:
            return await self.rest_client.get_profile()
        logger.warning("REST client not initialized. Call connect() first.")
        return None

    async def get_positions(self):
        if self.rest_client:
            return await self.rest_client.get_positions()
        logger.warning("REST client not initialized. Call connect() first.")
        return None

    async def get_orders(self):
        if self.rest_client:
            return await self.rest_client.get_orders()
        logger.warning("REST client not initialized. Call connect() first.")
        return None

    async def place_order(self, order_params):
        if self.rest_client:
            return await self.rest_client.place_order(order_params)
        logger.warning("REST client not initialized. Call connect() first.")
        return None
