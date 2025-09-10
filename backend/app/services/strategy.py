import asyncio
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time, timedelta
import numpy as np

from ..core.config import settings, StrategyConfig
from ..core.logging import logger
from .order_manager import OrderManager
from .risk_manager import RiskManager
from .market_data_manager import market_data_manager
from .instrument_manager import instrument_manager
from ..db.session import database
from ..models.trading import Candle

class TradingStrategy:
    """
    Implements the core scalping strategy, generating signals based on technical indicators.
    """
    def __init__(self, order_manager: OrderManager, risk_manager: RiskManager, connector):
        logger.info("Initializing Trading Strategy...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.connector = connector
        self.params = settings.strategy # Hold a local copy of the params
        self.instruments = self.params.instruments
        self.is_running = False
        self.active_trades = {}
        self.candle_history = {symbol: pd.DataFrame() for symbol in self.instruments}

    def update_parameters(self, new_params: StrategyConfig):
        """
        Updates the strategy parameters safely.
        """
        logger.info(f"Updating strategy parameters to: {new_params.dict()}")
        self.params = new_params
        # If instruments change, we would need more complex logic to re-subscribe websockets etc.
        # For now, we assume the instrument list is static.
        self.instruments = self.params.instruments
        logger.info("Strategy parameters updated.")

    async def warm_up(self):
        """
        Loads the last N candles from the database to warm up indicators.
        """
        logger.info("Warming up indicators with historical data from database...")
        for symbol in self.instruments:
            try:
                query = Candle.__table__.select().where(Candle.symbol == symbol).order_by(Candle.ts.desc()).limit(200)
                results = await database.fetch_all(query)
                if results:
                    # The data is fetched in descending order, so we need to reverse it
                    results.reverse()
                    df = pd.DataFrame(results)
                    df['timestamp'] = pd.to_datetime(df['ts'])
                    df.set_index('timestamp', inplace=True)
                    self.candle_history[symbol] = df
                    logger.info(f"Successfully warmed up {len(df)} candles for {symbol} from DB.")
                else:
                    logger.warning(f"No historical data found in DB for {symbol}. Will build history from live data.")
            except Exception as e:
                logger.error(f"Error during DB warm-up for {symbol}: {e}", exc_info=True)
        logger.info("Indicator warm-up complete.")

    def start(self):
        self.is_running = True
        logger.info("Trading Strategy started.")

    def stop(self):
        self.is_running = False
        logger.info("Trading Strategy stopped.")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates all required technical indicators using pandas-ta."""
        df.ta.ema(length=self.params.ema_short, append=True, col_names=(f'EMA_{self.params.ema_short}',))
        df.ta.ema(length=self.params.ema_long, append=True, col_names=(f'EMA_{self.params.ema_long}',))
        df.ta.vwap(append=True, col_names=('VWAP',))
        df.ta.supertrend(period=self.params.supertrend_period,
                         multiplier=self.params.supertrend_multiplier,
                         append=True, col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        df.ta.atr(length=self.params.atr_period, append=True, col_names=(f'ATR_{self.params.atr_period}',))
        return df

    async def check_entry_conditions(self, symbol: str):
        """Checks for trade entry signals based on the latest candle data."""
        try:
            df = self.candle_history.get(symbol)
            if df is None or df.empty or len(df) < self.params.ema_long:
                logger.debug(f"Not enough candle data to check entry for {symbol}.")
                return

            df = self.calculate_indicators(df.copy())
            latest = df.iloc[-1]
            price = latest['close']
            atr = latest[f'ATR_{self.params.atr_period}']

            required_cols = [f'EMA_{self.params.ema_short}', f'EMA_{self.params.ema_long}', 'VWAP', 'SUPERTd', f'ATR_{self.params.atr_period}']
            if latest[required_cols].hasnans:
                logger.debug(f"Indicators not ready for {symbol}. Skipping.")
                return

            is_buy_signal = (latest[f'EMA_{self.params.ema_short}'] > latest[f'EMA_{self.params.ema_long}'] and
                             price > latest['VWAP'] and latest['SUPERTd'] == 1)
            is_sell_signal = (latest[f'EMA_{self.params.ema_short}'] < latest[f'EMA_{self.params.ema_long}'] and
                              price < latest['VWAP'] and latest['SUPERTd'] == -1)

            if is_buy_signal:
                signal = {'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'BUY', 'entry': price,
                          'sl': price - (1 * atr), 'tp': price + (0.6 * atr), 'atr_at_entry': atr,
                          'reason': 'EMA_VWAP_ST_BUY'}
                logger.info(f"BUY Signal generated: {signal}")
                await self.order_manager.handle_signal(signal)
            elif is_sell_signal:
                signal = {'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'SELL', 'entry': price,
                          'sl': price + (1 * atr), 'tp': price - (0.6 * atr), 'atr_at_entry': atr,
                          'reason': 'EMA_VWAP_ST_SELL'}
                logger.info(f"SELL Signal generated: {signal}")
                await self.order_manager.handle_signal(signal)
        except Exception as e:
            logger.error(f"Error checking entry conditions for {symbol}: {e}", exc_info=True)

    async def update_and_check_candles(self):
        """
        Checks for new 1-minute candles from the MarketDataManager,
        updates the history, and triggers entry condition checks.
        """
        for symbol in self.instruments:
            # get_1m_candle now returns a new, completed candle that was saved to DB, or None
            new_candle_df = await market_data_manager.get_1m_candle(symbol)
            if new_candle_df is not None:
                logger.info(f"New 1m candle processed for {symbol} at {new_candle_df.index[0]}.")
                # Append the new candle and check for signals
                self.candle_history[symbol] = pd.concat([self.candle_history[symbol], new_candle_df])
                self.candle_history[symbol] = self.candle_history[symbol].tail(200)

                await self.check_entry_conditions(symbol)

    async def manage_active_trades(self):
        """Manages exits for active trades."""
        open_positions = self.order_manager.get_open_positions()
        if not open_positions:
            return
        for position in open_positions:
            symbol = position['symbol']
            live_price = await market_data_manager.get_latest_price(symbol)
            if not live_price:
                logger.warning(f"Could not get live price for {symbol} to manage position.")
                continue

            side, sl, tp, entry_time = position['side'], position['sl'], position['tp'], position['entry_time']
            is_sl_hit = (side == 'BUY' and live_price <= sl) or (side == 'SELL' and live_price >= sl)
            is_tp_hit = (side == 'BUY' and live_price >= tp) or (side == 'SELL' and live_price <= tp)
            is_time_exit = (datetime.utcnow() - entry_time) > timedelta(minutes=5)

            if is_sl_hit:
                logger.info(f"Stop-loss hit for {symbol}. Closing position.")
                await self.order_manager.close_position(position, "STOP_LOSS_HIT")
            elif is_tp_hit:
                logger.info(f"Take-profit hit for {symbol}. Closing position.")
                await self.order_manager.close_position(position, "TAKE_PROFIT_HIT")
            elif is_time_exit:
                logger.info(f"Time-based exit for {symbol}. Closing position.")
                await self.order_manager.close_position(position, "TIME_EXIT")
            else:
                atr = position.get('atr_at_entry', 0)
                if atr > 0:
                    trail_amount = 1.5 * atr
                    if side == 'BUY':
                        new_sl = max(sl, live_price - trail_amount)
                        if new_sl > sl:
                            self.order_manager.update_position_sl(position, new_sl)
                    elif side == 'SELL':
                        new_sl = min(sl, live_price + trail_amount)
                        if new_sl < sl:
                            self.order_manager.update_position_sl(position, new_sl)

    async def run(self):
        """The main loop of the trading strategy."""
        await self.warm_up()
        while True:
            await asyncio.sleep(1)
            if not self.is_running or self.risk_manager.is_trading_stopped:
                continue

            now_time = datetime.now().time()
            start_time = time.fromisoformat(settings.trading.hours['start'])
            end_time = time.fromisoformat(settings.trading.hours['end'])

            if not (start_time <= now_time < end_time):
                if self.active_trades:
                    logger.info("Outside trading hours. Closing all open positions...")
                await asyncio.sleep(30)
                continue

            try:
                await self.update_and_check_candles()
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)
