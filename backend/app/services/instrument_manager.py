from typing import Dict, Optional, List
from ..core.logging import logger
from ..core.config import settings
from datetime import datetime, timedelta
import re

class InstrumentManager:
    def __init__(self):
        self.instruments = []
        self.symbol_to_token = {}
        self.token_to_symbol = {}
        self.is_map_built = False
        self.is_reverse_map_built = False

    async def load_instruments(self, rest_client):
        """
        Load options instruments optimized for scalping.
        """
        try:
            raw_instruments = await rest_client.get_instrument_list()
            if not raw_instruments:
                logger.error("Failed to load instruments or instrument list is empty.")
                return

            logger.info(f"Loaded {len(raw_instruments)} raw instruments. Filtering for options scalping...")

            trade_indices = settings.strategy.trade_indices
            instrument_types = settings.strategy.instrument_types
            max_days_to_expiry = settings.strategy.expiry_preference.max_days_to_expiry

            # Filter for options only
            options_instruments = [
                inst for inst in raw_instruments
                if inst.get('exch_seg') == 'NFO' and \
                   inst.get('name') in trade_indices and \
                   inst.get('instrumenttype') in instrument_types and \
                   inst.get('expiry') and \
                   inst.get('symbol')
            ]

            logger.info(f"Found {len(options_instruments)} options after basic filtering.")

            # Filter by expiry (weekly/monthly preference)
            final_instruments = []
            today = datetime.now().date()
            
            for inst in options_instruments:
                try:
                    expiry_date = datetime.strptime(inst['expiry'], '%d%b%Y').date()
                    days_to_expiry = (expiry_date - today).days
                    
                    # Only include options expiring within max_days_to_expiry
                    if 0 <= days_to_expiry <= max_days_to_expiry:
                        # Additional filtering for liquid options
                        if self._is_liquid_option(inst):
                            final_instruments.append(inst)
                            
                except (ValueError, KeyError):
                    continue

            self.instruments = final_instruments
            logger.info(f"Loaded {len(self.instruments)} liquid options for scalping.")

            # Reset and rebuild the maps
            self.is_map_built = False
            self.is_reverse_map_built = False
            self._build_map()
            self._build_reverse_map()

        except Exception as e:
            logger.error(f"Error during options instrument loading: {e}", exc_info=True)

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

    def _is_liquid_option(self, instrument: Dict) -> bool:
        """Check if option is liquid enough for scalping."""
        try:
            symbol = instrument.get('symbol', '')
            
            # Parse strike price from symbol
            strike_match = re.search(r'(\d+)(CE|PE)$', symbol)
            if not strike_match:
                return False
                
            strike = int(strike_match.group(1))
            option_type = strike_match.group(2)
            
            # Filter by strike intervals (standard strikes only)
            if 'BANKNIFTY' in symbol:
                return strike % 100 == 0  # Only 100-point intervals
            else:  # NIFTY, FINNIFTY
                return strike % 50 == 0   # Only 50-point intervals
                
        except:
            return False
    
    def get_options_by_expiry_and_type(self, index: str, expiry: str, option_type: str) -> List[Dict]:
        """Get all options for a specific index, expiry, and type."""
        matching_options = []
        
        for instrument in self.instruments:
            if (instrument.get('name') == index and 
                instrument.get('expiry') == expiry and 
                instrument.get('symbol', '').endswith(option_type)):
                matching_options.append(instrument)
        
        return matching_options
    
    def get_atm_options(self, index: str, spot_price: float, expiry: str) -> Dict[str, Optional[Dict]]:
        """Get ATM CE and PE options for given spot price."""
        strike_interval = 100 if index == 'BANKNIFTY' else 50
        atm_strike = round(spot_price / strike_interval) * strike_interval
        
        ce_symbol = f"{index}{expiry}{atm_strike}CE"
        pe_symbol = f"{index}{expiry}{atm_strike}PE"
        
        ce_option = None
        pe_option = None
        
        for instrument in self.instruments:
            if instrument.get('symbol') == ce_symbol:
                ce_option = instrument
            elif instrument.get('symbol') == pe_symbol:
                pe_option = instrument
                
        return {'CE': ce_option, 'PE': pe_option}
    
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
    
    def get_strike_chain(self, index: str, expiry: str, center_strike: int, range_strikes: int = 5) -> List[Dict]:
        """Get options chain around a center strike."""
        strike_interval = 100 if index == 'BANKNIFTY' else 50
        chain = []
        
        for i in range(-range_strikes, range_strikes + 1):
            strike = center_strike + (i * strike_interval)
            
            for option_type in ['CE', 'PE']:
                symbol = f"{index}{expiry}{strike}{option_type}"
                
                for instrument in self.instruments:
                    if instrument.get('symbol') == symbol:
                        chain.append({
                            'symbol': symbol,
                            'strike': strike,
                            'option_type': option_type,
                            'token': instrument.get('token'),
                            'instrument': instrument
                        })
                        break
        
        return sorted(chain, key=lambda x: (x['strike'], x['option_type']))

# Global instance
instrument_manager = InstrumentManager()