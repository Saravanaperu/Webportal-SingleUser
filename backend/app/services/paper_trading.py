import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from ..core.logging import logger

# --- Data Models for Paper Trading ---

@dataclass
class PaperPosition:
    """Represents an open position in paper trading."""
    symbol: str
    qty: int
    avg_price: float
    side: str
    entry_time: datetime
    total_cost: float
    # Optional: For more detailed simulation
    sl: Optional[float] = None
    tp: Optional[float] = None
    greeks: Dict = field(default_factory=dict)

@dataclass
class PaperHistoricalTrade:
    """Represents a completed trade in paper trading, mirroring HistoricalTrade model."""
    symbol: str
    side: str
    qty: int
    entry_price: float
    exit_price: float
    pnl: float
    entry_time: datetime
    exit_time: datetime
    holding_time_minutes: float
    pnl_percentage: float
    option_type: Optional[str] = None
    strike_price: Optional[float] = None
    underlying_price_entry: Optional[float] = None
    underlying_price_exit: Optional[float] = None
    reason: str = "CLOSED"

@dataclass
class PaperOrder:
    """Represents a paper trading order, mirroring the live Order model."""
    order_id: str
    symbol: str
    side: str
    qty: int
    price: float
    status: str = "PENDING" # PENDING, FILLED, FAILED
    ts: datetime = field(default_factory=datetime.now)
    reason: Optional[str] = None


