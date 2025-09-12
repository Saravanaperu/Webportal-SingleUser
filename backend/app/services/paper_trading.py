import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from ..core.logging import logger

class PaperTradingManager:
    """Manages paper trading positions and P&L calculation"""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: Dict[str, Dict] = {}
        self.trades: List[Dict] = []
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
        
    async def place_paper_order(self, symbol: str, side: str, qty: int, price: float) -> Dict:
        """Place a paper trading order"""
        if not self.is_paper_mode:
            return {"error": "Paper trading not enabled"}
            
        order_value = qty * price
        
        if side == "BUY" and order_value > self.current_balance:
            return {"error": "Insufficient balance for paper trade"}
            
        order_id = f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.trades)}"
        
        # Execute paper order
        if side == "BUY":
            self.current_balance -= order_value
            if symbol in self.positions:
                # Average price calculation for existing position
                existing_qty = self.positions[symbol]['qty']
                existing_price = self.positions[symbol]['avg_price']
                total_qty = existing_qty + qty
                avg_price = ((existing_qty * existing_price) + (qty * price)) / total_qty
                self.positions[symbol] = {
                    'qty': total_qty,
                    'avg_price': avg_price,
                    'side': 'BUY',
                    'entry_time': self.positions[symbol]['entry_time']
                }
            else:
                self.positions[symbol] = {
                    'qty': qty,
                    'avg_price': price,
                    'side': 'BUY',
                    'entry_time': datetime.now()
                }
        else:  # SELL
            if symbol in self.positions and self.positions[symbol]['qty'] >= qty:
                # Close position
                position = self.positions[symbol]
                pnl = (price - position['avg_price']) * qty
                self.current_balance += (qty * price)
                
                # Record trade
                trade = {
                    'symbol': symbol,
                    'entry_price': position['avg_price'],
                    'exit_price': price,
                    'qty': qty,
                    'pnl': pnl,
                    'entry_time': position['entry_time'],
                    'exit_time': datetime.now(),
                    'duration': (datetime.now() - position['entry_time']).total_seconds()
                }
                self.trades.append(trade)
                
                # Update position
                if position['qty'] == qty:
                    del self.positions[symbol]
                else:
                    self.positions[symbol]['qty'] -= qty
            else:
                return {"error": "Insufficient position to sell"}
        
        logger.info(f"Paper trade executed: {side} {qty} {symbol} @ ₹{price}")
        return {
            "status": "success",
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price
        }
        
    def get_paper_positions(self) -> List[Dict]:
        """Get current paper trading positions"""
        return [
            {
                'symbol': symbol,
                'qty': pos['qty'],
                'avg_price': pos['avg_price'],
                'side': pos['side'],
                'entry_time': pos['entry_time'].isoformat()
            }
            for symbol, pos in self.positions.items()
        ]
        
    def get_paper_trades(self) -> List[Dict]:
        """Get paper trading history"""
        return [
            {
                'symbol': trade['symbol'],
                'entry_price': trade['entry_price'],
                'exit_price': trade['exit_price'],
                'qty': trade['qty'],
                'pnl': trade['pnl'],
                'entry_time': trade['entry_time'].isoformat(),
                'exit_time': trade['exit_time'].isoformat(),
                'duration': trade['duration']
            }
            for trade in self.trades
        ]
        
    def get_paper_stats(self) -> Dict:
        """Get paper trading statistics"""
        if not self.trades:
            return {
                'total_pnl': 0,
                'total_trades': 0,
                'win_trades': 0,
                'loss_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'current_balance': self.current_balance,
                'initial_balance': self.initial_balance
            }
            
        total_pnl = sum(trade['pnl'] for trade in self.trades)
        win_trades = [t for t in self.trades if t['pnl'] > 0]
        loss_trades = [t for t in self.trades if t['pnl'] < 0]
        
        return {
            'total_pnl': round(total_pnl, 2),
            'total_trades': len(self.trades),
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': round((len(win_trades) / len(self.trades)) * 100, 2) if self.trades else 0,
            'avg_win': round(sum(t['pnl'] for t in win_trades) / len(win_trades), 2) if win_trades else 0,
            'avg_loss': round(sum(t['pnl'] for t in loss_trades) / len(loss_trades), 2) if loss_trades else 0,
            'current_balance': round(self.current_balance, 2),
            'initial_balance': self.initial_balance
        }

# Global paper trading manager
paper_trading_manager = PaperTradingManager()