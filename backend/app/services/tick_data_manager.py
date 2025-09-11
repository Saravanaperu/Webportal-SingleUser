import asyncio
from datetime import datetime, time
from sqlalchemy import select, desc
from ..db.session import database
from ..models.market_data import TickData, OptionsData
from ..core.logging import logger

class TickDataManager:
    def __init__(self):
        self.subscribed_symbols = []
        self.market_hours = {
            'start': time(9, 15),  # 9:15 AM
            'end': time(15, 30)    # 3:30 PM
        }
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        now = datetime.now().time()
        return self.market_hours['start'] <= now <= self.market_hours['end']
    
    async def store_tick_data(self, tick_data: dict):
        """Store tick data in database"""
        if not self.is_market_hours():
            return
            
        try:
            query = TickData.__table__.insert().values(
                symbol=tick_data.get('symbol'),
                token=tick_data.get('token'),
                ltp=float(tick_data.get('ltp', 0)),
                change=float(tick_data.get('change', 0)),
                change_percent=float(tick_data.get('change_percent', 0)),
                volume=int(tick_data.get('volume', 0)),
                timestamp=datetime.utcnow()
            )
            await database.execute(query)
        except Exception as e:
            logger.error(f"Error storing tick data: {e}")
    
    async def get_latest_ltp(self, symbol: str) -> dict:
        """Get latest LTP from database"""
        try:
            query = select(TickData).where(
                TickData.symbol == symbol
            ).order_by(desc(TickData.timestamp)).limit(1)
            
            result = await database.fetch_one(query)
            if result:
                return {
                    'symbol': result.symbol,
                    'ltp': result.ltp,
                    'change': result.change,
                    'change_percent': result.change_percent,
                    'volume': result.volume,
                    'timestamp': result.timestamp
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching latest LTP for {symbol}: {e}")
            return None
    
    async def store_options_data(self, options_data: dict):
        """Store options data in database"""
        if not self.is_market_hours():
            return
            
        try:
            query = OptionsData.__table__.insert().values(
                underlying=options_data.get('underlying'),
                strike=float(options_data.get('strike')),
                option_type=options_data.get('option_type'),
                ltp=float(options_data.get('ltp', 0)),
                volume=int(options_data.get('volume', 0)),
                oi=int(options_data.get('oi', 0)),
                iv=float(options_data.get('iv', 0)),
                timestamp=datetime.utcnow()
            )
            await database.execute(query)
        except Exception as e:
            logger.error(f"Error storing options data: {e}")
    
    async def get_options_chain_from_db(self, underlying: str) -> list:
        """Get options chain from database"""
        try:
            # Get latest options data for the underlying
            query = select(OptionsData).where(
                OptionsData.underlying == underlying
            ).order_by(desc(OptionsData.timestamp))
            
            results = await database.fetch_all(query)
            
            # Group by strike and option type
            options_dict = {}
            for row in results:
                strike = row.strike
                if strike not in options_dict:
                    options_dict[strike] = {'strike': strike, 'call': {}, 'put': {}}
                
                option_data = {
                    'ltp': row.ltp,
                    'volume': row.volume,
                    'oi': row.oi,
                    'iv': row.iv
                }
                
                if row.option_type == 'CE':
                    options_dict[strike]['call'] = option_data
                elif row.option_type == 'PE':
                    options_dict[strike]['put'] = option_data
            
            # Convert to list and sort by strike
            options_list = list(options_dict.values())
            options_list.sort(key=lambda x: x['strike'])
            
            return options_list
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {underlying}: {e}")
            return []

# Global instance
tick_data_manager = TickDataManager()