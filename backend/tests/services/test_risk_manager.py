import pytest
from app.services.risk_manager import RiskManager
from app.core.config import settings

# Use a fixed equity for predictable test results
TEST_EQUITY = 100000

@pytest.fixture
def risk_manager():
    """Returns a RiskManager instance with default settings for each test."""
    # Reset any potential singleton state by creating a new instance
    return RiskManager(account_equity=TEST_EQUITY)

def test_calculate_position_size_normal(risk_manager):
    """
    Test position size calculation under normal conditions.
    """
    risk_per_trade = TEST_EQUITY * (settings.risk.risk_per_trade_percent / 100)
    # e.g., 100,000 * (1/100) = 1000 risk per trade

    entry_price = 100
    sl_price = 98 # Risk per share = 2

    # Expected size = risk_per_trade / risk_per_share = 1000 / 2 = 500
    expected_size = risk_per_trade / (entry_price - sl_price)

    size = risk_manager.calculate_position_size(entry_price, sl_price)
    assert size == int(expected_size)

def test_calculate_position_size_zero_risk(risk_manager):
    """
    Test position size calculation when stop loss is at entry price (zero risk).
    It should return 0 to avoid division by zero errors.
    """
    size = risk_manager.calculate_position_size(entry_price=100, stop_loss_price=100)
    assert size == 0

def test_can_place_trade_initially(risk_manager):
    """
    Test that trading is allowed initially.
    """
    assert risk_manager.can_place_trade() is True

def test_can_place_trade_after_max_daily_loss(risk_manager):
    """
    Test that trading is stopped after the max daily loss is breached.
    """
    max_loss = TEST_EQUITY * (settings.risk.max_daily_loss_percent / 100)

    risk_manager.record_trade(pnl=-(max_loss + 1))

    assert risk_manager.is_trading_stopped is True
    assert risk_manager.can_place_trade() is False

def test_can_place_trade_after_consecutive_losses(risk_manager):
    """
    Test that trading is stopped after max consecutive losses are hit.
    """
    for _ in range(settings.risk.consecutive_losses_stop):
        risk_manager.record_trade(pnl=-100) # Record a losing trade

    assert risk_manager.is_trading_stopped is True
    assert risk_manager.can_place_trade() is False

def test_pnl_and_consecutive_loss_reset_on_win(risk_manager):
    """
    Test that a winning trade resets the consecutive loss counter.
    """
    # Given a series of losses
    risk_manager.record_trade(pnl=-100)
    risk_manager.record_trade(pnl=-150)
    assert risk_manager.consecutive_losses == 2
    assert risk_manager.daily_pnl == -250

    # When a winning trade occurs
    risk_manager.record_trade(pnl=300)

    # Then the counter should reset and P&L should update
    assert risk_manager.consecutive_losses == 0
    assert risk_manager.daily_pnl == 50
