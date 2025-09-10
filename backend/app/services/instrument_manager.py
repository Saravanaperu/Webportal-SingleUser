from typing import Dict, Optional
from ..core.logging import logger

class InstrumentManager:
    def __init__(self):
        self.instruments = []
        self.symbol_to_token = {}
        self.token_to_symbol = {}
        self.is_map_built = False
        self.is_reverse_map_built = False

    async def load_instruments(self, rest_client):
        """Load instruments from the broker API"""
        try:
            instruments = await rest_client.get_instrument_list()
            if instruments:
                self.instruments = instruments
                logger.info(f"Loaded {len(instruments)} instruments")
            else:
                logger.error("Failed to load instruments")
        except Exception as e:
            logger.error(f"Error loading instruments: {e}")

    def _build_map(self):
        """Build symbol to token mapping"""
        if self.is_map_built:
            return
        
        for instrument in self.instruments:
            symbol = instrument.get('symbol')
            token = instrument.get('token')
            if symbol and token:
                self.symbol_to_token[symbol] = token
        
        self.is_map_built = True
        logger.info(f"Built symbol-to-token map with {len(self.symbol_to_token)} entries")

    def _build_reverse_map(self):
        """Build token to symbol mapping"""
        if self.is_reverse_map_built:
            return
        
        if not self.is_map_built:
            self._build_map()
        
        for symbol, token in self.symbol_to_token.items():
            self.token_to_symbol[token] = symbol
        
        self.is_reverse_map_built = True

    def get_token(self, symbol: str, exchange: str = "NSE") -> Optional[str]:
        """Get token for a symbol"""
        if not self.is_map_built:
            self._build_map()
        
        # Try exact match first
        token = self.symbol_to_token.get(symbol)
        if token:
            return token
        
        # Try with exchange suffix
        symbol_with_exchange = f"{symbol}-EQ"
        return self.symbol_to_token.get(symbol_with_exchange)

    def get_symbol(self, token: str) -> Optional[str]:
        """Get symbol for a token"""
        if not self.is_reverse_map_built:
            self._build_reverse_map()
        
        return self.token_to_symbol.get(token)

# Global instance
instrument_manager = InstrumentManager()