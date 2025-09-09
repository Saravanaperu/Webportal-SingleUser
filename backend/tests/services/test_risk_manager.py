import pytest
from app.services.risk_manager import RiskManager
from app.core.config import settings

# Use a fixed equity for predictable test results
TEST_EQUITY = 100000

@pytest.fixture
def risk_manager():
    """Returns a RiskManager instance with default settings for each test."""
    return RiskManager(account_equity=TEST_EQUITY)

def test_calculate_position_size_normal_volatility(risk_manager):
    """
    Test position size calculation under normal volatility conditions.
    """
    risk_per_trade = TEST_EQUITY * (settings.risk.risk_per_trade_percent / 100)
    entry_price = 100
    sl_price = 98
    atr = 2.0 # Volatility = (2.0 / 100) * 100 = 2.0%, which is > threshold

    # Expected size = (risk_per_trade * reduction_factor) / risk_per_share
    # (1000 * 0.5) / 2 = 250
    expected_size = (risk_per_trade * settings.risk.volatility_adjustment.risk_reduction_factor) / (entry_price - sl_price)

    size = risk_manager.calculate_position_size(entry_price, sl_price, atr)
    assert size == int(expected_size)

def test_calculate_position_size_low_volatility(risk_manager):
    """
    Test position size calculation when volatility is below the threshold.
    """
    risk_per_trade = TEST_EQUITY * (settings.risk.risk_per_trade_percent / 100)
    entry_price = 100
    sl_price = 99.8
    atr = 0.2 # Volatility = (0.2 / 100) * 100 = 0.2%, which is < threshold

    # Expected size = risk_per_trade / risk_per_share
    # 1000 / 0.2 = 5000
    expected_size = risk_per_trade / (entry_price - sl_price)

    size = risk_manager.calculate_position_size(entry_price, sl_price, atr)
    assert size == int(expected_size)

def test_calculate_position_size_zero_risk(risk_manager):
    """
    Test position size calculation when stop loss is at entry price (zero risk).
    """
    size = risk_manager.calculate_position_size(entry_price=100, stop_loss_price=100, atr=1.0)
    assert size == 0

def test_can_place_trade_initially(risk_manager):
    """Test that trading is allowed initially."""
    assert risk_manager.can_place_trade() is True

@pytest.mark.asyncio
async def test_can_place_trade_after_max_daily_loss(risk_manager):
    """Test that trading is stopped after the max daily loss is breached."""
    max_loss = TEST_EQUITY * (risk_manager.risk_params.max_daily_loss_percent / 100)
    await risk_manager.record_trade(pnl=-(max_loss + 1))
    assert risk_manager.is_trading_stopped is True
    assert risk_manager.can_place_trade() is False

@pytest.mark.asyncio
async def test_can_place_trade_after_consecutive_losses(risk_manager):
    """Test that trading is stopped after max consecutive losses are hit."""
    for _ in range(risk_manager.risk_params.consecutive_losses_stop):
        await risk_manager.record_trade(pnl=-100)
    assert risk_manager.is_trading_stopped is True
    assert risk_manager.can_place_trade() is False

@pytest.mark.asyncio
async def test_pnl_and_consecutive_loss_reset_on_win(risk_manager):
    """Test that a winning trade resets the consecutive loss counter."""
    await risk_manager.record_trade(pnl=-100)
    await risk_manager.record_trade(pnl=-150)
    assert risk_manager.consecutive_losses == 2
    assert risk_manager.daily_pnl == -250

    await risk_manager.record_trade(pnl=300)
    assert risk_manager.consecutive_losses == 0
    assert risk_manager.daily_pnl == 50