class PaperTradingManager:
    """Manages paper trading positions and P&L calculation"""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.trades: List[PaperHistoricalTrade] = []
        self.active_orders: Dict[str, PaperOrder] = {}
        self.is_paper_mode = False
        
    def enable_paper_trading(self):
        """Enable paper trading mode"""
        self.is_paper_mode = True
        logger.info("Paper trading mode enabled")
        
    def disable_paper_trading(self):
        """Disable paper trading mode"""
        self.is_paper_mode = False
        logger.info("Paper trading mode disabled")
        
    def reset_paper_account(self):
        """Reset paper trading account"""
        self.current_balance = self.initial_balance
        self.positions.clear()
        self.trades.clear()
        logger.info(f"Paper account reset to ₹{self.initial_balance}")
        
    def _execute_paper_trade(self, order: PaperOrder) -> bool:
        """Internal logic to execute a paper trade and update state."""
        symbol, side, qty, price = order.symbol, order.side, order.qty, order.price
        order_value = qty * price

        if side == "BUY":
            if order_value > self.current_balance:
                order.status = "FAILED"
                order.reason = "INSUFFICIENT_FUNDS"
                logger.warning(f"[PAPER] Order {order.order_id} failed: Insufficient balance. Have ₹{self.current_balance:.2f}, need ₹{order_value:.2f}")
                return False

            self.current_balance -= order_value
            if symbol in self.positions:
                pos = self.positions[symbol]
                original_qty = pos.qty
                new_total_cost = pos.total_cost + order_value
                new_qty = pos.qty + qty
                pos.avg_price = new_total_cost / new_qty
                pos.qty = new_qty
                pos.total_cost = new_total_cost
                logger.info(f"[PAPER] Increased position in {symbol}. Qty: {original_qty} -> {new_qty}, Avg Price: ₹{pos.avg_price:.2f}")
            else:
                self.positions[symbol] = PaperPosition(
                    symbol=symbol, qty=qty, avg_price=price, side='BUY',
                    entry_time=datetime.now(), total_cost=order_value
                )
                logger.info(f"[PAPER] New position opened for {symbol}: {qty} @ ₹{price:.2f}")

        else:  # SELL
            if symbol in self.positions and self.positions[symbol].qty >= qty:
                position = self.positions[symbol]
                pnl = (price - position.avg_price) * qty
                self.current_balance += (qty * price)
                
                exit_time = datetime.now()
                holding_time_minutes = (exit_time - position.entry_time).total_seconds() / 60
                pnl_percentage = (pnl / position.total_cost) * 100 if position.total_cost else 0

                trade = PaperHistoricalTrade(
                    symbol=symbol, side=position.side, qty=qty,
                    entry_price=position.avg_price, exit_price=price, pnl=pnl,
                    entry_time=position.entry_time, exit_time=exit_time,
                    holding_time_minutes=holding_time_minutes, pnl_percentage=pnl_percentage
                )
                self.trades.append(trade)
                
                logger.info(
                    f"[PAPER] Closed position in {symbol}. Sold {qty} @ ₹{price:.2f}, "
                    f"Entry: ₹{position.avg_price:.2f}, P&L: ₹{pnl:.2f} ({pnl_percentage:.2f}%)"
                )

                if position.qty == qty:
                    del self.positions[symbol]
                else:
                    position.qty -= qty
            else:
                order.status = "FAILED"
                order.reason = "INSUFFICIENT_POSITION"
                logger.warning(f"[PAPER] Order {order.order_id} failed: No sufficient position to sell.")
                return False
        
        order.status = "FILLED"
        return True

    async def place_paper_order(self, symbol: str, side: str, qty: int, price: float) -> Dict:
        """Creates and executes a paper trading order, simulating an order lifecycle."""
        if not self.is_paper_mode:
            return {"error": "Paper trading not enabled"}

        order_id = f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.trades)}"
        order = PaperOrder(order_id=order_id, symbol=symbol, side=side, qty=qty, price=price)

        self.active_orders[order_id] = order
        logger.info(f"[PAPER] Created order {order_id}: {side} {qty} {symbol} @ ₹{price:.2f}")

        # In paper trading, we execute immediately.
        success = self._execute_paper_trade(order)

        # Clean up finished order
        del self.active_orders[order_id]

        if success:
            logger.info(f"[PAPER] Order {order_id} filled successfully.")
            return {"status": "success", "order_id": order_id, **asdict(order)}
        else:
            return {"status": "error", "order_id": order_id, "reason": order.reason}
        
    def get_paper_positions(self) -> List[Dict]:
        """Get current paper trading positions"""
        # Convert dataclass to dict for API response, handling datetime
        pos_list = []
        for pos in self.positions.values():
            pos_dict = asdict(pos)
            pos_dict['entry_time'] = pos.entry_time.isoformat()
            pos_list.append(pos_dict)
        return pos_list
        
    def get_paper_trades(self) -> List[Dict]:
        """Get paper trading history"""
        # Convert dataclass to dict for API response, handling datetime
        trade_list = []
        for trade in self.trades:
            trade_dict = asdict(trade)
            trade_dict['entry_time'] = trade.entry_time.isoformat()
            trade_dict['exit_time'] = trade.exit_time.isoformat()
            trade_list.append(trade_dict)
        return trade_list
        
    def get_paper_stats(self) -> Dict:
        """Get paper trading statistics"""
        if not self.trades:
            return {
                'total_pnl': 0, 'total_trades': 0, 'win_trades': 0, 'loss_trades': 0,
                'win_rate': 0, 'avg_win': 0, 'avg_loss': 0,
                'current_balance': self.current_balance,
                'initial_balance': self.initial_balance
            }
            
        total_pnl = sum(trade.pnl for trade in self.trades)
        win_trades = [t for t in self.trades if t.pnl > 0]
        loss_trades = [t for t in self.trades if t.pnl < 0]
        
        return {
            'total_pnl': round(total_pnl, 2),
            'total_trades': len(self.trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': round((len(win_trades) / len(self.trades)) * 100, 2) if self.trades else 0,
            'avg_win': round(sum(t.pnl for t in win_trades) / len(win_trades), 2) if win_trades else 0,
            'avg_loss': round(sum(t.pnl for t in loss_trades) / len(loss_trades), 2) if loss_trades else 0,
            'current_balance': round(self.current_balance, 2),
            'initial_balance': self.initial_balance
        }

# Global paper trading manager
paper_trading_manager = PaperTradingManager()