import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.services.order_manager import OrderManager
from app.models.trading import Order

# Mock dependencies
@pytest.fixture
def mock_connector():
    return MagicMock()

@pytest.fixture
def mock_risk_manager():
    return MagicMock()

@pytest.fixture
def mock_instrument_manager():
    return MagicMock()

@pytest.fixture
def mock_db():
    """Mocks the database session object."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    return db

@pytest.fixture
def order_manager(mock_connector, mock_risk_manager, mock_instrument_manager, mock_db):
    """Returns an OrderManager instance with mocked dependencies, including the DB."""
    return OrderManager(
        connector=mock_connector,
        risk_manager=mock_risk_manager,
        instrument_manager=mock_instrument_manager,
        db=mock_db
    )

@pytest.mark.asyncio
async def test_handle_order_update_full_fill(order_manager, mock_db):
    """
    Tests the existing case of a single, complete fill for an order.
    """
    # Arrange
    broker_order_id = "BROKER_ID_123"
    internal_order_id = 1
    order_manager.active_orders[broker_order_id] = internal_order_id

    mock_order = MagicMock()
    mock_order.symbol = "TEST-EQ"
    mock_order.side = "BUY"
    mock_order.qty = 100
    mock_order.sl = 95.0
    mock_order.tp = 105.0
    mock_order.atr_at_entry = 1.0
    mock_db.fetch_one.return_value = mock_order

    # Act
    update = {
        "orderid": broker_order_id,
        "status": "COMPLETE",
        "averageprice": "100.50",
        "filledshares": "100"
    }
    await order_manager.handle_order_update(update)

    # Assert
    assert "TEST-EQ" in order_manager.open_positions
    position = order_manager.open_positions["TEST-EQ"]
    assert position['qty'] == 100
    assert position['entry_price'] == 100.50
    assert broker_order_id not in order_manager.active_orders
    # Assert that a trade record was created
    assert mock_db.execute.call_count >= 2 # 1 for status update, 1 for trade creation


@pytest.mark.asyncio
async def test_handle_order_update_partial_fills(order_manager, mock_db):
    """
    Tests the new case of handling an order that is filled in multiple parts.
    This test will fail until the logic is implemented.
    """
    # Arrange
    broker_order_id = "BROKER_ID_456"
    internal_order_id = 2
    order_manager.active_orders[broker_order_id] = internal_order_id

    mock_order = MagicMock()
    mock_order.symbol = "TEST-PARTIAL-EQ"
    mock_order.side = "BUY"
    mock_order.qty = 100
    mock_order.sl = 95.0
    mock_order.tp = 110.0
    mock_order.atr_at_entry = 1.0
    mock_db.fetch_one.return_value = mock_order

    # --- Act 1: First partial fill ---
    update1 = {
        "orderid": broker_order_id,
        "status": "PARTIALLY FILLED",
        "averageprice": "100.00",
        "filledshares": "40"
    }
    await order_manager.handle_order_update(update1)

    # --- Assert 1: This part should fail initially ---
    assert "TEST-PARTIAL-EQ" in order_manager.open_positions
    position1 = order_manager.open_positions["TEST-PARTIAL-EQ"]
    assert position1['qty'] == 40
    assert position1['entry_price'] == 100.00
    assert broker_order_id in order_manager.active_orders

    # --- Act 2: Second and final fill ---
    update2 = {
        "orderid": broker_order_id,
        "status": "COMPLETE",
        "averageprice": "100.60",
        "filledshares": "100" # Broker sends total filled
    }
    await order_manager.handle_order_update(update2)

    # --- Assert 2: This part should also fail initially ---
    position2 = order_manager.open_positions["TEST-PARTIAL-EQ"]
    assert position2['qty'] == 100
    # Expected avg price = (40 * 100.00 + 60 * 101.00) / 100 = 100.60
    # The final average price is provided by the broker in the last update
    assert position2['entry_price'] == pytest.approx(100.60)
    assert broker_order_id not in order_manager.active_orders
    assert mock_db.execute.call_count >= 4 # 2 status updates, 2 trade creations
