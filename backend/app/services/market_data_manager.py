import asyncio
from datetime import datetime
from typing import Dict, Optional, Any
from ..core.logging import logger

class MarketDataManager:
    """
    Manages real-time market data from the broker.
    Stores and provides access to live prices, ticks, and market information.
    """
    
    def __init__(self):
        self.latest_prices: Dict[str, Dict[str, Any]] = {}
        self.last_tick_time: Optional[datetime] = None
        self.price_history: Dict[str, list] = {}
        
    def update_tick(self, tick_data: Dict[str, Any]) -> None:
        """
        Updates the latest price data from incoming tick.
        
        Args:
            tick_data: Raw tick data from broker
        """
        try:
            if isinstance(tick_data, dict):
                symbol = tick_data.get('symbol', tick_data.get('token', ''))
                if symbol:
                    self.latest_prices[symbol] = {
                        'ltp': tick_data.get('ltp', tick_data.get('last_price', 0)),
                        'volume': tick_data.get('volume', 0),
                        'oi': tick_data.get('oi', tick_data.get('open_interest', 0)),
                        'change': tick_data.get('change', 0),
                        'changePercent': tick_data.get('changePercent', 0),
                        'timestamp': datetime.now()
                    }
                    self.last_tick_time = datetime.now()
                    
                    # Store price history (keep last 100 ticks)
                    if symbol not in self.price_history:
                        self.price_history[symbol] = []
                    
                    self.price_history[symbol].append({
                        'price': self.latest_prices[symbol]['ltp'],
                        'timestamp': self.last_tick_time
                    })
                    
                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol].pop(0)
                        
        except Exception as e:
            logger.error(f"Error updating tick data: {e}")
    
    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Gets the latest price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price data or None if not available
        """
        return self.latest_prices.get(symbol)
    
    def get_last_tick_time(self) -> Optional[datetime]:
        """
        Returns the timestamp of the last received tick.
        
        Returns:
            Last tick timestamp or None
        """
        return self.last_tick_time
    
    def get_price_history(self, symbol: str, limit: int = 50) -> list:
        """
        Gets price history for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Number of historical points to return
            
        Returns:
            List of historical price data
        """
        history = self.price_history.get(symbol, [])
        return history[-limit:] if history else []
    
    def get_all_symbols(self) -> list:
        """
        Returns all symbols with available price data.
        
        Returns:
            List of symbols
        """
        return list(self.latest_prices.keys())
    
    def is_data_fresh(self, max_age_seconds: int = 30) -> bool:
        """
        Checks if the latest data is fresh (within specified age).
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            True if data is fresh, False otherwise
        """
        if not self.last_tick_time:
            return False
        
        age = (datetime.now() - self.last_tick_time).total_seconds()
        return age <= max_age_seconds
    
    def get_indices_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Gets formatted indices data for frontend.
        
        Returns:
            Dictionary with indices data
        """
        indices = {}
        index_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
        
        for symbol in index_symbols:
            price_data = self.latest_prices.get(symbol, {})
            if price_data:
                indices[symbol] = {
                    'price': price_data.get('ltp', 0),
                    'change': price_data.get('change', 0),
                    'changePercent': price_data.get('changePercent', 0)
                }
            else:
                indices[symbol] = {'price': 0, 'change': 0, 'changePercent': 0}
        
        return indices
    
    def get_options_chain_data(self, symbol: str, strikes: list) -> list:
        """
        Gets options chain data for given strikes.
        
        Args:
            symbol: Base symbol (e.g., 'BANKNIFTY')
            strikes: List of strike prices
            
        Returns:
            List of options data
        """
        options_data = []
        
        for strike in strikes:
            call_symbol = f"{symbol}{strike}CE"
            put_symbol = f"{symbol}{strike}PE"
            
            call_data = self.latest_prices.get(call_symbol, {})
            put_data = self.latest_prices.get(put_symbol, {})
            
            options_data.append({
                'strike': strike,
                'call': {
                    'ltp': call_data.get('ltp', 0),
                    'volume': call_data.get('volume', 0),
                    'oi': call_data.get('oi', 0),
                    'iv': call_data.get('iv', 0)
                },
                'put': {
                    'ltp': put_data.get('ltp', 0),
                    'volume': put_data.get('volume', 0),
                    'oi': put_data.get('oi', 0),
                    'iv': put_data.get('iv', 0)
                }
            })
        
        return options_data

# Global instance
market_data_manager = MarketDataManager()