from app.core.logging import logger
from collections import defaultdict

class InstrumentManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InstrumentManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.instrument_list = []
        self.symbol_to_token_map = defaultdict(dict)
        self._initialized = True
        logger.info("InstrumentManager initialized.")

    async def load_instruments(self, rest_client):
        """
        Loads the instrument list from the rest client and builds the symbol-to-token map.
        """
        if not self.instrument_list:
            logger.info("Loading instruments for the first time...")
            instruments = await rest_client.get_instrument_list()
            if instruments:
                self.instrument_list = instruments
                self._build_map()
                logger.info(f"Instrument map built with {len(self.instrument_list)} instruments.")
            else:
                logger.error("Failed to load instruments.")
        else:
            logger.info("Instruments are already loaded.")

    def _build_map(self):
        """
        Builds a mapping from tradingsymbol to token for faster lookups.
        """
        for instrument in self.instrument_list:
            symbol = instrument.get("tradingsymbol")
            token = instrument.get("token")
            exchange = instrument.get("exch_seg")
            if symbol and token and exchange:
                self.symbol_to_token_map[symbol][exchange] = token

    def get_token(self, symbol: str, exchange: str = "NSE") -> str | None:
        """
        Gets the token for a given symbol and exchange.
        """
        if not self.symbol_to_token_map:
            logger.warning("Instrument map is not built. Call load_instruments first.")
            return None

        exchange_map = self.symbol_to_token_map.get(symbol)
        if not exchange_map:
            logger.error(f"Symbol '{symbol}' not found in instrument map.")
            return None

        token = exchange_map.get(exchange.upper())
        if not token:
            logger.error(f"Token for symbol '{symbol}' with exchange '{exchange}' not found.")
            return None

        return token

    def get_underlying_config(self, underlying: str) -> dict | None:
        """
        Gets the configuration for a given underlying from the settings file.
        """
        from app.core.config import settings
        return settings.underlying_instruments.get(underlying)

# Create a single instance of the instrument manager
instrument_manager = InstrumentManager()
