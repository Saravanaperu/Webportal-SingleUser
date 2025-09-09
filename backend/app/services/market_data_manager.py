import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from app.core.logging import logger

class MarketDataManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MarketDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.latest_ticks = {}
        self.candle_data = defaultdict(list)
        self._initialized = True
        logger.info("MarketDataManager initialized.")

    def update_tick(self, tick_data: dict):
        """
        Updates the latest tick for a given instrument.
        This is where the raw WebSocket message would be parsed and stored.
        """
        from .instrument_manager import instrument_manager

        # The tick format from the smartapi-python library needs to be known.
        # Assuming a format like: {'token': '2885', 'ltp': '123.45', 'timestamp': ...}
        # This needs to be verified against the actual data.
        symbol_token = tick_data.get('tk')
        ltp = tick_data.get('ltp')

        if symbol_token and ltp:
            symbol = instrument_manager.get_symbol(symbol_token)
            if not symbol:
                logger.warning(f"Received tick for unknown token: {symbol_token}")
                return

            price = float(ltp)
            tick_time = datetime.now() # Ideally use a server timestamp from the tick

            self.latest_ticks[symbol] = {"price": price, "ts": tick_time}
            self.candle_data[symbol].append({"price": price, "ts": tick_time})
            logger.debug(f"Tick updated for {symbol}: {self.latest_ticks[symbol]}")

    async def get_latest_price(self, symbol: str) -> float | None:
        tick = self.latest_ticks.get(symbol)
        return tick['price'] if tick else None

    async def get_1m_candle(self, symbol: str) -> pd.DataFrame | None:
        """
        Builds a 1-minute OHLCV candle from the stored ticks.
        """
        ticks = self.candle_data.get(symbol, [])
        if not ticks:
            return None

        df = pd.DataFrame(ticks)
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)

        # Resample to 1 minute
        # We need a volume component to do this properly, which we don't have yet.
        # We will simulate it for now.
        ohlc = df['price'].resample('1Min').ohlc()

        # Clear old ticks to prevent memory leak
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        self.candle_data[symbol] = [t for t in ticks if t['ts'] > one_minute_ago]

        return ohlc.tail(1) # Return the last complete candle

# Create a single instance of the market data manager
market_data_manager = MarketDataManager()
