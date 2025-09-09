from datetime import datetime
from app.core.logging import logger
from app.services.risk_manager import RiskManager
from app.models.trading import Order, Trade, HistoricalTrade
from app.db.session import database
from .notifier import notifier

class OrderManager:
    """
    Manages the lifecycle of orders, from signal to execution, and tracks open positions.
    """
    def __init__(self, connector, risk_manager: RiskManager, instrument_manager, db=database):
        logger.info("Initializing Order Manager...")
        self.connector = connector
        self.risk_manager = risk_manager
        self.instrument_manager = instrument_manager
        self.db = db
        self.active_orders = {}  # Maps broker_order_id to our internal order.id
        self.open_positions = {} # Maps symbol to position details

    async def create_market_order(self, signal: dict, position_size: int):
        """Creates and places a market order based on a signal."""
        symbol = signal['symbol']
        exchange = "NSE"
        token = self.instrument_manager.get_token(symbol, exchange)

        order_to_create = {
            "signal_id": signal.get('id'), "symbol": symbol, "side": signal['side'],
            "qty": position_size, "status": "PENDING", "ts": datetime.utcnow(),
            "sl": signal.get('sl'), "tp": signal.get('tp'), "atr_at_entry": signal.get('atr_at_entry')
        }
        query = Order.__table__.insert().values(order_to_create)
        order_id = await self.db.execute(query)
        logger.info(f"Order {order_id} saved to DB with PENDING status.")

        if not token:
            logger.error(f"Could not find token for {symbol}. Order {order_id} failed.")
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED", reason="TOKEN_NOT_FOUND")
            await self.db.execute(update_query)
            return

        order_params = {
            "variety": "NORMAL", "tradingsymbol": symbol, "symboltoken": token,
            "transactiontype": signal['side'], "exchange": exchange, "ordertype": "MARKET",
            "producttype": "INTRADAY", "duration": "DAY", "quantity": str(position_size)
        }
        broker_response = await self.connector.place_order(order_params)

        if broker_response and broker_response.get('orderid'):
            broker_order_id = broker_response['orderid']
            self.active_orders[broker_order_id] = order_id
            update_query = Order.__table__.update().where(Order.id == order_id).values(broker_order_id=broker_order_id, status="SUBMITTED")
            await self.db.execute(update_query)
        else:
            reason = str(broker_response) if broker_response else "NO_RESPONSE"
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED", reason=reason)
            await self.db.execute(update_query)

    async def handle_signal(self, signal: dict):
        """Processes a trading signal to place an order."""
        if signal['symbol'] in self.open_positions:
            logger.warning(f"Already have an open position for {signal['symbol']}. Ignoring new signal.")
            return
        if not self.risk_manager.can_place_trade():
            return

        position_size = self.risk_manager.calculate_position_size(
            entry_price=signal['entry'],
            stop_loss_price=signal['sl'],
            atr=signal['atr_at_entry']
        )

        if position_size > 0:
            await self.create_market_order(signal, position_size)

    async def handle_order_update(self, update: dict):
        """Processes an order update from the broker, handling partial and full fills."""
        broker_order_id = update.get("orderid")
        status = update.get("status", "").upper()

        internal_order_id = self.active_orders.get(broker_order_id)
        if not internal_order_id:
            logger.warning(f"Received update for an unknown or inactive order: {broker_order_id}")
            return

        update_query = Order.__table__.update().where(Order.id == internal_order_id).values(status=status)
        await self.db.execute(update_query)

        is_fill = status in ["COMPLETE", "PARTIALLY FILLED"]
        if not is_fill:
            if status not in ["OPEN", "SUBMITTED"]: # If it's cancelled, rejected, etc.
                del self.active_orders[broker_order_id]
            return

        # --- Handle a fill (partial or complete) ---
        order_query = Order.__table__.select().where(Order.id == internal_order_id)
        order = await self.db.fetch_one(order_query)
        symbol = order.symbol

        # This update is for a closing order of an existing position
        if symbol in self.open_positions and self.open_positions[symbol]['side'] != order.side:
            position = self.open_positions[symbol]
            if status == "COMPLETE":
                exit_price = float(update.get("averageprice", 0))
                original_qty = position['qty']

                if position['side'] == 'BUY':
                    pnl = (exit_price - position['entry_price']) * original_qty
                else: # SELL
                    pnl = (position['entry_price'] - exit_price) * original_qty

                trade_log = {
                    "symbol": symbol, "side": position['side'], "qty": original_qty,
                    "entry_price": position['entry_price'], "exit_price": exit_price,
                    "pnl": pnl, "entry_time": position['entry_time'], "exit_time": datetime.utcnow()
                }
                insert_query = HistoricalTrade.__table__.insert().values(trade_log)
                await self.db.execute(insert_query)

                await self.risk_manager.record_trade(pnl=pnl)
                del self.open_positions[symbol]
                del self.active_orders[broker_order_id]

                pnl_icon = "🟢" if pnl >= 0 else "🔴"
                message = f"{pnl_icon} *Trade Closed*\nSymbol: {symbol}\nSide: {position['side']}\nQty: {original_qty}\nP&L: ${pnl:.2f}"
                await notifier.send_message(message)

            return

        # --- This update is for an entry order ---
        fill_qty = int(update.get("filledshares", 0))
        fill_price = float(update.get("averageprice", 0))

        trade_to_create = {"order_id": internal_order_id, "fill_price": fill_price, "qty": fill_qty, "ts": datetime.utcnow()}
        query = Trade.__table__.insert().values(trade_to_create)
        await self.db.execute(query)

        if symbol not in self.open_positions:
            self.open_positions[symbol] = {
                'symbol': symbol, 'side': order.side, 'qty': fill_qty,
                'entry_price': fill_price, 'sl': order.sl, 'tp': order.tp,
                'atr_at_entry': order.atr_at_entry, 'entry_time': datetime.utcnow(),
                'total_cost': fill_qty * fill_price
            }
            message = f"🔵 *New Trade Opened*\nSymbol: {symbol}\nSide: {order.side}\nQty: {fill_qty}\nPrice: ${fill_price:.2f}"
            await notifier.send_message(message)
        else:
            # Subsequent partial fill
            position = self.open_positions[symbol]
            new_total_cost = position['total_cost'] + (fill_qty * fill_price)
            new_total_qty = position['qty'] + fill_qty
            position['entry_price'] = new_total_cost / new_total_qty
            position['qty'] = new_total_qty
            position['total_cost'] = new_total_cost
            logger.info(f"Position for {symbol} updated with partial fill.")

        if status == "COMPLETE":
            del self.active_orders[broker_order_id]

    def get_open_positions(self) -> list[dict]:
        return list(self.open_positions.values())

    async def close_position(self, position: dict, reason: str):
        logger.info(f"Initiating close for {position['symbol']} due to {reason}.")
        closing_signal = {'symbol': position['symbol'], 'side': 'SELL' if position['side'] == 'BUY' else 'BUY', 'id': None}
        await self.create_market_order(closing_signal, position['qty'])

    def update_position_sl(self, position: dict, new_sl: float):
        if position['symbol'] in self.open_positions:
            self.open_positions[position['symbol']]['sl'] = new_sl
            logger.info(f"Updated SL for {position['symbol']} to {new_sl}.")
