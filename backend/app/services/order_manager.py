from datetime import datetime
from app.core.logging import logger
from app.services.angel_one import AngelOneConnector
from app.services.risk_manager import RiskManager
from app.services.instrument_manager import InstrumentManager
from app.db.session import database
from app.models.trading import Order, Trade, Position, Signal
from sqlalchemy import select

class OrderManager:
    """
    Manages the lifecycle of orders, from signal to execution.
    """
    def __init__(self, connector: AngelOneConnector, risk_manager: RiskManager, instrument_manager: InstrumentManager):
        logger.info("Initializing Order Manager...")
        self.connector = connector
        self.risk_manager = risk_manager
        self.instrument_manager = instrument_manager
        self.active_orders = {}  # Maps our DB order.id to broker_order_id

    async def create_market_order(self, signal: dict, position_size: int):
        """Creates and places a market order based on a signal."""

        exchange = "NSE" # Should be configurable
        token = self.instrument_manager.get_token(signal['symbol'], exchange)

        if not token:
            logger.error(f"Could not find token for symbol {signal['symbol']}. Order not placed.")
            return

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": signal['symbol'],
            "symboltoken": token,
            "transactiontype": signal['side'],  # "BUY" or "SELL"
            "exchange": exchange,
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": str(position_size)
        }

        logger.info(f"Preparing to place market order with params: {order_params}")

        # 1. Save the pending order to our database to get an ID
        order_to_create = {
            "signal_id": signal.get('id'),
            "symbol": signal['symbol'],
            "side": signal['side'],
            "qty": position_size,
            "status": "PENDING",
            "ts": datetime.utcnow()
        }
        query = Order.__table__.insert().values(order_to_create)
        order_id = await database.execute(query)
        logger.info(f"Order {order_id} saved to DB with PENDING status.")

        # 2. Place the order with the broker
        broker_response = await self.connector.place_order(order_params)

        # 3. Update the order in our DB with the result
        if broker_response and broker_response.get('status') == 'success' and broker_response.get('orderid'):
            broker_order_id = broker_response['orderid']
            self.active_orders[order_id] = broker_order_id
            update_query = Order.__table__.update().where(Order.id == order_id).values(
                broker_order_id=broker_order_id, status="SUBMITTED"
            )
            await database.execute(update_query)
            logger.info(f"Order {order_id} placed successfully with broker ID {broker_order_id}.")
        else:
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED")
            await database.execute(update_query)
            logger.error(f"Failed to place order {order_id}. Response: {broker_response}")

    async def handle_signal(self, signal: dict):
        """Processes a trading signal to place an order."""
        logger.info(f"Order Manager received signal: {signal}")

        if not self.risk_manager.can_place_trade():
            return

        # Calculate position size using the risk manager
        position_size = self.risk_manager.calculate_position_size(
            entry_price=signal['entry'],
            stop_loss_price=signal['sl'],
            underlying=signal.get('underlying')
        )

        if position_size <= 0:
            logger.warning(f"Position size is {position_size}. Skipping trade for signal: {signal}")
            return

        await self.create_market_order(signal, position_size)

    async def create_exit_order(self, position: Position, reason: str):
        """Creates and places a market order to exit a position."""
        logger.info(f"Creating exit order for position {position.id} ({position.symbol}) due to: {reason}")

        # Determine the side of the exit order
        exit_side = "SELL" if position.side == "BUY" else "BUY"

        exchange = "NSE" # Should be configurable
        token = self.instrument_manager.get_token(position.symbol, exchange)

        if not token:
            logger.error(f"Could not find token for symbol {position.symbol}. Exit order not placed.")
            return

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": position.symbol,
            "symboltoken": token,
            "transactiontype": exit_side,
            "exchange": exchange,
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": str(position.qty)
        }

        logger.info(f"Preparing to place exit order with params: {order_params}")

        # For exit orders, we don't have a signal_id, but we could link them to the position_id
        # For simplicity, we'll create an order record without a signal_id for now.
        order_to_create = {
            "symbol": position.symbol,
            "side": exit_side,
            "qty": position.qty,
            "status": "PENDING",
            "ts": datetime.utcnow()
        }
        query = Order.__table__.insert().values(order_to_create)
        order_id = await database.execute(query)
        logger.info(f"Exit order {order_id} saved to DB with PENDING status.")

        broker_response = await self.connector.place_order(order_params)

        if broker_response and broker_response.get('status') == 'success' and broker_response.get('orderid'):
            broker_order_id = broker_response['orderid']
            self.active_orders[order_id] = broker_order_id
            update_query = Order.__table__.update().where(Order.id == order_id).values(
                broker_order_id=broker_order_id, status="SUBMITTED"
            )
            await database.execute(update_query)
            logger.info(f"Exit order {order_id} placed successfully with broker ID {broker_order_id}.")
        else:
            update_query = Order.__table__.update().where(Order.id == order_id).values(status="FAILED")
            await database.execute(update_query)
            logger.error(f"Failed to place exit order {order_id}. Response: {broker_response}")


    async def handle_order_update(self, update: dict):
        """
        Processes an order update from the broker's WebSocket feed.
        """
        logger.info(f"Received order update: {update}")
        broker_order_id = update.get("orderid")
        status = update.get("status")

        if not broker_order_id or not status:
            logger.warning(f"Skipping incomplete order update: {update}")
            return

        # 1. Find our internal order from the broker_order_id
        order_query = select(Order).where(Order.broker_order_id == broker_order_id)
        order = await database.fetch_one(order_query)

        if not order:
            logger.warning(f"Received update for an unknown order with broker ID: {broker_order_id}")
            return

        # 2. Update the order status in the DB
        update_query = Order.__table__.update().where(Order.id == order.id).values(status=status)
        await database.execute(update_query)
        logger.info(f"Updated order {order.id} status to {status}.")

        # 3. If the order is 'COMPLETE' (which means filled for AngelOne), create trade and position
        if status == 'COMPLETE':
            fill_price = update.get("averageprice")
            fill_qty = update.get("filledshares")
            fill_ts = pd.to_datetime(update.get("filltimestamp"))

            # Create a trade record
            trade_query = Trade.__table__.insert().values(
                order_id=order.id,
                fill_price=fill_price,
                qty=fill_qty,
                ts=fill_ts
            )
            await database.execute(trade_query)
            logger.info(f"Created trade record for order {order.id}.")

            # Fetch the original signal to get SL/TP
            signal_query = select(Signal).where(Signal.id == order.signal_id)
            signal = await database.fetch_one(signal_query)

            if not signal:
                logger.error(f"Could not find original signal for order {order.id}. Cannot create position.")
                return

            # Check if this is an entry or exit order. For now, we assume new orders are entries.
            # A more robust system would tag orders as 'ENTRY' or 'EXIT'.
            existing_position_query = select(Position).where(Position.symbol == order.symbol, Position.status == "OPEN")
            existing_position = await database.fetch_one(existing_position_query)

            if not existing_position:
                # This is an entry order, create a new position
                position_query = Position.__table__.insert().values(
                    symbol=order.symbol,
                    side=order.side,
                    qty=fill_qty,
                    avg_price=fill_price,
                    sl=signal.sl,
                    tp=signal.tp,
                    trailing_sl=signal.sl, # Initialize TSL with the original SL
                    highest_price_seen=fill_price, # Initialize with entry price
                    status="OPEN",
                    entry_ts=fill_ts
                )
                await database.execute(position_query)
                logger.info(f"Created new OPEN position for {order.symbol}.")
                self.risk_manager.record_trade(pnl=0) # Initial PnL is 0
            else:
                # This is an exit order, close the existing position
                pnl = (fill_price - existing_position.avg_price) * existing_position.qty if existing_position.side == 'BUY' else (existing_position.avg_price - fill_price) * existing_position.qty

                position_update_query = Position.__table__.update().where(Position.id == existing_position.id).values(
                    status="CLOSED",
                    pnl=pnl,
                    exit_ts=fill_ts
                )
                await database.execute(position_update_query)
                logger.info(f"Closed position for {order.symbol} with PnL: {pnl}.")
                self.risk_manager.record_trade(pnl=pnl)
