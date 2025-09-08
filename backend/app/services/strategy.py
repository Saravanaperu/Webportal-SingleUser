import asyncio
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.order_manager import OrderManager
from app.services.risk_manager import RiskManager

class TradingStrategy:
    """
    Implements the core scalping strategy, generating signals based on technical indicators.
    """
    def __init__(self, order_manager: OrderManager, risk_manager: RiskManager):
        logger.info("Initializing Trading Strategy...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.instruments = settings.strategy.instruments
        self.is_running = False
        self.active_trades = {}  # Placeholder for managing exits

    def start(self):
        """Starts the strategy loop."""
        self.is_running = True
        logger.info("Trading Strategy started.")

    def stop(self):
        """Stops the strategy loop."""
        self.is_running = False
        logger.info("Trading Strategy stopped.")

    async def get_candle_data(self, symbol: str) -> pd.DataFrame:
        """
        Placeholder for fetching candle data.
        In a real application, this would fetch from the broker API or a database
        that is populated by the WebSocket client.
        """
        logger.debug(f"Generating dummy candle data for {symbol}...")
        # Generate 50 periods of dummy data for indicators to warm up
        dates = pd.to_datetime(pd.date_range(end=datetime.now(), periods=50, freq="min"))
        price_data = 100 + np.random.randn(50).cumsum() * 0.2
        data = {
            'open': price_data - np.random.rand(50) * 0.1,
            'high': price_data + np.random.rand(50) * 0.1,
            'low': price_data - np.random.rand(50) * 0.1,
            'close': price_data,
            'volume': np.random.randint(1000, 5000, 50)
        }
        df = pd.DataFrame(data, index=dates)
        df.index.name = "timestamp"
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates all required technical indicators using pandas-ta."""
        df.ta.ema(length=settings.strategy.ema_short, append=True, col_names=(f'EMA_{settings.strategy.ema_short}',))
        df.ta.ema(length=settings.strategy.ema_long, append=True, col_names=(f'EMA_{settings.strategy.ema_long}',))
        df.ta.vwap(append=True, col_names=('VWAP',))
        df.ta.supertrend(period=settings.strategy.supertrend_period,
                         multiplier=settings.strategy.supertrend_multiplier,
                         append=True,
                         col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        df.ta.atr(length=settings.strategy.atr_period, append=True, col_names=(f'ATR_{settings.strategy.atr_period}',))
        return df

    async def check_entry_conditions(self, symbol: str):
        """Fetches data, calculates indicators, and checks for trade entry signals."""
        try:
            df = await self.get_candle_data(symbol)
            df = self.calculate_indicators(df)

            if df.empty:
                return

            latest = df.iloc[-1]
            price = latest['close']
            atr = latest[f'ATR_{settings.strategy.atr_period}']

            # Ensure indicators are not NaN
            required_cols = [f'EMA_{settings.strategy.ema_short}', f'EMA_{settings.strategy.ema_long}', 'VWAP', 'SUPERTd', f'ATR_{settings.strategy.atr_period}']
            if latest[required_cols].hasnans:
                logger.debug(f"Indicators not ready for {symbol}. Skipping.")
                return

            # Entry Conditions
            is_buy_signal = (latest[f'EMA_{settings.strategy.ema_short}'] > latest[f'EMA_{settings.strategy.ema_long}'] and
                             price > latest['VWAP'] and
                             latest['SUPERTd'] == 1) # 1 for uptrend

            is_sell_signal = (latest[f'EMA_{settings.strategy.ema_short}'] < latest[f'EMA_{settings.strategy.ema_long}'] and
                              price < latest['VWAP'] and
                              latest['SUPERTd'] == -1) # -1 for downtrend

            if is_buy_signal:
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'BUY',
                    'entry': price, 'sl': price - (1 * atr), 'tp': price + (0.6 * atr),
                    'reason': 'EMA_VWAP_ST_BUY'
                }
                logger.info(f"BUY Signal generated: {signal}")
                await self.order_manager.handle_signal(signal)
            elif is_sell_signal:
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'SELL',
                    'entry': price, 'sl': price + (1 * atr), 'tp': price - (0.6 * atr),
                    'reason': 'EMA_VWAP_ST_SELL'
                }
                logger.info(f"SELL Signal generated: {signal}")
                await self.order_manager.handle_signal(signal)
        except Exception as e:
            logger.error(f"Error checking entry conditions for {symbol}: {e}", exc_info=True)

    async def manage_active_trades(self):
        """
        Manages exits for active trades (TP, SL, TSL, time-based).
        This is a placeholder for a very complex piece of logic.
        """
        # This would involve:
        # 1. Querying the database for open positions.
        # 2. Getting live price data for those positions.
        # 3. Checking each position against its SL and TP.
        # 4. Implementing the trailing stop-loss logic.
        # 5. Implementing the 5-minute auto-close logic.
        # 6. Creating exit orders via the OrderManager.
        pass

    async def run(self):
        """The main loop of the trading strategy."""
        while True:
            await asyncio.sleep(1) # Small sleep to prevent tight loop if stopped
            if not self.is_running or self.risk_manager.is_trading_stopped:
                continue

            now = datetime.now().time()
            start_time = time.fromisoformat(settings.trading.hours['start'])
            end_time = time.fromisoformat(settings.trading.hours['end'])

            if not (start_time <= now < end_time):
                if self.active_trades:
                    logger.info("Outside trading hours. Closing all open positions...")
                    # await self.order_manager.close_all_positions()
                await asyncio.sleep(30) # Check again in 30s
                continue

            logger.info("Running strategy cycle...")
            try:
                entry_tasks = [self.check_entry_conditions(symbol) for symbol in self.instruments]
                await asyncio.gather(*entry_tasks)
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)

            # Wait for the start of the next minute
            current_time = datetime.now()
            sleep_seconds = 60 - current_time.second
            await asyncio.sleep(sleep_seconds)
