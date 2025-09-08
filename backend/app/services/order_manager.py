from datetime import datetime
from app.core.logging import logger
from app.angel_one_connector import AngelOneConnector
from app.services.risk_manager import RiskManager
from app.db.session import database
from app.models.trading import Order
# from app.models.trading import Trade - will be used later

class OrderManager:
    """
    Manages the lifecycle of orders, from signal to execution.
    """
    def __init__(self, connector: AngelOneConnector, risk_manager: RiskManager):
        logger.info("Initializing Order Manager...")
        self.connector = connector
        self.risk_manager = risk_manager
        self.active_orders = {}  # Maps our DB order.id to broker_order_id

    async def create_market_order(self, signal: dict, position_size: int):
        """Creates and places a market order based on a signal."""
        # This is a simplified order payload. A real one would need a symbol-to-token lookup.
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": signal['symbol'],
            "symboltoken": "TOKEN_PLACEHOLDER",  # This needs a lookup mechanism
            "transactiontype": signal['side'],  # "BUY" or "SELL"
            "exchange": "NSE",  # Should be configurable
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
            stop_loss_price=signal['sl']
        )

        if position_size <= 0:
            logger.warning(f"Position size is {position_size}. Skipping trade for signal: {signal}")
            return

        await self.create_market_order(signal, position_size)

    async def handle_order_update(self, update: dict):
        """
        Processes an order update from the broker. (Placeholder)
        This would be called by the WebSocket client.
        """
        logger.info(f"Received order update: {update}")
        # In a real implementation:
        # 1. Find our internal order_id from the broker_order_id in the update.
        # 2. Update the order status in the DB.
        # 3. If the order is 'FILLED', create a new record in the 'trades' table.
        # 4. Update the P&L in the RiskManager.
        # 5. Update the position in the 'positions' table.
        pass
