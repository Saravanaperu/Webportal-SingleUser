import asyncio
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time, timedelta
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.order_manager import OrderManager
from app.services.risk_manager import RiskManager
from app.services.market_data_manager import market_data_manager
from app.services.instrument_manager import instrument_manager

class TradingStrategy:
    """
    Implements the core scalping strategy, generating signals based on technical indicators.
    """
    def __init__(self, order_manager: OrderManager, risk_manager: RiskManager, connector):
        logger.info("Initializing Trading Strategy...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.connector = connector
        self.instruments = settings.strategy.instruments
        self.is_running = False
        self.active_trades = {}
        self.candle_history = {symbol: pd.DataFrame() for symbol in self.instruments}

    async def warm_up(self):
        """
        Fetches historical data to warm up the indicators for all instruments.
        """
        logger.info("Warming up indicators with historical data...")
        for symbol in self.instruments:
            try:
                token = instrument_manager.get_token(symbol, "NSE")
                if not token:
                    logger.error(f"Could not get token for {symbol} during warm-up.")
                    continue

                # Fetch last 100 minutes of data to have enough for indicators
                historic_params = {
                    "exchange": "NSE",
                    "symboltoken": token,
                    "interval": "ONE_MINUTE",
                    "fromdate": (datetime.now() - timedelta(minutes=100)).strftime('%Y-%m-%d %H:%M'),
                    "todate": datetime.now().strftime('%Y-%m-%d %H:%M')
                }

                data = await self.connector.get_candle_data(historic_params)

                if data and isinstance(data, list):
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    self.candle_history[symbol] = df
                    logger.info(f"Successfully warmed up {len(df)} candles for {symbol}.")
                else:
                    logger.warning(f"Could not fetch historical data for {symbol}. Response: {data}")

            except Exception as e:
                logger.error(f"Error during warm-up for {symbol}: {e}", exc_info=True)
        logger.info("Indicator warm-up complete.")

    def start(self):
        """Starts the strategy loop."""
        self.is_running = True
        logger.info("Trading Strategy started.")

    def stop(self):
        """Stops the strategy loop."""
        self.is_running = False
        logger.info("Trading Strategy stopped.")

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
            # The main logic will now be triggered by new candles from the MarketDataManager
            # This function will be refactored or triggered differently.
            # For now, we get the latest full candle from our history.
            df = self.candle_history.get(symbol)
            if df is None or df.empty or len(df) < settings.strategy.ema_long:
                logger.debug(f"Not enough candle data to check entry for {symbol}.")
                return

            df = self.calculate_indicators(df.copy()) # Use copy to avoid modifying history

            latest = df.iloc[-1]
            price = latest['close']
            atr = latest[f'ATR_{settings.strategy.atr_period}']

            required_cols = [f'EMA_{settings.strategy.ema_short}', f'EMA_{settings.strategy.ema_long}', 'VWAP', 'SUPERTd', f'ATR_{settings.strategy.atr_period}']
            if latest[required_cols].hasnans:
                logger.debug(f"Indicators not ready for {symbol}. Skipping.")
                return

            is_buy_signal = (latest[f'EMA_{settings.strategy.ema_short}'] > latest[f'EMA_{settings.strategy.ema_long}'] and
                             price > latest['VWAP'] and
                             latest['SUPERTd'] == 1)

            is_sell_signal = (latest[f'EMA_{settings.strategy.ema_short}'] < latest[f'EMA_{settings.strategy.ema_long}'] and
                              price < latest['VWAP'] and
                              latest['SUPERTd'] == -1)

            if is_buy_signal:
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'BUY',
                    'entry': price, 'sl': price - (1 * atr), 'tp': price + (0.6 * atr),
                    'atr_at_entry': atr,
                    'reason': 'EMA_VWAP_ST_BUY'
                }
                logger.info(f"BUY Signal generated: {signal}")
                await self.order_manager.handle_signal(signal)
            elif is_sell_signal:
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'SELL',
                    'entry': price, 'sl': price + (1 * atr), 'tp': price - (0.6 * atr),
                    'atr_at_entry': atr,
                    'reason': 'EMA_VWAP_ST_SELL'
                }
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
            new_candle_df = await market_data_manager.get_1m_candle(symbol)
            if new_candle_df is not None and not new_candle_df.empty:
                last_known_candle_time = self.candle_history[symbol].index[-1] if not self.candle_history[symbol].empty else None
                new_candle_time = new_candle_df.index[0]

                if last_known_candle_time is None or new_candle_time > last_known_candle_time:
                    # This is a new candle, append it and check for signals
                    logger.info(f"New 1m candle received for {symbol} at {new_candle_time}.")
                    self.candle_history[symbol] = pd.concat([self.candle_history[symbol], new_candle_df])
                    # Keep history to a reasonable size to prevent memory leaks
                    self.candle_history[symbol] = self.candle_history[symbol].tail(200)

                    await self.check_entry_conditions(symbol)

    async def manage_active_trades(self):
        """
        Manages exits for active trades (TP, SL, TSL, time-based).
        """
        open_positions = self.order_manager.get_open_positions() # This method needs to be created
        if not open_positions:
            return

        for position in open_positions:
            symbol = position['symbol']
            live_price = await market_data_manager.get_latest_price(symbol)

            if not live_price:
                logger.warning(f"Could not get live price for {symbol} to manage position.")
                continue

            side = position['side']
            sl = position['sl']
            tp = position['tp']
            entry_time = position['entry_time']

            # 1. Check for Stop-Loss and Take-Profit
            is_sl_hit = (side == 'BUY' and live_price <= sl) or (side == 'SELL' and live_price >= sl)
            is_tp_hit = (side == 'BUY' and live_price >= tp) or (side == 'SELL' and live_price <= tp)

            # 2. Check for Time-based Exit (e.g., 5 minutes)
            is_time_exit = (datetime.utcnow() - entry_time) > timedelta(minutes=5)

            if is_sl_hit:
                logger.info(f"Stop-loss hit for {symbol} at price {live_price}. Closing position.")
                await self.order_manager.close_position(position, "STOP_LOSS_HIT")
            elif is_tp_hit:
                logger.info(f"Take-profit hit for {symbol} at price {live_price}. Closing position.")
                await self.order_manager.close_position(position, "TAKE_PROFIT_HIT")
            elif is_time_exit:
                logger.info(f"Time-based exit for {symbol} at price {live_price}. Closing position.")
                await self.order_manager.close_position(position, "TIME_EXIT")
            else:
                # 3. Implement Trailing Stop-Loss (if no other exit condition is met)
                # This is a simple TSL implementation. A real one might be more complex.
                atr = position.get('atr_at_entry', 0) # Assumes ATR is stored with position
                if atr > 0:
                    trail_amount = 1.5 * atr
                    if side == 'BUY':
                        new_sl = max(sl, live_price - trail_amount)
                        if new_sl > sl:
                            logger.info(f"Trailing SL for {symbol} from {sl} to {new_sl}")
                            self.order_manager.update_position_sl(position, new_sl)
                    elif side == 'SELL':
                        new_sl = min(sl, live_price + trail_amount)
                        if new_sl < sl:
                            logger.info(f"Trailing SL for {symbol} from {sl} to {new_sl}")
                            self.order_manager.update_position_sl(position, new_sl)


    async def run(self):
        """The main loop of the trading strategy."""
        await self.warm_up()

        while True:
            await asyncio.sleep(1)
            if not self.is_running or self.risk_manager.is_trading_stopped:
                continue

            now = datetime.now().time()
            start_time = time.fromisoformat(settings.trading.hours['start'])
            end_time = time.fromisoformat(settings.trading.hours['end'])

            if not (start_time <= now < end_time):
                if self.active_trades:
                    logger.info("Outside trading hours. Closing all open positions...")
                    # await self.order_manager.close_all_positions()
                await asyncio.sleep(30)
                continue

            try:
                # Instead of running every minute, we check for new candles every second
                await self.update_and_check_candles()
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)
