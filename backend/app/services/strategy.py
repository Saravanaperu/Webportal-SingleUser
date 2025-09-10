import asyncio
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time, timedelta
import numpy as np
from typing import Dict, List, Optional

from ..core.config import settings, StrategyConfig
from ..core.logging import logger
from .order_manager import OrderManager
from .risk_manager import RiskManager
from .market_data_manager import market_data_manager
from .instrument_manager import instrument_manager
from .options_manager import get_options_manager
from ..db.session import database
from ..models.trading import Candle

class OptionsScalpingStrategy:
    """
    Advanced options scalping strategy optimized for Indian markets.
    Focuses on high-probability setups with proper Greeks management.
    """
    def __init__(self, order_manager: OrderManager, risk_manager: RiskManager, connector):
        logger.info("Initializing Options Scalping Strategy...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.connector = connector
        self.params = settings.strategy
        self.trade_indices = self.params.trade_indices
        self.is_running = False
        self.active_trades = {}
        self.index_candle_history = {index: pd.DataFrame() for index in self.trade_indices}
        self.options_manager = get_options_manager(connector.rest_client, instrument_manager)
        self.last_signal_time = {}
        self.signal_cooldown = 30  # seconds between signals for same index

    def update_parameters(self, new_params: StrategyConfig):
        """
        Updates the strategy parameters safely.
        """
        logger.info(f"Updating options scalping parameters: {new_params.dict()}")
        self.params = new_params
        self.trade_indices = self.params.trade_indices
        logger.info("Options scalping parameters updated.")

    async def warm_up(self):
        """
        Loads historical data for underlying indices to warm up indicators.
        """
        logger.info("Warming up options scalping indicators...")
        
        # Map indices to their spot symbols for data
        index_symbols = {
            'BANKNIFTY': 'BANKNIFTY-INDEX',
            'NIFTY': 'NIFTY 50', 
            'FINNIFTY': 'FINNIFTY'
        }
        
        for index in self.trade_indices:
            try:
                symbol = index_symbols.get(index, index)
                query = Candle.__table__.select().where(Candle.symbol == symbol).order_by(Candle.ts.desc()).limit(100)
                results = await database.fetch_all(query)
                
                if results:
                    results.reverse()
                    df = pd.DataFrame(results)
                    df['timestamp'] = pd.to_datetime(df['ts'])
                    df.set_index('timestamp', inplace=True)
                    self.index_candle_history[index] = df
                    logger.info(f"Warmed up {len(df)} candles for {index} index")
                else:
                    logger.warning(f"No historical data for {index}. Building from live data.")
                    
            except Exception as e:
                logger.error(f"Error warming up {index}: {e}", exc_info=True)
                
        logger.info("Options scalping warm-up complete.")

    def start(self):
        self.is_running = True
        logger.info("Trading Strategy started.")

    def stop(self):
        self.is_running = False
        logger.info("Trading Strategy stopped.")

    def calculate_scalping_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate optimized indicators for options scalping."""
        if len(df) < 30:
            return df
            
        # Fast trend indicators
        df.ta.ema(length=self.params.ema_short, append=True, col_names=(f'EMA_{self.params.ema_short}',))
        df.ta.ema(length=self.params.ema_long, append=True, col_names=(f'EMA_{self.params.ema_long}',))
        df.ta.vwap(append=True, col_names=('VWAP',))
        
        # Momentum oscillators
        df.ta.rsi(length=self.params.rsi_period, append=True, col_names=('RSI_FAST',))
        df.ta.stoch(k=self.params.stoch_k, d=self.params.stoch_d, append=True, col_names=('STOCH_K', 'STOCH_D'))
        
        # Volatility and trend
        df.ta.supertrend(period=self.params.supertrend_period, multiplier=self.params.supertrend_multiplier,
                         append=True, col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        df.ta.atr(length=self.params.atr_period, append=True, col_names=(f'ATR_{self.params.atr_period}',))
        df.ta.bbands(length=self.params.bb_period, std=2, append=True, col_names=('BB_L', 'BB_M', 'BB_U', 'BB_W', 'BB_P'))
        
        # Options-specific indicators
        df['price_velocity'] = df['close'].diff().rolling(3).mean()  # Price acceleration
        df['volatility_spike'] = df[f'ATR_{self.params.atr_period}'].rolling(5).std()
        df['momentum_strength'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
        
        # Volume analysis
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(10).mean()
            df['volume_surge'] = df['volume'] / df['volume_ma']
        else:
            df['volume_surge'] = 1.0
            
        # Market structure
        df['higher_high'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_low'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        
        return df

    async def analyze_options_entry(self, index: str) -> Optional[Dict]:
        """Analyze underlying index for options entry opportunities."""
        try:
            # Check signal cooldown
            now = datetime.utcnow()
            if index in self.last_signal_time:
                time_diff = (now - self.last_signal_time[index]).total_seconds()
                if time_diff < self.signal_cooldown:
                    return None
            
            df = self.index_candle_history.get(index)
            if df is None or df.empty or len(df) < 30:
                return None

            df = self.calculate_scalping_indicators(df.copy())
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Skip if indicators not ready
            required_indicators = ['RSI_FAST', 'STOCH_K', 'BB_L', 'SUPERTd']
            if any(pd.isna(latest[ind]) for ind in required_indicators):
                return None

            price = latest['close']
            
            # Market condition analysis
            momentum = latest['momentum_strength']
            volatility_spike = latest.get('volatility_spike', 0)
            volume_surge = latest.get('volume_surge', 1)
            price_velocity = latest.get('price_velocity', 0)
            
            # Bullish options setup (for CE buying)
            bullish_signals = [
                latest[f'EMA_{self.params.ema_short}'] > latest[f'EMA_{self.params.ema_long}'],  # Trend up
                price > latest['VWAP'],  # Above VWAP
                latest['SUPERTd'] == 1,  # SuperTrend bullish
                latest['RSI_FAST'] > 40 and latest['RSI_FAST'] < 75,  # RSI in momentum zone
                latest['STOCH_K'] > latest['STOCH_D'] and latest['STOCH_K'] > 20,  # Stoch momentum
                price > latest['BB_M'],  # Above BB middle
                momentum > 0.15,  # Strong positive momentum
                price_velocity > 0,  # Positive velocity
                volume_surge > self.params.volume_surge_threshold,  # Volume confirmation
                latest['higher_high']  # Market structure
            ]
            
            # Bearish options setup (for PE buying)
            bearish_signals = [
                latest[f'EMA_{self.params.ema_short}'] < latest[f'EMA_{self.params.ema_long}'],  # Trend down
                price < latest['VWAP'],  # Below VWAP
                latest['SUPERTd'] == -1,  # SuperTrend bearish
                latest['RSI_FAST'] < 60 and latest['RSI_FAST'] > 25,  # RSI in momentum zone
                latest['STOCH_K'] < latest['STOCH_D'] and latest['STOCH_K'] < 80,  # Stoch momentum
                price < latest['BB_M'],  # Below BB middle
                momentum < -0.15,  # Strong negative momentum
                price_velocity < 0,  # Negative velocity
                volume_surge > self.params.volume_surge_threshold,  # Volume confirmation
                latest['lower_low']  # Market structure
            ]
            
            # Determine signal direction and strength
            bullish_score = sum(bullish_signals)
            bearish_score = sum(bearish_signals)
            
            if bullish_score >= self.params.min_confirmations:
                direction = 'BULLISH'
                confidence = bullish_score
            elif bearish_score >= self.params.min_confirmations:
                direction = 'BEARISH'
                confidence = bearish_score
            else:
                return None
            
            # Get best options for the signal
            best_options = await self.options_manager.get_best_strikes_for_scalping(
                index, 'BUY' if direction == 'BULLISH' else 'SELL'
            )
            
            if not best_options:
                logger.warning(f"No suitable options found for {index} {direction} signal")
                return None
            
            # Select the best option
            selected_option = best_options[0]  # Highest scalping score
            
            self.last_signal_time[index] = now
            
            return {
                'index': index,
                'direction': direction,
                'confidence': confidence,
                'option': selected_option,
                'underlying_price': price,
                'momentum': momentum,
                'volatility_spike': volatility_spike,
                'timestamp': now
            }
            
        except Exception as e:
            logger.error(f"Error analyzing options entry for {index}: {e}", exc_info=True)
            return None

    async def scan_for_options_signals(self):
        """Scan underlying indices for options trading opportunities."""
        for index in self.trade_indices:
            try:
                # Update index candle data
                index_symbols = {
                    'BANKNIFTY': 'BANKNIFTY-INDEX',
                    'NIFTY': 'NIFTY 50',
                    'FINNIFTY': 'FINNIFTY'
                }
                
                symbol = index_symbols.get(index, index)
                new_candle_df = await market_data_manager.get_1m_candle(symbol)
                
                if new_candle_df is not None:
                    # Update candle history
                    self.index_candle_history[index] = pd.concat([
                        self.index_candle_history[index], new_candle_df
                    ]).tail(100)
                    
                    # Analyze for options entry
                    signal = await self.analyze_options_entry(index)
                    if signal:
                        await self.execute_options_signal(signal)
                        
            except Exception as e:
                logger.error(f"Error scanning {index} for options signals: {e}", exc_info=True)

    async def execute_options_signal(self, signal: Dict):
        """Execute options trade based on signal."""
        try:
            option = signal['option']
            symbol = option['symbol']
            
            # Check if we already have position in this option
            if symbol in [pos['symbol'] for pos in self.order_manager.get_open_positions()]:
                return
            
            # Create signal for order manager
            entry_price = option['ltp']
            
            # Calculate stop loss and take profit based on premium
            sl_pct = settings.risk.stop_loss_percent / 100
            tp_pct = settings.risk.take_profit_percent / 100
            
            trade_signal = {
                'symbol': symbol,
                'ts': signal['timestamp'],
                'side': 'BUY',  # Always buying options for scalping
                'entry': entry_price,
                'sl': entry_price * (1 - sl_pct),
                'tp': entry_price * (1 + tp_pct),
                'reason': f"OPTIONS_SCALP_{signal['direction']}_CONF_{signal['confidence']}",
                'confidence': signal['confidence'],
                'greeks': option['greeks'],
                'underlying_price': signal['underlying_price']
            }
            
            logger.info(f"Executing options signal: {trade_signal}")
            await self.order_manager.handle_signal(trade_signal)
            
        except Exception as e:
            logger.error(f"Error executing options signal: {e}", exc_info=True)
    
    async def manage_options_positions(self):
        """Advanced options position management with Greeks monitoring."""
        open_positions = self.order_manager.get_open_positions()
        if not open_positions:
            return
            
        for position in open_positions:
            try:
                symbol = position['symbol']
                
                # Get current option price
                option_data = await self.options_manager.get_option_data(symbol)
                if not option_data:
                    continue
                    
                live_price = float(option_data.get('ltp', 0))
                if live_price <= 0:
                    continue
                
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                confidence = position.get('confidence', 7)
                
                # Calculate P&L and time metrics
                pnl_pct = (live_price - entry_price) / entry_price * 100
                time_in_trade = (datetime.utcnow() - entry_time).total_seconds() / 60
                
                # Options-specific exit conditions
                should_exit = False
                exit_reason = ""
                
                # 1. Profit target hit
                if pnl_pct >= settings.risk.take_profit_percent:
                    should_exit = True
                    exit_reason = "PROFIT_TARGET"
                    
                # 2. Stop loss hit
                elif pnl_pct <= -settings.risk.stop_loss_percent:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                    
                # 3. Theta decay protection
                elif time_in_trade > settings.risk.theta_decay_exit_minutes:
                    if pnl_pct < 10:  # Exit if not profitable after theta decay time
                        should_exit = True
                        exit_reason = "THETA_DECAY"
                        
                # 4. Quick profit taking for high confidence trades
                elif confidence >= 9 and pnl_pct >= 25 and time_in_trade >= 2:
                    should_exit = True
                    exit_reason = "QUICK_PROFIT"
                    
                # 5. Trailing stop for profitable trades
                elif pnl_pct >= settings.risk.trailing_stop.activate_at_profit_percent:
                    trail_pct = settings.risk.trailing_stop.trail_by_percent / 100
                    new_sl = live_price * (1 - trail_pct)
                    
                    current_sl = position.get('sl', entry_price * 0.6)
                    if new_sl > current_sl:
                        self.order_manager.update_position_sl(position, new_sl)
                        logger.info(f"Updated trailing SL for {symbol}: {new_sl:.2f}")
                        
                # 6. Time-based exit for scalping
                elif time_in_trade > 10:  # Max 10 minutes for scalping
                    should_exit = True
                    exit_reason = "TIME_EXIT"
                    
                # 7. Market close protection
                elif self.is_near_market_close():
                    should_exit = True
                    exit_reason = "MARKET_CLOSE"
                
                if should_exit:
                    logger.info(f"Closing {symbol}: {exit_reason}, P&L: {pnl_pct:.2f}%, Time: {time_in_trade:.1f}min")
                    await self.order_manager.close_position(position, exit_reason)
                    
            except Exception as e:
                logger.error(f"Error managing position {position.get('symbol', 'unknown')}: {e}", exc_info=True)
    
    def is_near_market_close(self) -> bool:
        """Check if we're near market close time."""
        now = datetime.now().time()
        square_off_time = datetime.strptime(settings.trading.square_off_time, '%H:%M').time()
        return now >= square_off_time

    async def run(self):
        """Main options scalping strategy loop."""
        await self.warm_up()
        logger.info("Options scalping strategy started")
        
        while True:
            try:
                if not self.is_running or self.risk_manager.is_trading_stopped:
                    await asyncio.sleep(2)
                    continue

                now_time = datetime.now().time()
                start_time = time.fromisoformat(settings.trading.hours['start'])
                end_time = time.fromisoformat(settings.trading.hours['end'])

                # Check trading hours
                if not (start_time <= now_time < end_time):
                    # Close all positions outside trading hours
                    open_positions = self.order_manager.get_open_positions()
                    if open_positions:
                        logger.info("Outside trading hours. Closing all positions...")
                        for position in open_positions:
                            await self.order_manager.close_position(position, "MARKET_CLOSED")
                    await asyncio.sleep(30)
                    continue
                
                # Skip avoid sessions (lunch break)
                if self.options_manager.should_avoid_trading():
                    await asyncio.sleep(10)
                    continue
                
                # Determine scan frequency based on market session
                is_high_volume = self.options_manager.is_high_volume_session()
                scan_interval = 1 if is_high_volume else 3  # Faster scanning in high volume
                
                # Main strategy operations
                await self.scan_for_options_signals()
                await self.manage_options_positions()
                
                # Risk management check
                if not self.risk_manager.can_place_trade():
                    logger.warning("Risk limits reached. Pausing new trades.")
                    await asyncio.sleep(10)
                    continue
                
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in options scalping cycle: {e}", exc_info=True)
                await asyncio.sleep(5)

# Alias for backward compatibility
TradingStrategy = OptionsScalpingStrategy
