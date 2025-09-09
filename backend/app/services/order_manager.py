from datetime import datetime
from app.core.logging import logger
from app.services.risk_manager import RiskManager
from app.db.session import database
from app.models.trading import Order, Trade

class OrderManager:
    """
    Manages the lifecycle of orders, from signal to execution, and tracks open positions.
    """
    def __init__(self, connector, risk_manager: RiskManager, instrument_manager):
        logger.info("Initializing Order Manager...")
        self.connector = connector
        self.risk_manager = risk_manager
        self.instrument_manager = instrument_manager
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
        order_id = await database.execute(query)
        logger.info(f"Order {order_id} saved to DB with PENDING status.")

        if not token:
            logger.error(f"Could not find token for {symbol}. Order {order_id} failed.")
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED", reason="TOKEN_NOT_FOUND")
            await database.execute(update_query)
            return

        order_params = {
            "variety": "NORMAL", "tradingsymbol": symbol, "symboltoken": token,
            "transactiontype": signal['side'], "exchange": exchange, "ordertype": "MARKET",
            "producttype": "INTRADAY", "duration": "DAY", "quantity": str(position_size)
        }
        logger.info(f"Placing market order: {order_params}")
        broker_response = await self.connector.place_order(order_params)

        if broker_response and broker_response.get('orderid'):
            broker_order_id = broker_response['orderid']
            self.active_orders[broker_order_id] = order_id
            update_query = Order.__table__.update().where(Order.id == order_id).values(
                broker_order_id=broker_order_id, status="SUBMITTED"
            )
            await database.execute(update_query)
            logger.info(f"Order {order_id} placed successfully with broker ID {broker_order_id}.")
        else:
            reason = str(broker_response) if broker_response else "NO_RESPONSE"
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED", reason=reason)
            await database.execute(update_query)
            logger.error(f"Failed to place order {order_id}. Response: {broker_response}")

    async def handle_signal(self, signal: dict):
        """Processes a trading signal to place an order."""
        logger.info(f"Order Manager received signal: {signal}")
        if signal['symbol'] in self.open_positions:
            logger.warning(f"Already have an open position for {signal['symbol']}. Ignoring new signal.")
            return
        if not self.risk_manager.can_place_trade():
            return
        position_size = self.risk_manager.calculate_position_size(signal['entry'], signal['sl'])
        if position_size <= 0:
            logger.warning(f"Position size is {position_size}. Skipping trade.")
            return
        await self.create_market_order(signal, position_size)

    async def handle_order_update(self, update: dict):
        """Processes an order update from the broker (via WebSocket)."""
        broker_order_id = update.get("orderid")
        status = update.get("status", "").upper()

        internal_order_id = self.active_orders.get(broker_order_id)
        if not internal_order_id:
            logger.warning(f"Received update for an unknown or inactive order: {broker_order_id}")
            return

        update_query = Order.__table__.update().where(Order.id == internal_order_id).values(status=status)
        await database.execute(update_query)
        logger.info(f"Order {internal_order_id} status updated to {status}.")

        if status == "COMPLETE":
            order_query = Order.__table__.select().where(Order.id == internal_order_id)
            order = await database.fetch_one(order_query)

            # Create a trade record
            trade_to_create = {
                "order_id": internal_order_id,
                "fill_price": float(update.get("averageprice")),
                "qty": int(update.get("filledshares")), "ts": datetime.utcnow()
            }
            query = Trade.__table__.insert().values(trade_to_create)
            await database.execute(query)
            logger.info(f"Trade created for order {internal_order_id}.")

            # If this was an entry order, create the position
            if order.symbol not in self.open_positions:
                self.open_positions[order.symbol] = {
                    'symbol': order.symbol, 'side': order.side, 'qty': order.qty,
                    'entry_price': float(update.get("averageprice")),
                    'sl': order.sl, 'tp': order.tp, 'atr_at_entry': order.atr_at_entry,
                    'entry_time': datetime.utcnow()
                }
                logger.info(f"New position opened for {order.symbol}: {self.open_positions[order.symbol]}")
            else: # This was a closing order
                del self.open_positions[order.symbol]
                logger.info(f"Position closed for {order.symbol}.")

            self.risk_manager.record_trade(pnl=0) # PNL calculation is complex, placeholder
            del self.active_orders[broker_order_id]

    def get_open_positions(self) -> list[dict]:
        """Returns a list of all open positions."""
        return list(self.open_positions.values())

    async def close_position(self, position: dict, reason: str):
        """Closes an open position by placing an opposing market order."""
        logger.info(f"Closing position for {position['symbol']} due to {reason}.")
        closing_signal = {
            'symbol': position['symbol'],
            'side': 'SELL' if position['side'] == 'BUY' else 'BUY',
            'id': None
        }
        await self.create_market_order(closing_signal, position['qty'])

    def update_position_sl(self, position: dict, new_sl: float):
        """Updates the stop-loss for an open position."""
        if position['symbol'] in self.open_positions:
            self.open_positions[position['symbol']]['sl'] = new_sl
            logger.info(f"Updated SL for {position['symbol']} to {new_sl}.")
