import pytest
import pandas as pd
import numpy as np

# Mock necessary services for initializing TradingStrategy
class MockOrderManager:
    pass
class MockRiskManager:
    pass
class MockConnector:
    pass

# We need to import the real TradingStrategy to test its method
from app.services.strategy import TradingStrategy
from app.core.config import settings

@pytest.fixture
def sample_ohlc_data():
    """Creates a sample pandas DataFrame with OHLC data."""
    dates = pd.to_datetime(pd.date_range(end='2023-01-31', periods=50, freq='min'))
    price_data = 100 + np.random.randn(50).cumsum() * 0.2
    data = {
        'open': price_data - np.random.rand(50) * 0.1,
        'high': price_data + np.random.rand(50) * 0.1,
        'low': price_data - np.random.rand(50) * 0.1,
        'close': price_data,
        'volume': np.random.randint(1000, 5000, 50)
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def strategy_instance():
    """Returns a TradingStrategy instance with mocked dependencies."""
    return TradingStrategy(
        order_manager=MockOrderManager(),
        risk_manager=MockRiskManager(),
        connector=MockConnector()
    )

def test_calculate_indicators(strategy_instance, sample_ohlc_data):
    """
    Tests that the calculate_indicators method adds the correct columns.
    """
    df = sample_ohlc_data

    # Act
    df_with_indicators = strategy_instance.calculate_indicators(df)

    # Assert
    # Check that the original DataFrame is modified or a new one is returned
    assert df_with_indicators is not None

    # Check that all expected indicator columns have been added
    expected_columns = [
        f'EMA_{settings.strategy.ema_short}',
        f'EMA_{settings.strategy.ema_long}',
        'VWAP',
        'SUPERT',
        'SUPERTd',
        'SUPERTl',
        'SUPERTs',
        f'ATR_{settings.strategy.atr_period}'
    ]

    for col in expected_columns:
        assert col in df_with_indicators.columns

    # Check that the indicator values are not all NaN after a sufficient warm-up period
    # (The first few rows will be NaN, which is expected)
    long_period = max(settings.strategy.ema_long, settings.strategy.supertrend_period)
    for col in expected_columns:
        assert not df_with_indicators[col].iloc[long_period:].isnull().all()
