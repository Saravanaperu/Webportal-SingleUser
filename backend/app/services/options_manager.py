import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
from scipy.stats import norm
import numpy as np

from ..core.logging import logger
from ..core.config import settings

class OptionsManager:
    """Manages options chain, strike selection, and Greeks calculations for scalping."""
    
    def __init__(self, rest_client, instrument_manager):
        self.rest_client = rest_client
        self.instrument_manager = instrument_manager
        self.options_chain = {}
        self.spot_prices = {}
        self.atm_strikes = {}
        self.last_chain_update = {}
        
    async def get_spot_price(self, index: str) -> Optional[float]:
        """Get current spot price of the underlying index."""
        try:
            # Map index names to spot symbols
            spot_symbols = {
                'BANKNIFTY': 'BANKNIFTY-INDEX',
                'NIFTY': 'NIFTY 50',
                'FINNIFTY': 'FINNIFTY'
            }
            
            spot_symbol = spot_symbols.get(index)
            if not spot_symbol:
                return None
                
            # Get LTP from broker API
            response = await self.rest_client.get_ltp(spot_symbol, 'NSE')
            if response and 'data' in response:
                ltp = float(response['data']['ltp'])
                self.spot_prices[index] = ltp
                return ltp
                
        except Exception as e:
            logger.error(f"Error getting spot price for {index}: {e}")
        return None
    
    def calculate_atm_strike(self, spot_price: float, index: str) -> int:
        """Calculate ATM strike based on spot price."""
        strike_intervals = {
            'BANKNIFTY': 100,
            'NIFTY': 50,
            'FINNIFTY': 50
        }
        
        interval = strike_intervals.get(index, 50)
        atm_strike = round(spot_price / interval) * interval
        self.atm_strikes[index] = atm_strike
        return atm_strike
    
    def black_scholes_price(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
        """Calculate Black-Scholes option price."""
        try:
            if T <= 0:
                return max(0, S - K) if option_type == 'CE' else max(0, K - S)
                
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            if option_type == 'CE':
                price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:  # PE
                price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
                
            return max(0, price)
        except:
            return 0
    
    def calculate_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> Dict:
        """Calculate option Greeks."""
        try:
            if T <= 0:
                return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
                
            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Delta
            if option_type == 'CE':
                delta = norm.cdf(d1)
            else:
                delta = -norm.cdf(-d1)
            
            # Gamma
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            
            # Theta (per day)
            if option_type == 'CE':
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                        r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
            else:
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                        r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
            
            # Vega (per 1% change in IV)
            vega = S * norm.pdf(d1) * np.sqrt(T) / 100
            
            return {
                'delta': round(delta, 4),
                'gamma': round(gamma, 6),
                'theta': round(theta, 4),
                'vega': round(vega, 4)
            }
        except:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
    
    async def get_best_strikes_for_scalping(self, index: str, direction: str) -> List[Dict]:
        """Get best option strikes for scalping based on direction and Greeks."""
        try:
            spot_price = await self.get_spot_price(index)
            if not spot_price:
                return []
            
            atm_strike = self.calculate_atm_strike(spot_price, index)
            strike_range = settings.strategy.strike_selection.atm_range
            
            # Get available strikes around ATM
            strikes_to_check = []
            strike_interval = 100 if index == 'BANKNIFTY' else 50
            
            for i in range(-strike_range, strike_range + 1):
                strike = atm_strike + (i * strike_interval)
                strikes_to_check.append(strike)
            
            # Get current expiry
            expiry = self.get_nearest_expiry()
            if not expiry:
                return []
            
            best_options = []
            
            for strike in strikes_to_check:
                option_type = 'CE' if direction == 'BUY' else 'PE'
                symbol = f"{index}{expiry}{strike}{option_type}"
                
                # Get option data
                option_data = await self.get_option_data(symbol)
                if not option_data:
                    continue
                
                ltp = option_data.get('ltp', 0)
                if not (settings.strategy.strike_selection.min_premium <= ltp <= settings.strategy.strike_selection.max_premium):
                    continue
                
                # Calculate Greeks
                T = self.get_time_to_expiry(expiry)
                greeks = self.calculate_greeks(spot_price, strike, T, 0.06, 0.2, option_type)
                
                # Filter by Greeks
                if (abs(greeks['delta']) < settings.strategy.min_delta or 
                    abs(greeks['delta']) > settings.strategy.max_delta or
                    greeks['theta'] < settings.strategy.max_theta):
                    continue
                
                # Calculate scalping score
                scalping_score = self.calculate_scalping_score(greeks, ltp, strike, atm_strike)
                
                best_options.append({
                    'symbol': symbol,
                    'strike': strike,
                    'ltp': ltp,
                    'greeks': greeks,
                    'scalping_score': scalping_score,
                    'moneyness': abs(strike - spot_price) / spot_price * 100
                })
            
            # Sort by scalping score and return top 3
            best_options.sort(key=lambda x: x['scalping_score'], reverse=True)
            return best_options[:3]
            
        except Exception as e:
            logger.error(f"Error getting best strikes for {index}: {e}")
            return []
    
    def calculate_scalping_score(self, greeks: Dict, ltp: float, strike: int, atm_strike: int) -> float:
        """Calculate scalping suitability score for an option."""
        try:
            # Higher delta = better directional movement
            delta_score = abs(greeks['delta']) * 100
            
            # Higher gamma = better acceleration
            gamma_score = greeks['gamma'] * 10000
            
            # Lower theta decay = better for short holds
            theta_score = max(0, 10 + greeks['theta'])  # Theta is negative
            
            # Moderate premium preferred
            premium_score = max(0, 10 - abs(ltp - 50) / 10)
            
            # Slight preference for ATM/ITM
            moneyness_score = max(0, 10 - abs(strike - atm_strike) / 100)
            
            total_score = (delta_score * 0.3 + gamma_score * 0.25 + 
                          theta_score * 0.2 + premium_score * 0.15 + 
                          moneyness_score * 0.1)
            
            return round(total_score, 2)
        except:
            return 0
    
    def get_nearest_expiry(self) -> Optional[str]:
        """Get the nearest weekly/monthly expiry date."""
        try:
            today = datetime.now().date()
            
            # Find next Thursday (weekly expiry)
            days_ahead = 3 - today.weekday()  # Thursday is 3
            if days_ahead <= 0:
                days_ahead += 7
            
            next_expiry = today + timedelta(days=days_ahead)
            
            # Check if within max days to expiry
            if (next_expiry - today).days <= settings.strategy.expiry_preference.max_days_to_expiry:
                return next_expiry.strftime('%d%b%Y').upper()
            
            return None
        except:
            return None
    
    def get_time_to_expiry(self, expiry_str: str) -> float:
        """Calculate time to expiry in years."""
        try:
            expiry_date = datetime.strptime(expiry_str, '%d%b%Y').date()
            today = datetime.now().date()
            days_to_expiry = (expiry_date - today).days
            
            # Add intraday time (assume 3:30 PM expiry)
            hours_to_expiry = days_to_expiry * 24 + (15.5 - datetime.now().hour)
            return max(0.001, hours_to_expiry / (365 * 24))  # Convert to years
        except:
            return 0.001
    
    async def get_option_data(self, symbol: str) -> Optional[Dict]:
        """Get current option data including LTP, volume, etc."""
        try:
            token = self.instrument_manager.get_token(symbol, 'NFO')
            if not token:
                return None
            
            response = await self.rest_client.get_ltp(symbol, 'NFO')
            if response and 'data' in response:
                return response['data']
            
        except Exception as e:
            logger.error(f"Error getting option data for {symbol}: {e}")
        return None
    
    def is_high_volume_session(self) -> bool:
        """Check if current time is in high volume trading session."""
        now = datetime.now().time()
        
        for session in settings.trading.high_volume_sessions:
            start = datetime.strptime(session['start'], '%H:%M').time()
            end = datetime.strptime(session['end'], '%H:%M').time()
            if start <= now <= end:
                return True
        return False
    
    def should_avoid_trading(self) -> bool:
        """Check if current time is in avoid trading session."""
        now = datetime.now().time()
        
        for session in settings.trading.avoid_sessions:
            start = datetime.strptime(session['start'], '%H:%M').time()
            end = datetime.strptime(session['end'], '%H:%M').time()
            if start <= now <= end:
                return True
        return False

# Global instance
options_manager = None

def get_options_manager(rest_client=None, instrument_manager=None):
    global options_manager
    if options_manager is None and rest_client and instrument_manager:
        options_manager = OptionsManager(rest_client, instrument_manager)
    return options_manager