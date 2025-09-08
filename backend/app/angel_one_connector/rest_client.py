import httpx
from app.core.logging import logger
from SmartApi import SmartConnect

class AngelRestClient:
    """
    REST client for interacting with the AngelOne API using the smartapi-python library.
    """
    INSTRUMENT_LIST_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
    _instrument_cache = None

    def __init__(self, smart_api: SmartConnect):
        self.smart_api = smart_api

    async def get_instrument_list(self) -> list | None:
        """
        Fetches the full list of tradable instruments from the AngelOne URL.
        Caches the result in memory to avoid repeated downloads.
        """
        if AngelRestClient._instrument_cache:
            logger.info("Returning cached instrument list.")
            return AngelRestClient._instrument_cache

        logger.info("Fetching instrument list from AngelOne...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.INSTRUMENT_LIST_URL)
                response.raise_for_status()
                instruments = response.json()
                if instruments:
                    AngelRestClient._instrument_cache = instruments
                    logger.info(f"Successfully fetched and cached {len(instruments)} instruments.")
                    return instruments
                else:
                    logger.error("Instrument list fetched is empty.")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching instrument list: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error fetching instrument list: {e}", exc_info=True)
            return None

    def get_candle_data(self, historic_params: dict) -> list | None:
        """Fetches historical candle data."""
        logger.info(f"Fetching candle data with params: {historic_params}")
        try:
            candle_data = self.smart_api.getCandleData(historic_params)
            if candle_data.get("status") and candle_data.get("data"):
                return candle_data["data"]
            else:
                logger.error(f"Failed to fetch candle data: {candle_data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching candle data: {e}", exc_info=True)
            return None

    def get_profile(self, refresh_token: str) -> dict | None:
        """Fetches user profile, including funds."""
        logger.info("Fetching profile from AngelOne...")
        try:
            profile_data = self.smart_api.getProfile(refresh_token)
            if profile_data.get("status") and profile_data.get("data"):
                data = profile_data["data"]
                return {
                    "balance": float(data.get("net")),
                    "margin": float(data.get("availablecash")),
                    "name": data.get("name")
                }
            else:
                logger.error(f"Failed to fetch profile: {profile_data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching profile: {e}", exc_info=True)
            return None

    def get_positions(self) -> list | None:
        """Fetches open positions."""
        logger.info("Fetching positions from AngelOne...")
        try:
            positions_data = self.smart_api.position()
            if positions_data.get("status"):
                return positions_data.get("data", [])
            else:
                logger.error(f"Failed to fetch positions: {positions_data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching positions: {e}", exc_info=True)
            return None

    def get_orders(self) -> list | None:
        """Fetches today's orders."""
        logger.info("Fetching orders from AngelOne...")
        try:
            order_data = self.smart_api.orderBook()
            if order_data.get("status"):
                return order_data.get("data", [])
            else:
                logger.error(f"Failed to fetch orders: {order_data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching orders: {e}", exc_info=True)
            return None

    def place_order(self, params: dict) -> dict | None:
        """Places an order."""
        logger.info(f"Placing order: {params}")
        try:
            order_response = self.smart_api.placeOrder(params)
            if order_response:
                if isinstance(order_response, dict) and order_response.get("status"):
                    return order_response
                elif isinstance(order_response, str):
                     return {"status": "success", "orderid": order_response}
                else:
                    logger.error(f"Order placement failed with response: {order_response}")
                    return None
            else:
                logger.error("Order placement returned a null response.")
                return None
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None
