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
        """Enhanced indicators for high-profit scalping."""
        # Core indicators
        df.ta.ema(length=self.params.ema_short, append=True, col_names=(f'EMA_{self.params.ema_short}',))
        df.ta.ema(length=self.params.ema_long, append=True, col_names=(f'EMA_{self.params.ema_long}',))
        df.ta.vwap(append=True, col_names=('VWAP',))
        df.ta.supertrend(period=self.params.supertrend_period, multiplier=self.params.supertrend_multiplier,
                         append=True, col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        df.ta.atr(length=self.params.atr_period, append=True, col_names=(f'ATR_{self.params.atr_period}',))
        
        # High-profit scalping indicators
        df.ta.rsi(length=7, append=True, col_names=('RSI_7',))  # Fast RSI for momentum
        df.ta.bbands(length=20, std=2, append=True, col_names=('BB_L', 'BB_M', 'BB_U', 'BB_W', 'BB_P'))
        df.ta.stoch(k=5, d=3, append=True, col_names=('STOCH_K', 'STOCH_D'))  # Fast stochastic
        
        # Volume indicators for confirmation
        df.ta.ad(append=True, col_names=('AD',))  # Accumulation/Distribution
        df['volume_sma'] = df['volume'].rolling(20).mean() if 'volume' in df.columns else 0
        
        # Price action patterns
        df['price_momentum'] = (df['close'] - df['close'].shift(3)) / df['close'].shift(3) * 100
        df['volatility_ratio'] = df[f'ATR_{self.params.atr_period}'] / df['close'] * 100
        
        return df

    async def check_entry_conditions(self, symbol: str):
        """Advanced scalping entry with multiple confirmations for higher profits."""
        try:
            df = self.candle_history.get(symbol)
            if df is None or df.empty or len(df) < 30:
                return

            df = self.calculate_indicators(df.copy())
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            price = latest['close']
            atr = latest[f'ATR_{self.params.atr_period}']

            # Skip if indicators not ready
            if pd.isna([latest['RSI_7'], latest['STOCH_K'], latest['BB_L']]).any():
                return

            # Market condition filters
            volatility = latest['volatility_ratio']
            momentum = latest['price_momentum']
            volume_surge = latest.get('volume', 0) > latest.get('volume_sma', 1) * 1.5
            
            # High-probability BUY conditions
            buy_conditions = [
                latest[f'EMA_{self.params.ema_short}'] > latest[f'EMA_{self.params.ema_long}'],  # Trend
                price > latest['VWAP'],  # Above VWAP
                latest['SUPERTd'] == 1,  # SuperTrend bullish
                latest['RSI_7'] > 30 and latest['RSI_7'] < 70,  # RSI not extreme
                latest['STOCH_K'] > latest['STOCH_D'],  # Stoch momentum
                price > latest['BB_L'] and price < latest['BB_U'],  # Within Bollinger Bands
                momentum > 0.1,  # Positive momentum
                volatility > 0.3 and volatility < 2.0,  # Optimal volatility
                volume_surge  # Volume confirmation
            ]
            
            # High-probability SELL conditions
            sell_conditions = [
                latest[f'EMA_{self.params.ema_short}'] < latest[f'EMA_{self.params.ema_long}'],
                price < latest['VWAP'],
                latest['SUPERTd'] == -1,
                latest['RSI_7'] > 30 and latest['RSI_7'] < 70,
                latest['STOCH_K'] < latest['STOCH_D'],
                price > latest['BB_L'] and price < latest['BB_U'],
                momentum < -0.1,
                volatility > 0.3 and volatility < 2.0,
                volume_surge
            ]

            # Enhanced signal generation with dynamic targets
            if sum(buy_conditions) >= 7:  # Require 7/9 confirmations
                tp_multiplier = 1.2 if sum(buy_conditions) == 9 else 0.8  # Higher TP for perfect signals
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'BUY', 'entry': price,
                    'sl': price - (0.8 * atr), 'tp': price + (tp_multiplier * atr), 'atr_at_entry': atr,
                    'reason': f'SCALP_BUY_CONF_{sum(buy_conditions)}', 'confidence': sum(buy_conditions)
                }
                logger.info(f"HIGH-PROB BUY: {signal}")
                await self.order_manager.handle_signal(signal)
                
            elif sum(sell_conditions) >= 7:
                tp_multiplier = 1.2 if sum(sell_conditions) == 9 else 0.8
                signal = {
                    'symbol': symbol, 'ts': datetime.utcnow(), 'side': 'SELL', 'entry': price,
                    'sl': price + (0.8 * atr), 'tp': price - (tp_multiplier * atr), 'atr_at_entry': atr,
                    'reason': f'SCALP_SELL_CONF_{sum(sell_conditions)}', 'confidence': sum(sell_conditions)
                }
                logger.info(f"HIGH-PROB SELL: {signal}")
                await self.order_manager.handle_signal(signal)
                
        except Exception as e:
            logger.error(f"Error in enhanced entry logic for {symbol}: {e}", exc_info=True)

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
        """Advanced exit management for maximum profit extraction."""
        open_positions = self.order_manager.get_open_positions()
        if not open_positions:
            return
            
        for position in open_positions:
            symbol = position['symbol']
            live_price = await market_data_manager.get_latest_price(symbol)
            if not live_price:
                continue

            side = position['side']
            entry_price = position['entry_price']
            sl = position['sl']
            tp = position['tp']
            entry_time = position['entry_time']
            atr = position.get('atr_at_entry', 0)
            confidence = position.get('confidence', 7)
            
            # Calculate current P&L and time in trade
            pnl_pct = ((live_price - entry_price) / entry_price * 100) if side == 'BUY' else ((entry_price - live_price) / entry_price * 100)
            time_in_trade = (datetime.utcnow() - entry_time).total_seconds() / 60
            
            # Dynamic exit conditions based on performance
            is_sl_hit = (side == 'BUY' and live_price <= sl) or (side == 'SELL' and live_price >= sl)
            is_tp_hit = (side == 'BUY' and live_price >= tp) or (side == 'SELL' and live_price <= tp)
            
            # Profit-maximizing exit logic
            if is_sl_hit:
                await self.order_manager.close_position(position, "STOP_LOSS")
            elif is_tp_hit:
                # Partial profit taking for high-confidence trades
                if confidence >= 8 and pnl_pct > 0.8:
                    # Let 50% run for bigger profits, close 50%
                    logger.info(f"Partial TP hit for high-confidence {symbol}. P&L: {pnl_pct:.2f}%")
                await self.order_manager.close_position(position, "TAKE_PROFIT")
            elif pnl_pct > 1.5:  # Exceptional profit - trail tightly
                trail_amount = 0.3 * atr
                if side == 'BUY':
                    new_sl = max(sl, live_price - trail_amount)
                    if new_sl > sl:
                        self.order_manager.update_position_sl(position, new_sl)
                        logger.info(f"Tight trailing SL for {symbol}: {new_sl:.2f}")
                else:
                    new_sl = min(sl, live_price + trail_amount)
                    if new_sl < sl:
                        self.order_manager.update_position_sl(position, new_sl)
            elif pnl_pct > 0.5:  # Good profit - standard trailing
                trail_amount = 0.6 * atr
                if side == 'BUY':
                    new_sl = max(sl, live_price - trail_amount)
                    if new_sl > sl:
                        self.order_manager.update_position_sl(position, new_sl)
                else:
                    new_sl = min(sl, live_price + trail_amount)
                    if new_sl < sl:
                        self.order_manager.update_position_sl(position, new_sl)
            elif time_in_trade > 3 and pnl_pct < -0.2:  # Quick exit for losing trades
                logger.info(f"Quick exit for underperforming {symbol}. P&L: {pnl_pct:.2f}%")
                await self.order_manager.close_position(position, "QUICK_EXIT")
            elif time_in_trade > 8:  # Time-based exit for scalping
                logger.info(f"Time exit for {symbol} after {time_in_trade:.1f}min. P&L: {pnl_pct:.2f}%")
                await self.order_manager.close_position(position, "TIME_EXIT")

    async def run(self):
        """The main loop of the trading strategy."""
        await self.warm_up()
        while True:
            await asyncio.sleep(sleep_time)
            if not self.is_running or self.risk_manager.is_trading_stopped:
                continue

            now_time = datetime.now().time()
            start_time = time.fromisoformat(settings.trading.hours['start'])
            end_time = time.fromisoformat(settings.trading.hours['end'])

            # Optimize for high-volume sessions
            is_opening_session = time(9, 15) <= now_time <= time(10, 30)
            is_closing_session = time(14, 30) <= now_time <= time(15, 15)
            is_lunch_time = time(12, 0) <= now_time <= time(13, 0)
            
            if not (start_time <= now_time < end_time):
                if self.active_trades:
                    logger.info("Outside trading hours. Closing all open positions...")
                await asyncio.sleep(30)
                continue
                
            # Skip low-volume lunch period for scalping
            if is_lunch_time:
                await asyncio.sleep(10)
                continue
                
            # Faster execution during high-volume sessions
            sleep_time = 0.5 if (is_opening_session or is_closing_session) else 2

            try:
                await self.update_and_check_candles()
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)
