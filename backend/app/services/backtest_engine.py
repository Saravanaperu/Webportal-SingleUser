import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
from ..core.logging import logger

class BacktestEngine:
    def __init__(self):
        self.results = {}
        
    async def run_backtest(self, params: Dict) -> Dict:
        """Run backtest with given parameters"""
        try:
            symbol = params.get('symbol', 'BANKNIFTY')
            start_date = params.get('startDate')
            end_date = params.get('endDate')
            capital = params.get('capital', 100000)
            
            # Generate synthetic historical data for demo
            data = self._generate_synthetic_data(symbol, start_date, end_date)
            
            # Run strategy simulation
            trades = self._simulate_strategy(data, capital)
            
            # Calculate performance metrics
            results = self._calculate_metrics(trades, capital)
            
            return results
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {"error": str(e)}
    
    def _generate_synthetic_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate synthetic price data for backtesting"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Base prices for different symbols
        base_prices = {
            'BANKNIFTY': 51000,
            'NIFTY': 24500,
            'FINNIFTY': 23000
        }
        
        base_price = base_prices.get(symbol, 25000)
        
        # Generate daily data
        dates = pd.date_range(start=start, end=end, freq='D')
        dates = dates[dates.weekday < 5]  # Only weekdays
        
        # Random walk with trend
        returns = np.random.normal(0.0005, 0.02, len(dates))  # Slight positive bias
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        data = pd.DataFrame({
            'date': dates,
            'price': prices[:len(dates)],
            'volume': np.random.randint(50000, 200000, len(dates))
        })
        
        return data
    
    def _simulate_strategy(self, data: pd.DataFrame, capital: float) -> List[Dict]:
        """Simulate high win rate options scalping strategy"""
        trades = []
        current_capital = capital
        
        # Calculate indicators for better entry signals
        data['sma_5'] = data['price'].rolling(5).mean()
        data['sma_13'] = data['price'].rolling(13).mean()
        data['momentum'] = (data['price'] - data['price'].shift(5)) / data['price'].shift(5) * 100
        data['volatility'] = data['price'].rolling(10).std()
        
        for i in range(15, len(data) - 5):  # Need lookback for indicators
            # High probability entry conditions
            price = data.iloc[i]['price']
            momentum = data.iloc[i]['momentum']
            vol = data.iloc[i]['volatility']
            
            # High probability setups (stricter criteria)
            strong_momentum = abs(momentum) > 0.25
            vol_spike = vol > data['volatility'].mean() * 1.2
            price_above_sma5 = price > data.iloc[i]['sma_5']
            price_below_sma5 = price < data.iloc[i]['sma_5']
            
            trend_bullish = (data.iloc[i]['sma_5'] > data.iloc[i]['sma_13'] and 
                           momentum > 0.25 and vol_spike and price_above_sma5)
            trend_bearish = (data.iloc[i]['sma_5'] < data.iloc[i]['sma_13'] and 
                           momentum < -0.25 and vol_spike and price_below_sma5)
            
            if trend_bullish or trend_bearish:
                direction = 'CALL' if trend_bullish else 'PUT'
                
                # Dynamic option pricing based on volatility
                base_premium = 30 + (vol * 100)  # Higher vol = higher premium
                entry_price = max(15, min(150, base_premium))  # Realistic range
                
                # Position sizing - 1.5% risk per trade
                risk_amount = current_capital * 0.015
                quantity = max(25, int(risk_amount / entry_price))
                
                # Simulate realistic holding period (2-8 minutes for scalping)
                hold_periods = np.random.randint(2, 9)
                exit_idx = min(i + hold_periods, len(data) - 1)
                
                # Calculate underlying move
                underlying_move = (data.iloc[exit_idx]['price'] - data.iloc[i]['price']) / data.iloc[i]['price']
                
                # Improved options P&L simulation with Greeks
                if direction == 'CALL':
                    # Delta effect (0.5-0.7 for ATM options)
                    delta_pnl = underlying_move * np.random.uniform(0.5, 0.7)
                    # Gamma acceleration for large moves
                    if abs(underlying_move) > 0.003:
                        delta_pnl *= 1.2
                else:
                    delta_pnl = -underlying_move * np.random.uniform(0.5, 0.7)
                    if abs(underlying_move) > 0.003:
                        delta_pnl *= 1.2
                
                # Time decay (theta) - less for short holds
                theta_decay = -0.01 * hold_periods * (entry_price / 100)
                
                # Volatility impact
                vol_impact = (vol - data['volatility'].mean()) * 0.1
                
                total_pnl_pct = delta_pnl + theta_decay + vol_impact
                
                # Apply optimized stop loss (-35%) and take profit (+60%)
                if total_pnl_pct < -0.35:
                    total_pnl_pct = -0.35
                elif total_pnl_pct > 0.60:
                    total_pnl_pct = 0.60
                    
                # Add some realistic market noise (5% of trades hit stops)
                if np.random.random() < 0.05 and total_pnl_pct > 0:
                    total_pnl_pct = -0.35  # Occasional stop loss
                
                exit_price = entry_price * (1 + total_pnl_pct)
                pnl = (exit_price - entry_price) * quantity
                
                current_capital += pnl
                
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
    
    def _calculate_metrics(self, trades: List[Dict], initial_capital: float) -> Dict:
        """Calculate backtest performance metrics"""
        if not trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'final_capital': initial_capital
            }
        
        df = pd.DataFrame(trades)
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = len(df[df['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        final_capital = trades[-1]['capital']
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Calculate drawdown
        capital_series = df['capital'].values
        peak = np.maximum.accumulate(capital_series)
        drawdown = (capital_series - peak) / peak * 100
        max_drawdown = abs(drawdown.min())
        
        # Improved Sharpe ratio calculation
        returns = df['pnl'] / df['capital'].shift(1).fillna(initial_capital)
        excess_returns = returns - 0.065/252  # Risk-free rate
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': final_capital,
            'avg_pnl': df['pnl'].mean(),
            'avg_win': df[df['pnl'] > 0]['pnl'].mean() if len(df[df['pnl'] > 0]) > 0 else 0,
            'avg_loss': df[df['pnl'] < 0]['pnl'].mean() if len(df[df['pnl'] < 0]) > 0 else 0,
            'best_trade': df['pnl'].max(),
            'worst_trade': df['pnl'].min(),
            'avg_hold_time': df['hold_minutes'].mean() if 'hold_minutes' in df.columns else 0,
            'profit_factor': abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum()) if len(df[df['pnl'] < 0]) > 0 else float('inf')
        }

# Global instance
backtest_engine = BacktestEngine()