import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
from scipy.stats import norm
import numpy as np

from ..core.logging import logger
from ..core.config import settings
from ..core.constants import INDEX_SYMBOLS

class OptionsManager:
    """Manages options chain, strike selection, and Greeks calculations for scalping."""
    
    def __init__(self, rest_client, instrument_manager):
        self.rest_client = rest_client
        self.instrument_manager = instrument_manager
        self.options_chain = {}
        self.spot_prices = {}  # Cache for spot prices: {index: (price, timestamp)}
        self.atm_strikes = {}
        self.last_chain_update = {}
        self.spot_price_cache_ttl = timedelta(seconds=2)
        
    # Class constants
    SPOT_SYMBOLS = {
        'BANKNIFTY': 'BANKNIFTY-INDEX',
        'NIFTY': 'NIFTY 50',
        'FINNIFTY': 'FINNIFTY'
    }
    
    
    async def get_spot_price(self, index: str) -> Optional[float]:
        """Get current spot price of the underlying index, with caching."""
        now = datetime.utcnow()

        # Check cache first
        if index in self.spot_prices:
            price, ts = self.spot_prices[index]
            if now - ts < self.spot_price_cache_ttl:
                return price

        try:
            spot_symbol = INDEX_SYMBOLS.get(index)
            if not spot_symbol:
                return None
                
            # Get LTP from broker API
            response = await self.rest_client.get_ltp(spot_symbol, 'NSE')
            if response and 'data' in response:
                ltp = float(response['data']['ltp'])
                # Update cache
                self.spot_prices[index] = (ltp, now)
                return ltp
                
        except Exception as e:
            logger.error(f"Error getting spot price for {index}: {e}", exc_info=True)

        # Return stale price if API fails but a cached value exists
        if index in self.spot_prices:
            return self.spot_prices[index][0]

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
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Black-Scholes calculation error for S={S}, K={K}, T={T}, sigma={sigma}: {e}", exc_info=True)
            return 0
        except Exception as e:
            logger.error(f"An unexpected error occurred in Black-Scholes calculation: {e}", exc_info=True)
            return 0
    
    def calculate_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> Dict:
        """Calculate option Greeks."""
        greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
        try:
            if T <= 0 or S <= 0 or K <= 0 or sigma <=0:
                return greeks

            d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Delta
            if option_type == 'CE':
                greeks['delta'] = norm.cdf(d1)
            else:
                greeks['delta'] = -norm.cdf(-d1)
            
            # Gamma
            greeks['gamma'] = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            
            # Theta (per day)
            if option_type == 'CE':
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                        r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
            else:
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                        r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
            greeks['theta'] = theta

            # Vega (per 1% change in IV)
            greeks['vega'] = S * norm.pdf(d1) * np.sqrt(T) / 100
            
            return {k: round(v, 6) for k, v in greeks.items()}

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Greeks calculation error for S={S}, K={K}, T={T}, sigma={sigma}: {e}", exc_info=True)
            return greeks
        except Exception as e:
            logger.error(f"An unexpected error occurred in Greeks calculation: {e}", exc_info=True)
            return greeks
    
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
                greeks = self.calculate_greeks(spot_price, strike, T, settings.trading.risk_free_rate, settings.trading.default_volatility, option_type)
                
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
        """
        Calculate scalping suitability score for an option based on a weighted formula
        of its Greeks, premium, and moneyness.
        """
        try:
            weights = settings.strategy.scoring_weights

            # 1. Delta Score (30% weight): Prefers higher delta for better directional moves.
            delta_score = abs(greeks['delta']) * weights.delta_multiplier
            
            # 2. Gamma Score (25% weight): Prefers higher gamma for faster acceleration.
            gamma_score = greeks['gamma'] * weights.gamma_multiplier
            
            # 3. Theta Score (20% weight): Penalizes high theta decay.
            theta_score = max(0, weights.theta_base + greeks['theta'])  # Theta is negative, so we add.
            
            # 4. Premium Score (15% weight): Prefers premiums closer to a target value.
            premium_distance = abs(ltp - weights.premium_target)
            premium_score = max(0, weights.theta_base - (premium_distance / weights.premium_divisor))
            
            # 5. Moneyness Score (10% weight): Slightly prefers options closer to ATM.
            moneyness_distance = abs(strike - atm_strike)
            moneyness_score = max(0, weights.theta_base - (moneyness_distance / weights.moneyness_divisor))
            
            # Combine scores with their respective weights
            total_score = (delta_score * 0.3 +
                           gamma_score * 0.25 +
                           theta_score * 0.2 +
                           premium_score * 0.15 +
                           moneyness_score * 0.1)
            
            return round(total_score, 2)

        except (KeyError, TypeError) as e:
            logger.error(f"Error calculating scalping score due to missing key: {e}", exc_info=True)
            return 0
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Numerical error in calculating scalping score: {e}", exc_info=True)
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
        except (ValueError, TypeError) as e:
            logger.error(f"Error getting nearest expiry: {e}")
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
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating time to expiry: {e}")
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
    
# Global instance
options_manager = None

def get_options_manager(rest_client=None, instrument_manager=None):
    global options_manager
    if options_manager is None and rest_client and instrument_manager:
        options_manager = OptionsManager(rest_client, instrument_manager)
    return options_manager