import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from ..core.logging import logger
from ..db.session import database
from ..models.trading import Candle

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
        self.last_tick_time = None
        self._initialized = True
        logger.info("MarketDataManager initialized.")

    def update_tick(self, tick_data: dict):
        """
        Updates the latest tick for a given instrument and records the time.
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
        Builds a 1-minute OHLCV candle from the stored ticks, saves it to the DB,
        and returns the new candle.
        """
        ticks = self.candle_data.get(symbol, [])
        if not ticks:
            return None

        df = pd.DataFrame(ticks)
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)

        # Resample to 1 minute. We lack real volume, so it's omitted.
        ohlc = df['price'].resample('1Min').ohlc()

        # We only care about the most recently completed candle
        if len(ohlc) < 1:
            return None

        last_candle = ohlc.iloc[-1]

        # Clear old ticks to prevent memory leak, keeping only the current minute's ticks
        now = datetime.now()
        current_minute_start = now.replace(second=0, microsecond=0)
        self.candle_data[symbol] = [t for t in ticks if t['ts'] >= current_minute_start]

        # Save the new candle to the database
        try:
            candle_data_to_save = {
                "symbol": symbol,
                "ts": last_candle.name.to_pydatetime(),
                "open": last_candle.open,
                "high": last_candle.high,
                "low": last_candle.low,
                "close": last_candle.close,
                "volume": 0 # Volume is not available from ticks yet
            }
            # Check if this candle already exists to prevent duplicates
            query = Candle.__table__.select().where(
                (Candle.symbol == symbol) & (Candle.ts == candle_data_to_save['ts'])
            )
            exists = await database.fetch_one(query)
            if not exists:
                insert_query = Candle.__table__.insert().values(candle_data_to_save)
                await database.execute(insert_query)
                logger.info(f"Saved new 1m candle for {symbol} at {candle_data_to_save['ts']} to DB.")
        except Exception as e:
            logger.error(f"Failed to save candle for {symbol} to DB: {e}", exc_info=True)

        return pd.DataFrame([last_candle])

# Create a single instance of the market data manager
market_data_manager = MarketDataManager()
