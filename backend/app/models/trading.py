from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.db.base import Base

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
    price = Column(Float, nullable=True) # For limit orders
    status = Column(String) # e.g., 'PENDING', 'FILLED', 'CANCELLED'
    ts = Column(DateTime)

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
    side = Column(String) # 'BUY' or 'SELL'
    qty = Column(Integer)
    avg_price = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    trailing_sl = Column(Float, nullable=True)
    highest_price_seen = Column(Float, nullable=True)
    status = Column(String, default="OPEN") # 'OPEN' or 'CLOSED'
    pnl = Column(Float, default=0.0)
    entry_ts = Column(DateTime)
    exit_ts = Column(DateTime, nullable=True)
