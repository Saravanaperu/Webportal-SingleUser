import httpx
from app.core.logging import logger
from SmartApi import SmartConnect

class AngelRestClient:
    """
    REST client for interacting with the AngelOne API using the smartapi-python library.
    """
    def __init__(self, smart_api: SmartConnect):
        self.smart_api = smart_api

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
