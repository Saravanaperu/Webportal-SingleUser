import asyncio
import pandas as pd
import pandas_ta as ta
from datetime import datetime, time
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.order_manager import OrderManager
from app.services.risk_manager import RiskManager
from app.services.angel_one import AngelOneConnector
from app.services.instrument_manager import InstrumentManager
from app.services import options_helper
from app.db.session import database
from app.models.trading import Position
from sqlalchemy import select

class TradingStrategy:
    """
    Implements the core scalping strategy, generating signals based on technical indicators.
    """
    def __init__(self,
                 order_manager: OrderManager,
                 risk_manager: RiskManager,
                 connector: AngelOneConnector,
                 instrument_manager: InstrumentManager):
        logger.info("Initializing Trading Strategy for Options...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.connector = connector
        self.instrument_manager = instrument_manager
        self.ws_client = self.connector.get_ws_client()
        self.order_ws_client = self.connector.get_order_ws_client()

        self.underlyings_to_trade = settings.options_strategy.underlyings
        self.is_running = False

        # Data structures for live data
        self.token_to_symbol_map = {}
        self.live_ticks = {} # Will be populated dynamically
        self.candles = {} # Will be populated dynamically

    def start(self):
        """Starts the strategy loop."""
        self.is_running = True
        logger.info("Trading Strategy started.")

    def stop(self):
        """Stops the strategy loop."""
        self.is_running = False
        logger.info("Trading Strategy stopped.")

    async def _initialize_data_stream(self):
        """
        Initializes the WebSocket connection and subscribes to the underlying indices.
        """
        logger.info("Initializing data stream for underlying indices...")
        if not self.ws_client:
            logger.error("WebSocket client is not available. Cannot initialize data stream.")
            return

        # 1. Get tokens for underlying indices
        subscription_tokens = []
        for underlying in self.underlyings_to_trade:
            config = settings.underlying_instruments.get(underlying)
            if config and config.token:
                exchange_type = 1 if config.exchange == "NSE" else 2 # 1 for NSE, 2 for BSE. Simplified.
                subscription_tokens.append({"exchangeType": exchange_type, "tokens": [config.token]})
                self.token_to_symbol_map[config.token] = underlying
                self.live_ticks[underlying] = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
                self.candles[underlying] = pd.DataFrame()
            else:
                logger.error(f"Could not find token for underlying {underlying} in config. It will not be traded.")

        if not subscription_tokens:
            logger.error("No valid tokens found for underlying subscriptions. Stopping strategy.")
            self.stop()
            return

        # 2. Connect and subscribe
        try:
            await asyncio.gather(self.ws_client.connect(), self.order_ws_client.connect())
            await self.ws_client.subscribe_to_instruments(subscription_tokens)
            logger.info(f"Successfully subscribed to underlying indices: {subscription_tokens}")
        except Exception as e:
            logger.critical(f"Failed to connect or subscribe to WebSocket: {e}", exc_info=True)
            self.stop()

    async def _process_order_updates(self):
        """
        Listens for incoming order updates from the WebSocket and processes them.
        """
        logger.info("Starting order update processing loop...")
        try:
            async for message in self.order_ws_client.receive_data():
                await self.order_manager.handle_order_update(message)
        except Exception as e:
            logger.error(f"Error in order update processing loop: {e}", exc_info=True)
            self.stop()
        logger.warning("Order update processing loop has stopped.")

    async def _process_market_data(self):
        """
        Listens for incoming ticks from the WebSocket and processes them.
        """
        logger.info("Starting market data processing loop...")
        try:
            async for message in self.ws_client.receive_data():
                # This is where you would parse the message and update candles
                # For now, we just log it. The aggregation logic will be in the next step.
                await self._aggregate_tick_to_candle(message)
        except Exception as e:
            logger.error(f"Error in market data processing loop: {e}", exc_info=True)
            self.stop()
        logger.warning("Market data processing loop has stopped.")

    async def _aggregate_tick_to_candle(self, tick: dict):
        """
        Aggregates a single tick into a 1-minute candle using pandas resampling.
        """
        try:
            token = tick.get('token')
            price = tick.get('last_traded_price')
            volume = tick.get('last_traded_quantity')
            timestamp = pd.to_datetime(tick.get('exchange_timestamp'), unit='s')

            if not all([token, price, volume, timestamp]):
                logger.debug(f"Skipping incomplete tick: {tick}")
                return

            symbol = self.token_to_symbol_map.get(str(token))
            if not symbol:
                logger.debug(f"Received tick for unknown token {token}. Skipping.")
                return

            # Append the new tick to the temporary DataFrame
            ticks_df = self.live_ticks[symbol]
            new_tick = pd.DataFrame([{'timestamp': timestamp, 'price': price, 'volume': volume}])
            self.live_ticks[symbol] = pd.concat([ticks_df, new_tick], ignore_index=True)

            # Resample the ticks into 1-minute candles
            resampled_df = self.live_ticks[symbol].set_index('timestamp')['price'].resample('1Min').ohlc()
            volume_df = self.live_ticks[symbol].set_index('timestamp')['volume'].resample('1Min').sum()
            resampled_df['volume'] = volume_df

            # Keep only the last 100 candles to avoid memory issues
            self.candles[symbol] = resampled_df.tail(100)

            # Clean up old ticks to save memory
            cutoff_time = timestamp - pd.Timedelta(minutes=105)
            self.live_ticks[symbol] = self.live_ticks[symbol][self.live_ticks[symbol]['timestamp'] > cutoff_time]

            logger.debug(f"Updated candles for {symbol} with tick at {timestamp}. Total candles: {len(self.candles[symbol])}")

        except Exception as e:
            logger.error(f"Error aggregating tick: {tick}. Error: {e}", exc_info=True)

    async def get_candle_data(self, symbol: str) -> pd.DataFrame:
        """
        Returns the latest candle data for a given symbol from the in-memory store.
        """
        if symbol in self.candles:
            return self.candles[symbol]
        else:
            logger.warning(f"No candle data available for {symbol}.")
            return pd.DataFrame()

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

    async def check_underlying_conditions(self, underlying: str):
        """
        Fetches data for the underlying index, calculates indicators, and
        generates a bullish or bearish signal.
        """
        try:
            df = await self.get_candle_data(underlying)
            if df.empty or len(df) < settings.strategy.ema_long:
                logger.debug(f"Not enough candle data for {underlying} to generate signals.")
                return

            df = self.calculate_indicators(df)
            latest = df.iloc[-1]

            # Ensure indicators are not NaN
            required_cols = [f'EMA_{settings.strategy.ema_short}', f'EMA_{settings.strategy.ema_long}', 'VWAP', 'SUPERTd']
            if latest[required_cols].hasnans:
                logger.debug(f"Indicators not ready for {underlying}. Skipping.")
                return

            # Entry Conditions
            is_bullish = (latest[f'EMA_{settings.strategy.ema_short}'] > latest[f'EMA_{settings.strategy.ema_long}'] and
                          latest['close'] > latest['VWAP'] and
                          latest['SUPERTd'] == 1)

            is_bearish = (latest[f'EMA_{settings.strategy.ema_short}'] < latest[f'EMA_{settings.strategy.ema_long}'] and
                          latest['close'] < latest['VWAP'] and
                          latest['SUPERTd'] == -1)

            if is_bullish:
                await self._execute_option_trade(underlying, 'bullish', latest)
            elif is_bearish:
                await self._execute_option_trade(underlying, 'bearish', latest)

        except Exception as e:
            logger.error(f"Error checking conditions for {underlying}: {e}", exc_info=True)

    async def _execute_option_trade(self, underlying: str, signal_type: str, latest_candle: pd.Series):
        """
        Selects the appropriate option contract based on the signal and places the trade.
        """
        logger.info(f"Executing option trade for {underlying} based on {signal_type} signal.")

        # 1. Determine option type and find the contract
        option_type = "CE" if signal_type == 'bullish' else "PE"
        spot_price = latest_candle['close']

        config = settings.underlying_instruments.get(underlying)
        atm_strike = options_helper.get_atm_strike(spot_price, config.strike_interval)
        expiry = options_helper.get_current_weekly_expiry()

        option_symbol = options_helper.generate_option_symbol(underlying, expiry, atm_strike, option_type)

        # 2. Check if we are already in a trade for this underlying
        query = select(Position).where(Position.symbol.like(f"{underlying}%"), Position.status == "OPEN")
        existing_position = await database.fetch_one(query)
        if existing_position:
            logger.warning(f"Already have an open position for {underlying}. Skipping new trade.")
            return

        # 3. Subscribe to the option's tick data
        option_token = self.instrument_manager.get_token(option_symbol, "NFO") # Assuming NFO for options
        if not option_token:
            logger.error(f"Could not find token for option {option_symbol}. Cannot place trade.")
            return

        await self.ws_client.subscribe_to_tokens([{"exchangeType": 2, "tokens": [option_token]}]) # 2 for NFO
        self.token_to_symbol_map[option_token] = option_symbol
        self.live_ticks[option_symbol] = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
        self.candles[option_symbol] = pd.DataFrame()
        logger.info(f"Subscribed to tick data for {option_symbol}")

        # 4. Get the live price of the option to calculate SL/TP
        # This part is still simplified. We need to wait for the first tick to get the premium.
        # For now, we'll continue with the placeholder premium.
        assumed_premium = 100 # Placeholder
        sl_price = assumed_premium * 0.5 # 50% stop-loss
        tp_price = assumed_premium * 2.0 # 100% take-profit

        # 5. Create signal for OrderManager
        trade_signal = {
            'symbol': option_symbol,
            'ts': datetime.utcnow(),
            'side': 'BUY', # We are buying options
            'entry': assumed_premium, # This would be the live premium
            'sl': sl_price,
            'tp': tp_price,
            'reason': f'{underlying}_{signal_type.upper()}'
        }

        logger.info(f"Generated trade signal for option: {trade_signal}")
        await self.order_manager.handle_signal(trade_signal)

    async def manage_active_trades(self):
        """
        Manages exits for active trades based on SL/TP, trailing SL, and time-based exits.
        """
        query = select(Position).where(Position.status == "OPEN")
        open_positions = await database.fetch_all(query)

        now_time = datetime.now().time()
        eod_exit_time = time.fromisoformat(settings.trading.hours['end_of_day_exit'])

        for pos in open_positions:
            # 1. Time-based exit
            if now_time >= eod_exit_time:
                logger.info(f"End-of-day exit for {pos.symbol}. Closing position.")
                await self.order_manager.create_exit_order(pos, "EOD_EXIT")
                continue

            ticks_df = self.live_ticks.get(pos.symbol)
            if ticks_df is None or ticks_df.empty:
                logger.debug(f"No live ticks available yet for position {pos.symbol}. Skipping.")
                continue

            current_price = ticks_df.iloc[-1]['price']

            # 2. Trailing Stop-Loss Logic
            trailing_sl = pos.trailing_sl
            if settings.strategy.trailing_sl.is_enabled:
                if pos.side == 'BUY':
                    new_highest = max(pos.highest_price_seen or pos.avg_price, current_price)
                    new_tsl = new_highest * (1 - settings.strategy.trailing_sl.percentage / 100)
                    if new_tsl > (trailing_sl or pos.sl):
                        trailing_sl = new_tsl
                        # Update position with new TSL and highest price
                        update_q = Position.__table__.update().where(Position.id == pos.id).values(trailing_sl=trailing_sl, highest_price_seen=new_highest)
                        await database.execute(update_q)
                elif pos.side == 'SELL':
                    new_lowest = min(pos.highest_price_seen or pos.avg_price, current_price) # Note: field is highest_price_seen, but used for lowest here
                    new_tsl = new_lowest * (1 + settings.strategy.trailing_sl.percentage / 100)
                    if new_tsl < (trailing_sl or pos.sl):
                        trailing_sl = new_tsl
                        update_q = Position.__table__.update().where(Position.id == pos.id).values(trailing_sl=trailing_sl, highest_price_seen=new_lowest)
                        await database.execute(update_q)

            # 3. Check for SL/TP Exits
            stop_loss_price = trailing_sl or pos.sl
            if pos.side == 'BUY':
                if current_price <= stop_loss_price:
                    logger.info(f"Stop-loss hit for BUY position on {pos.symbol}. Exiting.")
                    await self.order_manager.create_exit_order(pos, "STOPLOSS_HIT")
                elif current_price >= pos.tp:
                    logger.info(f"Take-profit hit for BUY position on {pos.symbol}. Exiting.")
                    await self.order_manager.create_exit_order(pos, "TAKEPROFIT_HIT")
            elif pos.side == 'SELL':
                if current_price >= stop_loss_price:
                    logger.info(f"Stop-loss hit for SELL position on {pos.symbol}. Exiting.")
                    await self.order_manager.create_exit_order(pos, "STOPLOSS_HIT")
                elif current_price <= pos.tp:
                    logger.info(f"Take-profit hit for SELL position on {pos.symbol}. Exiting.")
                    await self.order_manager.create_exit_order(pos, "TAKEPROFIT_HIT")

    async def run(self):
        """The main loop of the trading strategy."""
        await self._initialize_data_stream()

        if self.is_running:
            # Start the market data and order update processing in the background
            asyncio.create_task(self._process_market_data())
            asyncio.create_task(self._process_order_updates())

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
                entry_tasks = [self.check_underlying_conditions(underlying) for underlying in self.underlyings_to_trade]
                await asyncio.gather(*entry_tasks)
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)

            # Wait for the start of the next minute
            current_time = datetime.now()
            sleep_seconds = 60 - current_time.second
            await asyncio.sleep(sleep_seconds)
