import pytest
from unittest.mock import MagicMock, patch

from app.services.order_manager import OrderManager
from app.services.risk_manager import RiskManager

# Since notifier is a singleton instance, we can patch it directly
@patch('app.services.order_manager.notifier', new_callable=MagicMock)
@pytest.mark.asyncio
async def test_order_manager_sends_notifications(mock_notifier):
    """
    Tests that OrderManager calls the notifier on open and close events.
    """
    # Arrange
    # We need to mock all dependencies of OrderManager
    mock_connector = MagicMock()
    mock_risk_manager = MagicMock()
    mock_instrument_manager = MagicMock()
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    order_manager = OrderManager(mock_connector, mock_risk_manager, mock_instrument_manager, db=mock_db)

    # Mock the return value for the database call
    mock_order = MagicMock()
    mock_order.symbol = "NOTIFY-TEST"
    mock_order.side = "BUY"
    mock_order.qty = 10
    mock_db.fetch_one.return_value = mock_order

    order_manager.active_orders["BROKER_ID_OPEN"] = 1

    # --- Test 1: Opening a position ---
    open_update = {
        "orderid": "BROKER_ID_OPEN",
        "status": "COMPLETE",
        "averageprice": "100.00",
        "filledshares": "10"
    }
    await order_manager.handle_order_update(open_update)

    # Assert
    mock_notifier.send_message.assert_called_once()
    call_args = mock_notifier.send_message.call_args[0][0]
    assert "New Trade Opened" in call_args
    assert "NOTIFY-TEST" in call_args

    # --- Test 2: Closing a position ---
    mock_notifier.reset_mock() # Reset mock for the next assertion

    order_manager.active_orders["BROKER_ID_CLOSE"] = 2
    close_update = {
        "orderid": "BROKER_ID_CLOSE",
        "status": "COMPLETE",
        "averageprice": "102.00",
        "filledshares": "10"
    }
    # A closing order has the opposite side of the position
    mock_order.side = "SELL"
    await order_manager.handle_order_update(close_update)

    # Assert
    mock_notifier.send_message.assert_called_once()
    call_args = mock_notifier.send_message.call_args[0][0]
    assert "Trade Closed" in call_args
    assert "P&L: $20.00" in call_args


@patch('app.services.risk_manager.notifier', new_callable=MagicMock)
@pytest.mark.asyncio
async def test_risk_manager_sends_notification(mock_notifier):
    """
    Tests that RiskManager calls the notifier when trading is stopped.
    """
    # Arrange
    risk_manager = RiskManager(account_equity=100000)

    # Act
    reason = "Test stop reason"
    await risk_manager.stop_trading(reason)

    # Assert
    mock_notifier.send_message.assert_called_once()
    call_args = mock_notifier.send_message.call_args[0][0]
    assert "STOPPING TRADING" in call_args
    assert reason in call_args
