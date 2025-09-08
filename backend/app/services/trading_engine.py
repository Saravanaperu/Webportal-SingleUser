import asyncio
import importlib
import pandas as pd
from datetime import datetime, time
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.order_manager import OrderManager
from app.services.risk_manager import RiskManager
from app.services.angel_one import AngelOneConnector
from app.services.instrument_manager import InstrumentManager
from app.services import instrument_helper as ins_helper
from app.db.session import database
from app.models.trading import Position, Signal
from sqlalchemy import select

class TradingEngine:
    """
    The main engine that runs the trading strategy, manages data, and executes trades.
    """
    def __init__(self,
                 order_manager: OrderManager,
                 risk_manager: RiskManager,
                 connector: AngelOneConnector,
                 instrument_manager: InstrumentManager):
        logger.info("Initializing Trading Engine...")
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
        self.live_ticks = {}
        self.candles = {}

        # Dynamically load the strategy
        self.strategy = self._load_strategy()

    def _load_strategy(self):
        """Dynamically loads the strategy class from the config."""
        try:
            strategy_name = settings.strategy.active_strategy
            strategy_params = settings.strategy.model_dump()
            logger.info(f"Loading strategy: {strategy_name} with params: {strategy_params}")

            module_name = f"app.services.strategies.{strategy_name.lower()}"
            module = importlib.import_module(module_name)
            StrategyClass = getattr(module, strategy_name)

            return StrategyClass(**strategy_params)
        except (ImportError, AttributeError) as e:
            logger.critical(f"Could not load strategy '{settings.strategy.active_strategy}'. Please check the class name and file location. Error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.critical(f"An unexpected error occurred while loading the strategy: {e}", exc_info=True)
            raise

    def start(self):
        """Starts the strategy loop."""
        self.is_running = True
        logger.info("Trading Engine started.")

    def stop(self):
        """Stops the strategy loop."""
        self.is_running = False
        logger.info("Trading Engine stopped.")

    async def _initialize_data_stream(self):
        """
        Initializes the WebSocket connection and subscribes to the underlying indices.
        """
        logger.info("Initializing data stream for underlying indices...")
        if not self.ws_client:
            logger.error("WebSocket client is not available. Cannot initialize data stream.")
            return

        subscription_tokens = []
        for underlying in self.underlyings_to_trade:
            config = settings.underlying_instruments.get(underlying)
            if config and config.token:
                exchange_type = 1 if config.exchange == "NSE" else 2
                subscription_tokens.append({"exchangeType": exchange_type, "tokens": [config.token]})
                self.token_to_symbol_map[config.token] = underlying
                self.live_ticks[underlying] = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
                self.candles[underlying] = pd.DataFrame()
            else:
                logger.error(f"Could not find token for underlying {underlying} in config. It will not be traded.")

        if not subscription_tokens:
            logger.error("No valid tokens found for underlying subscriptions. Stopping engine.")
            self.stop()
            return

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
                await self._aggregate_tick_to_candle(message)
        except Exception as e:
            logger.error(f"Error in market data processing loop: {e}", exc_info=True)
            self.stop()
        logger.warning("Market data processing loop has stopped.")

    async def _aggregate_tick_to_candle(self, tick: dict):
        """
        Aggregates a single tick into a 1-minute candle.
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

            ticks_df = self.live_ticks[symbol]
            new_tick = pd.DataFrame([{'timestamp': timestamp, 'price': price, 'volume': volume}])
            self.live_ticks[symbol] = pd.concat([ticks_df, new_tick], ignore_index=True)

            resampled_df = self.live_ticks[symbol].set_index('timestamp')['price'].resample('1Min').ohlc()
            volume_df = self.live_ticks[symbol].set_index('timestamp')['volume'].resample('1Min').sum()
            resampled_df['volume'] = volume_df

            # This logic will be moved to the strategy itself
            if hasattr(self.strategy, 'atr_period'):
                 df.ta.atr(length=settings.strategy.atr_period, append=True, col_names=(f'ATR_{settings.strategy.atr_period}',))

            self.candles[symbol] = resampled_df.tail(100)

            cutoff_time = timestamp - pd.Timedelta(minutes=105)
            self.live_ticks[symbol] = self.live_ticks[symbol][self.live_ticks[symbol]['timestamp'] > cutoff_time]

        except Exception as e:
            logger.error(f"Error aggregating tick: {tick}. Error: {e}", exc_info=True)

    async def get_candle_data(self, symbol: str) -> pd.DataFrame:
        """
        Returns the latest candle data for a given symbol.
        """
        return self.candles.get(symbol, pd.DataFrame())

    async def check_underlying_conditions(self, underlying: str):
        """
        Applies the loaded strategy to the underlying's data and executes trades based on signals.
        """
        try:
            df = await self.get_candle_data(underlying)
            if df.empty:
                logger.debug(f"No candle data for {underlying}.")
                return

            # 1. Calculate indicators using the strategy
            df_with_indicators = self.strategy.calculate_indicators(df.copy())

            # 2. Generate signal using the strategy
            signal = self.strategy.generate_signal(df_with_indicators)

            latest = df_with_indicators.iloc[-1]

            # 3. Act on the signal
            if signal == "BUY":
                signal_type = 'bullish'
                if settings.options_strategy.trade_calls:
                    await self._execute_option_trade(underlying, signal_type, latest)
                if settings.futures_strategy.enabled:
                    await self._execute_futures_trade(underlying, signal_type, latest)
            elif signal == "SELL":
                signal_type = 'bearish'
                if settings.options_strategy.trade_puts:
                    await self._execute_option_trade(underlying, signal_type, latest)
                if settings.futures_strategy.enabled:
                    await self._execute_futures_trade(underlying, signal_type, latest)

        except Exception as e:
            logger.error(f"Error checking conditions for {underlying}: {e}", exc_info=True)

    async def _execute_futures_trade(self, underlying: str, signal_type: str, latest_candle: pd.Series):
        """
        Selects the appropriate futures contract and places the trade.
        """
        logger.info(f"Executing futures trade for {underlying} based on {signal_type} signal.")

        futures_symbol = ins_helper.generate_futures_symbol(underlying, settings.futures_strategy.contract_month)

        query = select(Position).where(Position.symbol == futures_symbol, Position.status == "OPEN")
        if await database.fetch_one(query):
            logger.warning(f"Already have an open position for {futures_symbol}. Skipping new trade.")
            return

        futures_token = self.instrument_manager.get_token(futures_symbol, "NFO")
        if not futures_token:
            logger.error(f"Could not find token for futures contract {futures_symbol}.")
            return

        live_price = await self.connector.get_ltp("NFO", futures_symbol, futures_token)
        if not live_price:
            logger.error(f"Could not fetch live price for {futures_symbol}.")
            return

        atr_col = next((col for col in latest_candle.index if 'ATR' in col), None)
        if atr_col and pd.notna(latest_candle[atr_col]):
            atr = latest_candle[atr_col]
            sl_price = live_price - (atr * 1.5) if signal_type == 'bullish' else live_price + (atr * 1.5)
            tp_price = live_price + (atr * 2.0) if signal_type == 'bullish' else live_price - (atr * 2.0)
        else:
            # Fallback to percentage-based if ATR is not available
            sl_price = live_price * 0.99
            tp_price = live_price * 1.02


        trade_signal = {
            'symbol': futures_symbol, 'ts': datetime.utcnow(), 'side': 'BUY' if signal_type == 'bullish' else 'SELL',
            'entry': live_price, 'sl': sl_price, 'tp': tp_price, 'reason': f'{underlying}_FUT_{signal_type.upper()}'
        }

        query = Signal.__table__.insert().values(trade_signal)
        trade_signal['id'] = await database.execute(query)
        await self.order_manager.handle_signal(trade_signal)

    async def _execute_option_trade(self, underlying: str, signal_type: str, latest_candle: pd.Series):
        """
        Selects the appropriate option contract and places the trade.
        """
        logger.info(f"Executing option trade for {underlying} based on {signal_type} signal.")

        option_type = "CE" if signal_type == 'bullish' else "PE"
        spot_price = latest_candle['close']

        query = select(Position).where(Position.symbol.like(f"{underlying}%"), Position.status == "OPEN")
        if await database.fetch_one(query):
            logger.warning(f"Already have an open position for {underlying}. Skipping new trade.")
            return

        config = settings.underlying_instruments.get(underlying)
        expiry = ins_helper.get_current_weekly_expiry()

        strike_to_trade = None
        if settings.options_strategy.strike_selection_method == "DELTA":
            target_delta = settings.options_strategy.target_delta
            call_strike, put_strike = await ins_helper.get_strike_by_delta(underlying, expiry, target_delta, self.connector)
            strike_to_trade = call_strike if option_type == "CE" else put_strike
        else: # Default to ATM
            strike_to_trade = ins_helper.get_atm_strike(spot_price, config.strike_interval)

        if not strike_to_trade:
            logger.error(f"Could not determine strike to trade for {underlying}. Skipping.")
            return

        option_symbol = ins_helper.generate_option_symbol(underlying, expiry, strike_to_trade, option_type)
        option_token = self.instrument_manager.get_token(option_symbol, "NFO")
        if not option_token:
            logger.error(f"Could not find token for option {option_symbol}.")
            return

        await self.ws_client.subscribe_to_tokens([{"exchangeType": 2, "tokens": [option_token]}])
        self.token_to_symbol_map[option_token] = option_symbol
        self.live_ticks[option_symbol] = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
        self.candles[option_symbol] = pd.DataFrame()
        logger.info(f"Subscribed to tick data for {option_symbol}")

        live_premium = await self.connector.get_ltp("NFO", option_symbol, option_token)
        if not live_premium:
            logger.error(f"Could not fetch live premium for {option_symbol}.")
            return

        sl_price = live_premium * (1 - settings.options_strategy.sl_percentage / 100)
        tp_price = live_premium * (1 + settings.options_strategy.tp_percentage / 100)

        trade_signal = {
            'symbol': option_symbol, 'underlying': underlying, 'ts': datetime.utcnow(), 'side': 'BUY',
            'entry': live_premium, 'sl': sl_price, 'tp': tp_price, 'reason': f'{underlying}_{signal_type.upper()}'
        }

        query = Signal.__table__.insert().values(trade_signal)
        trade_signal['id'] = await database.execute(query)
        await self.order_manager.handle_signal(trade_signal)

    async def manage_active_trades(self):
        """
        Manages exits for active trades.
        """
        query = select(Position).where(Position.status == "OPEN")
        open_positions = await database.fetch_all(query)

        now_time = datetime.now().time()
        eod_exit_time = time.fromisoformat(settings.trading.hours['end_of_day_exit'])

        for pos in open_positions:
            if now_time >= eod_exit_time:
                logger.info(f"End-of-day exit for {pos.symbol}. Closing position.")
                await self.order_manager.create_exit_order(pos, "EOD_EXIT")
                continue

            ticks_df = self.live_ticks.get(pos.symbol)
            if ticks_df is None or ticks_df.empty:
                logger.debug(f"No live ticks for {pos.symbol}.")
                continue

            current_price = ticks_df.iloc[-1]['price']

            live_pnl = (current_price - pos.avg_price) * pos.qty if pos.side == 'BUY' else (pos.avg_price - current_price) * pos.qty
            update_pnl_q = Position.__table__.update().where(Position.id == pos.id).values(live_pnl=live_pnl)
            await database.execute(update_pnl_q)

            trailing_sl = pos.trailing_sl
            if settings.strategy.trailing_sl.is_enabled:
                # Trailing SL logic needs ATR from the underlying, not the option
                underlying_candles = await self.get_candle_data(pos.underlying)
                if not underlying_candles.empty:
                    # We need to recalculate indicators for the underlying to get latest ATR
                    underlying_candles = self.strategy.calculate_indicators(underlying_candles.copy())
                    atr_col = next((col for col in underlying_candles.columns if 'ATR' in col), None)

                    if atr_col and pd.notna(underlying_candles.iloc[-1][atr_col]):
                        atr = underlying_candles.iloc[-1][atr_col]
                        atr_trail = atr * settings.strategy.trailing_sl.atr_multiplier

                        # This trailing logic is for the underlying, not the option premium.
                        # A more sophisticated approach might be needed. For now, we trail the option price.
                        if pos.side == 'BUY':
                            new_highest = max(pos.highest_price_seen or pos.avg_price, current_price)
                            new_tsl = new_highest - atr_trail
                            if new_tsl > (trailing_sl or pos.sl):
                                trailing_sl = new_tsl
                                update_q = Position.__table__.update().where(Position.id == pos.id).values(trailing_sl=trailing_sl, highest_price_seen=new_highest)
                                await database.execute(update_q)

            stop_loss_price = trailing_sl or pos.sl
            if (pos.side == 'BUY' and current_price <= stop_loss_price) or \
               (pos.side == 'SELL' and current_price >= stop_loss_price):
                logger.info(f"Stop-loss hit for {pos.symbol}. Exiting.")
                await self.order_manager.create_exit_order(pos, "STOPLOSS_HIT")
            elif (pos.side == 'BUY' and current_price >= pos.tp) or \
                 (pos.side == 'SELL' and current_price <= pos.tp):
                logger.info(f"Take-profit hit for {pos.symbol}. Exiting.")
                await self.order_manager.create_exit_order(pos, "TAKEPROFIT_HIT")

    async def run(self):
        """The main loop of the trading engine."""
        await self._initialize_data_stream()

        if self.is_running:
            asyncio.create_task(self._process_market_data())
            asyncio.create_task(self._process_order_updates())

        while True:
            await asyncio.sleep(1)
            if not self.is_running or self.risk_manager.is_trading_stopped:
                continue

            now = datetime.now().time()
            start_time = time.fromisoformat(settings.trading.hours['start'])
            end_time = time.fromisoformat(settings.trading.hours['end'])

            if not (start_time <= now < end_time):
                await asyncio.sleep(30)
                continue

            logger.info("Running strategy cycle...")
            try:
                entry_tasks = [self.check_underlying_conditions(underlying) for underlying in self.underlyings_to_trade]
                await asyncio.gather(*entry_tasks)
                await self.manage_active_trades()
            except Exception as e:
                logger.error(f"Error in strategy cycle: {e}", exc_info=True)

            current_time = datetime.now()
            sleep_seconds = 60 - current_time.second
            await asyncio.sleep(sleep_seconds)
