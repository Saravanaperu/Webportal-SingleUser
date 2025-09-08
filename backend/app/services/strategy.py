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

class TradingStrategy:
    """
    Implements the core scalping strategy, generating signals based on technical indicators.
    """
    def __init__(self,
                 order_manager: OrderManager,
                 risk_manager: RiskManager,
                 connector: AngelOneConnector,
                 instrument_manager: InstrumentManager):
        logger.info("Initializing Trading Strategy...")
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.connector = connector
        self.instrument_manager = instrument_manager
        self.ws_client = self.connector.get_ws_client()

        self.instruments_to_trade = settings.strategy.instruments
        self.is_running = False
        self.active_trades = {}

        # Data structures for live data
        self.token_to_symbol_map = {}
        self.live_ticks = {symbol: pd.DataFrame(columns=['timestamp', 'price', 'volume']) for symbol in self.instruments_to_trade}
        self.candles = {symbol: pd.DataFrame() for symbol in self.instruments_to_trade}

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
        Initializes the WebSocket connection and subscribes to instrument feeds.
        """
        logger.info("Initializing data stream...")
        if not self.ws_client:
            logger.error("WebSocket client is not available. Cannot initialize data stream.")
            return

        # 1. Get tokens for instruments
        subscription_tokens = []
        for symbol in self.instruments_to_trade:
            # Assuming NSE for now, should be configurable
            token = self.instrument_manager.get_token(symbol, "NSE")
            if token:
                # The format required by the smartapi-python library
                subscription_tokens.append({"exchangeType": 1, "tokens": [token]})
                self.token_to_symbol_map[token] = symbol
            else:
                logger.error(f"Could not find token for {symbol}. It will not be traded.")

        if not subscription_tokens:
            logger.error("No valid tokens found for subscription. Stopping strategy.")
            self.stop()
            return

        # 2. Connect and subscribe
        try:
            await self.ws_client.connect()
            await self.ws_client.subscribe_to_instruments(subscription_tokens)
            logger.info(f"Successfully subscribed to tokens: {subscription_tokens}")
        except Exception as e:
            logger.critical(f"Failed to connect or subscribe to WebSocket: {e}", exc_info=True)
            self.stop()

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
        await self._initialize_data_stream()

        if self.is_running:
            # Start the market data processing in the background
            asyncio.create_task(self._process_market_data())

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
                entry_tasks = [self.check_entry_conditions(symbol) for symbol in self.instruments_to_trade]
                await asyncio.gather(*entry_tasks)
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)

            # Wait for the start of the next minute
            current_time = datetime.now()
            sleep_seconds = 60 - current_time.second
            await asyncio.sleep(sleep_seconds)
