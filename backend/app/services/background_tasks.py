import asyncio
from datetime import datetime
from ..core.logging import logger
from .cache_manager import cache_manager

class BackgroundTaskManager:
    """Manages background tasks for continuous data sync and calculations"""
    
    def __init__(self):
        self.tasks = {}
        self.running = False
        
    async def start(self, app_state):
        """Start all background tasks"""
        self.running = True
        self.app_state = app_state
        
        # Start continuous data sync
        self.tasks['data_sync'] = asyncio.create_task(self._continuous_data_sync())
        
        # Start options chain calculator
        self.tasks['options_calc'] = asyncio.create_task(self._options_chain_calculator())
        
        logger.info("Background tasks started")
        
    async def stop(self):
        """Stop all background tasks"""
        self.running = False
        for task_name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Background task {task_name} cancelled")
                
    async def _continuous_data_sync(self):
        """Continuously sync critical data to cache"""
        while self.running:
            try:
                if hasattr(self.app_state, 'order_manager') and self.app_state.order_manager:
                    # Cache account data
                    if hasattr(self.app_state.order_manager, 'connector'):
                        connector = self.app_state.order_manager.connector
                        if connector:
                            account_data = await connector.get_account_details()
                            if account_data:
                                await cache_manager.set("account_data", account_data, ttl=60)
                            
                            # Cache indices data
                            indices = {}
                            symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
                            for symbol in symbols:
                                try:
                                    quote_data = await connector.get_quote(symbol)
                                    if quote_data and quote_data.get('ltp', 0) > 0:
                                        indices[symbol] = {
                                            "price": float(quote_data.get('ltp', 0)),
                                            "change": float(quote_data.get('change', 0)),
                                            "changePercent": float(quote_data.get('pChange', 0))
                                        }
                                except Exception as e:
                                    logger.warning(f"Failed to get quote for {symbol}: {e}")
                            
                            if indices:
                                await cache_manager.set("indices_data", indices, ttl=30)
                    
                    # Cache positions data
                    positions = self.app_state.order_manager.get_open_positions()
                    await cache_manager.set("positions_data", positions, ttl=5)
                
                await asyncio.sleep(10)  # Sync every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Data sync error: {e}")
                await asyncio.sleep(10)
                
    async def _options_chain_calculator(self):
        """Calculate options chain data in background"""
        while self.running:
            try:
                # Get current spot prices from cache
                indices_data = await cache_manager.get("indices_data")
                
                if indices_data:
                    for symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
                        if symbol in indices_data and 'price' in indices_data[symbol]:
                            spot_price = indices_data[symbol]['price']
                            options_chain = self._calculate_options_chain(symbol, spot_price)
                            await cache_manager.set(f"options_{symbol}", options_chain, ttl=30)
                            logger.info(f"Cached options chain for {symbol} with spot price {spot_price}")
                else:
                    # Fallback: calculate with default prices if no indices data
                    default_prices = {"NIFTY": 24500, "BANKNIFTY": 51000, "FINNIFTY": 23000}
                    for symbol, price in default_prices.items():
                        options_chain = self._calculate_options_chain(symbol, price)
                        await cache_manager.set(f"options_{symbol}", options_chain, ttl=30)
                        logger.info(f"Cached default options chain for {symbol}")
                
                await asyncio.sleep(15)  # Calculate every 15 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Options calculation error: {e}")
                await asyncio.sleep(15)
                
    def _calculate_options_chain(self, symbol: str, spot_price: float) -> list:
        """Calculate realistic options chain based on spot price"""
        if symbol == "BANKNIFTY":
            strike_interval = 100
        elif symbol == "FINNIFTY":
            strike_interval = 50
        else:  # NIFTY
            strike_interval = 50
        
        atm_strike = round(spot_price / strike_interval) * strike_interval
        strikes = [atm_strike + (i * strike_interval) for i in range(-5, 6)]
        
        options_data = []
        for i, strike in enumerate(strikes):
            distance_from_atm = abs(i - 5)
            
            # Calculate realistic option prices
            price_multiplier = 0.0025 if symbol == "BANKNIFTY" else 0.002
            min_premium = 8 if symbol == "BANKNIFTY" else 5
            
            if distance_from_atm == 0:  # ATM
                call_ltp = max(min_premium, spot_price * price_multiplier)
                put_ltp = max(min_premium, spot_price * price_multiplier)
            elif i < 5:  # ITM calls, OTM puts
                intrinsic_call = max(0, spot_price - strike)
                time_value_call = spot_price * (price_multiplier * 0.5)
                call_ltp = max(min_premium, intrinsic_call + time_value_call)
                put_ltp = max(min_premium, spot_price * price_multiplier * 0.5 * (distance_from_atm + 1))
            else:  # OTM calls, ITM puts
                call_ltp = max(min_premium, spot_price * price_multiplier * 0.5 * (distance_from_atm + 1))
                intrinsic_put = max(0, strike - spot_price)
                time_value_put = spot_price * (price_multiplier * 0.5)
                put_ltp = max(min_premium, intrinsic_put + time_value_put)
            
            # Volume and OI based on symbol
            if symbol == "BANKNIFTY":
                base_volume = 120000 - (distance_from_atm * 15000)
                base_oi = 200000 - (distance_from_atm * 25000)
            elif symbol == "NIFTY":
                base_volume = 90000 - (distance_from_atm * 12000)
                base_oi = 180000 - (distance_from_atm * 22000)
            else:  # FINNIFTY
                base_volume = 60000 - (distance_from_atm * 10000)
                base_oi = 120000 - (distance_from_atm * 15000)
            
            options_data.append({
                "strike": strike,
                "call": {
                    "ltp": round(call_ltp, 2),
                    "volume": max(5000, base_volume),
                    "oi": max(10000, base_oi),
                    "iv": round(15 + (distance_from_atm * 2.5), 1)
                },
                "put": {
                    "ltp": round(put_ltp, 2),
                    "volume": max(4000, base_volume - 5000),
                    "oi": max(8000, base_oi - 10000),
                    "iv": round(15 + (distance_from_atm * 2.5), 1)
                }
            })
        
        return options_data

# Global background task manager
background_task_manager = BackgroundTaskManager()