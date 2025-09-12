import httpx
from ..core.logging import logger
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

    def get_profile(self, refresh_token: str) -> dict | None:
        """Fetches user profile, including funds."""
        logger.info("Fetching profile from AngelOne...")
        try:
            # Get RMS (Risk Management System) data for funds
            rms_data = self.smart_api.rmsLimit()
            if rms_data and rms_data.get("status") and rms_data.get("data"):
                data = rms_data["data"]
                # Angel One RMS API returns funds data
                balance = data.get("net", 0)
                margin_used = data.get("utiliseddebits", 0)
                available_cash = data.get("availablecash", 0)
                
                logger.info(f"RMS Data - Net: {balance}, Used: {margin_used}, Available: {available_cash}")
                
                return {
                    "balance": float(balance) if balance is not None else 0.0,
                    "margin": float(margin_used) if margin_used is not None else 0.0,
                    "available": float(available_cash) if available_cash is not None else 0.0
                }
            else:
                logger.error(f"Failed to fetch RMS data: {rms_data.get('message') if rms_data else 'No response'}")
                return None
        except Exception as e:
            logger.error(f"Error fetching RMS data: {e}", exc_info=True)
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

    def get_candle_data(self, params: dict) -> list | None:
        """Fetches historical candle data."""
        logger.info(f"Fetching candle data with params: {params}")
        try:
            candle_data = self.smart_api.getCandleData(params)
            if isinstance(candle_data, dict) and candle_data.get("status") == False:
                 logger.error(f"Failed to fetch candle data: {candle_data.get('message')}")
                 return None
            return candle_data
        except Exception as e:
            logger.error(f"Error fetching candle data: {e}", exc_info=True)
            return None
    
    def get_quote(self, symbol: str) -> dict | None:
        """Fetches live quote for a symbol using correct Angel One API."""
        try:
            token = self._get_symbol_token(symbol)
            if not token:
                logger.error(f"No token found for symbol: {symbol}")
                return None
            
            # Use the correct ltpData method
            quote_data = self.smart_api.ltpData("NSE", symbol, token)
            
            if quote_data and quote_data.get("status"):
                data = quote_data.get("data", {})
                if isinstance(data, dict):
                    ltp = float(data.get("ltp", 0))
                    close = float(data.get("close", ltp))
                    change = ltp - close if close > 0 else 0
                    change_percent = (change / close * 100) if close > 0 else 0
                    
                    logger.info(f"Quote for {symbol}: LTP={ltp}, Change={change}")
                    return {
                        "ltp": ltp,
                        "change": change,
                        "pChange": change_percent
                    }
                else:
                    logger.error(f"Invalid data format for {symbol}: {data}")
                    return None
            else:
                error_msg = quote_data.get('message', 'No response') if quote_data else 'No response'
                logger.error(f"Failed to fetch quote for {symbol}: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}", exc_info=True)
            return None
    
    def get_holdings(self) -> list | None:
        """Fetches holdings data."""
        try:
            holdings_data = self.smart_api.holding()
            if holdings_data and holdings_data.get("status"):
                return holdings_data.get("data", [])
            else:
                logger.error(f"Failed to fetch holdings: {holdings_data.get('message') if holdings_data else 'No response'}")
                return None
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}", exc_info=True)
            return None
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get token for symbol"""
        token_map = {
            "NIFTY": "99926000",
            "BANKNIFTY": "99926009", 
            "FINNIFTY": "99926037"
        }
        return token_map.get(symbol, "")
