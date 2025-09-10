from typing import Dict, Optional
from ..core.logging import logger
from ..core.config import settings
from datetime import datetime, timedelta

class InstrumentManager:
    def __init__(self):
        self.instruments = []
        self.symbol_to_token = {}
        self.token_to_symbol = {}
        self.is_map_built = False
        self.is_reverse_map_built = False

    async def load_instruments(self, rest_client):
        """
        Load instruments from the broker API and filter for relevant F&O contracts.
        """
        try:
            raw_instruments = await rest_client.get_instrument_list()
            if not raw_instruments:
                logger.error("Failed to load instruments or instrument list is empty.")
                return

            logger.info(f"Loaded {len(raw_instruments)} raw instruments. Filtering now...")

            trade_indices = settings.strategy.trade_indices
            instrument_types = settings.strategy.instrument_types

            pre_filtered_instruments = [
                inst for inst in raw_instruments
                if inst.get('exch_seg') == 'NFO' and \
                   inst.get('name') in trade_indices and \
                   inst.get('instrumenttype') in instrument_types and \
                   inst.get('expiry')
            ]

            logger.info(f"Found {len(pre_filtered_instruments)} instruments after basic filtering by name and type.")

            # Further filter by expiry date (e.g., contracts expiring within the next 45 days)
            # This is a heuristic to focus on active, near-term contracts.
            final_instruments = []
            today = datetime.now().date()
            expiry_limit = today + timedelta(days=45)

            for inst in pre_filtered_instruments:
                try:
                    expiry_date = datetime.strptime(inst['expiry'], '%d%b%Y').date()
                    if today <= expiry_date <= expiry_limit:
                        final_instruments.append(inst)
                except (ValueError, KeyError):
                    # Skip instruments with unparsable expiry dates
                    continue

            self.instruments = final_instruments
            logger.info(f"Loaded {len(self.instruments)} instruments after all filtering.")

            # Reset and rebuild the maps with the filtered list
            self.is_map_built = False
            self.is_reverse_map_built = False
            self._build_map()
            self._build_reverse_map()

        except Exception as e:
            logger.error(f"Error during instrument loading and filtering: {e}", exc_info=True)

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

    def get_token(self, symbol: str, exchange: str = "NFO") -> Optional[str]:
        """Get token for a symbol using an exact match from the filtered list."""
        if not self.is_map_built:
            self._build_map()
        
        return self.symbol_to_token.get(symbol)

    def get_symbol(self, token: str) -> Optional[str]:
        """Get symbol for a token"""
        if not self.is_reverse_map_built:
            self._build_reverse_map()
        
        return self.token_to_symbol.get(token)

# Global instance
instrument_manager = InstrumentManager()