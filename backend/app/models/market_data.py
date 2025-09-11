from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TickData(Base):
    __tablename__ = "tick_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    token = Column(String, index=True)
    ltp = Column(Float)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Index for fast queries
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )

class OptionsData(Base):
    __tablename__ = "options_data"
    
    id = Column(Integer, primary_key=True, index=True)
    underlying = Column(String, index=True)
    strike = Column(Float, index=True)
    option_type = Column(String)  # CE or PE
    ltp = Column(Float)
    volume = Column(Integer)
    oi = Column(Integer)
    iv = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_underlying_strike_type', 'underlying', 'strike', 'option_type'),
    )