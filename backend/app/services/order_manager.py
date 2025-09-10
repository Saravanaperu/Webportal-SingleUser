from datetime import datetime
from typing import Dict, Optional
from ..core.logging import logger
from ..core.config import settings
from .risk_manager import RiskManager
from ..models.trading import Order, Trade, HistoricalTrade
from ..db.session import database

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
        self.open_positions = {}  # Maps symbol to position details
        self.daily_trades_count = 0
        self.daily_pnl = 0.0

    async def create_options_order(self, signal: dict, position_size: int):
        """Creates and places an options order optimized for scalping."""
        symbol = signal['symbol']
        exchange = "NFO"  # Options are traded on NFO
        token = self.instrument_manager.get_token(symbol, exchange)

        order_to_create = {
            "signal_id": signal.get('id'), "symbol": symbol, "side": signal['side'],
            "qty": position_size, "status": "PENDING", "ts": datetime.utcnow(),
            "sl": signal.get('sl'), "tp": signal.get('tp'), 
            "atr_at_entry": signal.get('atr_at_entry'),
            "confidence": signal.get('confidence'),
            "greeks": str(signal.get('greeks', {}))  # Store Greeks as string
        }
        query = Order.__table__.insert().values(order_to_create)
        order_id = await self.db.execute(query)
        logger.info(f"Options order {order_id} created for {symbol}")

        if not token:
            logger.error(f"Token not found for {symbol}. Order {order_id} failed.")
            update_query = Order.__table__.update().where(Order.id == order_id).values(
                status="FAILED", reason="TOKEN_NOT_FOUND"
            )
            await self.db.execute(update_query)
            return

        # Options order parameters
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": signal['side'],
            "exchange": exchange,
            "ordertype": "MARKET",  # Market orders for fast execution
            "producttype": "INTRADAY",  # Intraday for options scalping
            "duration": "DAY",
            "quantity": str(position_size)
        }
        
        try:
            broker_response = await self.connector.place_order(order_params)
            
            if broker_response and broker_response.get('orderid'):
                broker_order_id = broker_response['orderid']
                self.active_orders[broker_order_id] = order_id
                update_query = Order.__table__.update().where(Order.id == order_id).values(
                    broker_order_id=broker_order_id, status="SUBMITTED"
                )
                await self.db.execute(update_query)
                logger.info(f"Options order {order_id} submitted with broker ID {broker_order_id}")
            else:
                reason = str(broker_response) if broker_response else "NO_RESPONSE"
                update_query = Order.__table__.update().where(Order.id == order_id).values(
                    status="FAILED", reason=reason
                )
                await self.db.execute(update_query)
                logger.error(f"Options order {order_id} failed: {reason}")
                
        except Exception as e:
            logger.error(f"Error placing options order: {e}", exc_info=True)
            update_query = Order.__table__.update().where(Order.id == order_id).values(
                status="FAILED", reason=str(e)
            )
            await self.db.execute(update_query)

    async def handle_signal(self, signal: dict):
        """Processes an options trading signal."""
        symbol = signal['symbol']
        
        # Check for existing position
        if symbol in self.open_positions:
            logger.warning(f"Position already exists for {symbol}. Ignoring signal.")
            return
            
        # Risk management checks
        if not self.risk_manager.can_place_trade():
            logger.warning("Risk manager blocked new trade")
            return
            
        # Check maximum positions limit
        if len(self.open_positions) >= settings.risk.max_positions:
            logger.warning(f"Maximum positions ({settings.risk.max_positions}) reached")
            return

        # Calculate position size for options
        position_size = self.calculate_options_position_size(signal)
        
        if position_size > 0:
            await self.create_options_order(signal, position_size)
        else:
            logger.warning(f"Position size calculated as 0 for {symbol}")
    
    def calculate_options_position_size(self, signal: dict) -> int:
        """Calculate position size specifically for options trading."""
        try:
            entry_price = signal['entry']
            account_balance = self.risk_manager.get_account_balance()
            
            # Risk per trade as percentage of account
            risk_amount = account_balance * (settings.risk.risk_per_trade_percent / 100)
            
            # For options, risk is the premium paid
            # Calculate lot size (assuming standard lot sizes)
            lot_sizes = {
                'BANKNIFTY': 15,
                'NIFTY': 50,
                'FINNIFTY': 40
            }
            
            # Determine index from symbol
            index = None
            for idx in lot_sizes.keys():
                if idx in signal['symbol']:
                    index = idx
                    break
                    
            if not index:
                logger.error(f"Could not determine index for {signal['symbol']}")
                return 0
                
            lot_size = lot_sizes[index]
            premium_per_lot = entry_price * lot_size
            
            # Calculate number of lots based on risk
            max_lots = int(risk_amount / premium_per_lot)
            
            # Ensure at least 1 lot but not more than risk allows
            lots = max(1, min(max_lots, 3))  # Max 3 lots for scalping
            
            total_quantity = lots * lot_size
            total_premium = total_quantity * entry_price
            
            logger.info(f"Options position size: {lots} lots = {total_quantity} qty, Premium: ₹{total_premium:.2f}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"Error calculating options position size: {e}", exc_info=True)
            return 0

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

                # Calculate options-specific metrics
                holding_time_minutes = (datetime.utcnow() - position['entry_time']).total_seconds() / 60
                pnl_percentage = (pnl / (position['entry_price'] * original_qty)) * 100
                
                trade_log = {
                    "symbol": symbol, "side": position['side'], "qty": original_qty,
                    "entry_price": position['entry_price'], "exit_price": exit_price,
                    "pnl": pnl, "entry_time": position['entry_time'], "exit_time": datetime.utcnow(),
                    "holding_time_minutes": holding_time_minutes, "pnl_percentage": pnl_percentage
                }
                insert_query = HistoricalTrade.__table__.insert().values(trade_log)
                await self.db.execute(insert_query)

                await self.risk_manager.record_trade(pnl=pnl)
                del self.open_positions[symbol]
                del self.active_orders[broker_order_id]

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
            logger.info(f"New position opened on first fill for {symbol}.")
        else:
            # Logic for subsequent partial fills
            position = self.open_positions[symbol]

            # The 'filledshares' from the broker is the CUMULATIVE quantity.
            # We need to calculate the quantity of this specific fill.
            last_fill_qty = fill_qty - position['qty']
            if last_fill_qty <= 0:
                logger.warning(f"Received a partial fill update for {symbol} with no new shares. Ignoring.")
                return

            # The 'averageprice' from the broker is the average for the ENTIRE order so far.
            # We need to update our position's average price based on this.
            new_total_cost = fill_price * fill_qty # The total cost is now based on the new average price

            position['entry_price'] = new_total_cost / fill_qty
            position['qty'] = fill_qty
            position['total_cost'] = new_total_cost
            
            # Store additional options data
            if 'greeks' in order.__dict__:
                position['greeks'] = order.greeks
            if 'confidence' in order.__dict__:
                position['confidence'] = order.confidence
                
            logger.info(f"Options position updated for {symbol}: Qty={position['qty']}, Avg Price=₹{position['entry_price']:.2f}")

        if status == "COMPLETE":
            del self.active_orders[broker_order_id]

    def get_open_positions(self) -> list[dict]:
        return list(self.open_positions.values())

    async def close_position(self, position: dict, reason: str):
        """Close an options position."""
        symbol = position['symbol']
        logger.info(f"Closing options position {symbol} due to {reason}")
        
        # For options, we always sell to close (since we only buy options for scalping)
        closing_signal = {
            'symbol': symbol,
            'side': 'SELL',  # Always sell to close options positions
            'id': None,
            'entry': 0,  # Will be filled by market price
            'reason': f'CLOSE_{reason}'
        }
        
        await self.create_options_order(closing_signal, position['qty'])

    def update_position_sl(self, position: dict, new_sl: float):
        """Update stop loss for an options position."""
        symbol = position['symbol']
        if symbol in self.open_positions:
            old_sl = self.open_positions[symbol].get('sl', 0)
            self.open_positions[symbol]['sl'] = new_sl
            logger.info(f"Updated SL for {symbol}: ₹{old_sl:.2f} → ₹{new_sl:.2f}")
    
    def get_position_pnl(self, position: dict, current_price: float) -> Dict:
        """Calculate detailed P&L for options position."""
        entry_price = position['entry_price']
        qty = position['qty']
        
        # Calculate absolute and percentage P&L
        pnl_absolute = (current_price - entry_price) * qty
        pnl_percentage = ((current_price - entry_price) / entry_price) * 100
        
        # Calculate holding time
        holding_time = (datetime.utcnow() - position['entry_time']).total_seconds() / 60
        
        return {
            'pnl_absolute': pnl_absolute,
            'pnl_percentage': pnl_percentage,
            'holding_time_minutes': holding_time,
            'current_value': current_price * qty,
            'invested_amount': entry_price * qty
        }
