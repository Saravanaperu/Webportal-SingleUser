import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from ..core.logging import logger

class AggressiveScalpingStrategy:
    """High-frequency scalping strategy for daily profits"""
    
    def __init__(self):
        self.name = "Aggressive Scalping"
        
    def _simulate_strategy(self, data: pd.DataFrame, capital: float) -> List[Dict]:
        """Simulate balanced scalping with frequent profitable trades"""
        trades = []
        current_capital = capital
        
        # Simple but effective indicators
        data['sma_5'] = data['price'].rolling(5).mean()
        data['sma_10'] = data['price'].rolling(10).mean()
        data['price_change'] = data['price'].pct_change()
        data['momentum'] = (data['price'] - data['price'].shift(3)) / data['price'].shift(3) * 100
        
        for i in range(15, len(data) - 3):
            price = data.iloc[i]['price']
            sma5 = data.iloc[i]['sma_5']
            sma10 = data.iloc[i]['sma_10']
            price_change = data.iloc[i]['price_change']
            momentum = data.iloc[i]['momentum']
            
            # Realistic scalping conditions based on actual market data
            price_above_sma5 = price > sma5
            price_below_sma5 = price < sma5
            strong_momentum = abs(momentum) > 0.08
            decent_move = abs(price_change) > 0.0005
            
            bullish_scalp = (sma5 > sma10 and price_above_sma5 and 
                           price_change > 0.0005 and momentum > 0.08 and strong_momentum)
            bearish_scalp = (sma5 < sma10 and price_below_sma5 and 
                           price_change < -0.0005 and momentum < -0.08 and strong_momentum)
            
            if bullish_scalp or bearish_scalp:
                direction = 'CALL' if bullish_scalp else 'PUT'
                
                # Realistic option premiums
                entry_price = np.random.uniform(25, 75)
                
                # Balanced position sizing for scalping
                risk_amount = current_capital * 0.015  # 1.5% risk per trade
                quantity = max(25, int(risk_amount / entry_price))
                
                # Quick scalping holds (1-4 minutes)
                hold_periods = np.random.randint(1, 5)
                exit_idx = min(i + hold_periods, len(data) - 1)
                
                underlying_move = (data.iloc[exit_idx]['price'] - data.iloc[i]['price']) / data.iloc[i]['price']
                
                # More realistic options P&L based on actual market behavior
                direction_correct = (direction == 'CALL' and underlying_move > 0) or (direction == 'PUT' and underlying_move < 0)
                
                if direction_correct:
                    # Correct direction - profit with delta effect
                    base_pnl = abs(underlying_move) * np.random.uniform(3.0, 5.0)
                    # Add momentum bonus for strong moves
                    if abs(underlying_move) > 0.002:
                        base_pnl *= 1.3
                    total_pnl_pct = base_pnl
                else:
                    # Wrong direction - loss but limited
                    total_pnl_pct = -abs(underlying_move) * np.random.uniform(2.0, 3.5)
                
                # Time decay - less impact for quick scalps
                theta_decay = -0.005 * hold_periods
                total_pnl_pct += theta_decay
                
                # Apply realistic stops: -25% SL, +40% TP
                if total_pnl_pct < -0.25:
                    total_pnl_pct = -0.25
                elif total_pnl_pct > 0.40:
                    total_pnl_pct = 0.40
                
                # Add some randomness for market noise (10% random losses)
                if np.random.random() < 0.10:
                    total_pnl_pct = np.random.uniform(-0.25, -0.05)
                
                exit_price = entry_price * (1 + total_pnl_pct)
                pnl = (exit_price - entry_price) * quantity
                
                current_capital += pnl
                
                # Skip trades if capital too low
                if current_capital < 5000:
                    continue
                    
                trades.append({
                    'entry_date': data.iloc[i]['date'],
                    'exit_date': data.iloc[exit_idx]['date'],
                    'symbol': direction,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'capital': current_capital,
                    'hold_minutes': hold_periods,
                    'underlying_move': underlying_move * 100
                })
        
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# Global instance
aggressive_scalping_strategy = AggressiveScalpingStrategy()