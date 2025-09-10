from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from ..db.base import Base

class Candle(Base):
    __tablename__ = "candles"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    ts = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    ts = Column(DateTime)
    side = Column(String) # 'BUY' or 'SELL'
    entry = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    reason = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    broker_order_id = Column(String, unique=True, index=True, nullable=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String)
    side = Column(String)
    qty = Column(Integer)
    price = Column(Float, nullable=True)
    status = Column(String)
    reason = Column(String, nullable=True)
    ts = Column(DateTime)
    # Options-specific fields
    sl = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    atr_at_entry = Column(Float, nullable=True)
    confidence = Column(Integer, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    fill_price = Column(Float)
    qty = Column(Integer)
    ts = Column(DateTime)

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    qty = Column(Integer)
    avg_price = Column(Float)
    pnl = Column(Float, default=0.0)
    ts = Column(DateTime) # Last updated timestamp

class HistoricalTrade(Base):
    __tablename__ = "historical_trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)
    qty = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float)
    pnl = Column(Float)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    # Options-specific fields
    holding_time_minutes = Column(Float, nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    option_type = Column(String, nullable=True)  # CE or PE
    strike_price = Column(Float, nullable=True)
    underlying_price_entry = Column(Float, nullable=True)
    underlying_price_exit = Column(Float, nullable=True)
