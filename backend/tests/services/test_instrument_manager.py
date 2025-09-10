import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.instrument_manager import InstrumentManager
from app.core.config import settings

# A diverse list of mock instruments to test all filtering scenarios
MOCK_INSTRUMENTS = [
    # 1. Valid NIFTY Future (should be included)
    {"token": "1001", "symbol": "NIFTY24SEPFUT", "name": "NIFTY", "expiry": "26SEP2024", "instrumenttype": "FUTIDX", "exch_seg": "NFO"},
    # 2. Valid BANKNIFTY Option (should be included)
    {"token": "2001", "symbol": "BANKNIFTY24SEP1250000CE", "name": "BANKNIFTY", "expiry": "12SEP2024", "instrumenttype": "OPTIDX", "exch_seg": "NFO"},
    # 3. Valid SENSEX Option (should be included)
    {"token": "3001", "symbol": "SENSEX24SEP72000PE", "name": "SENSEX", "expiry": "20SEP2024", "instrumenttype": "OPTIDX", "exch_seg": "NFO"},

    # --- Cases that should be filtered out ---
    # 4. Expired Contract
    {"token": "4001", "symbol": "NIFTY24JANFUT", "name": "NIFTY", "expiry": "25JAN2024", "instrumenttype": "FUTIDX", "exch_seg": "NFO"},
    # 5. Far-month Contract (well outside the 45-day test window)
    {"token": "5001", "symbol": "NIFTY25DECFUT", "name": "NIFTY", "expiry": "25DEC2025", "instrumenttype": "FUTIDX", "exch_seg": "NFO"},
    # 6. Wrong Index (FINNIFTY)
    {"token": "6001", "symbol": "FINNIFTY24SEPFUT", "name": "FINNIFTY", "expiry": "24SEP2024", "instrumenttype": "FUTIDX", "exch_seg": "NFO"},
    # 7. Wrong Exchange (Equity)
    {"token": "7001", "symbol": "RELIANCE-EQ", "name": "RELIANCE", "expiry": "", "instrumenttype": "STK", "exch_seg": "NSE"},
    # 8. Wrong Instrument Type (Commodity Future)
    {"token": "8001", "symbol": "GOLDPETAL24SEPFUT", "name": "GOLDPETAL", "expiry": "28AUG2024", "instrumenttype": "FUTCOM", "exch_seg": "MCX"},
    # 9. No expiry date
    {"token": "9001", "symbol": "CORRUPT", "name": "NIFTY", "expiry": "", "instrumenttype": "FUTIDX", "exch_seg": "NFO"},
]

@pytest.fixture
def mock_rest_client():
    """Fixture to create a mock REST client with a predefined instrument list."""
    client = MagicMock()
    client.get_instrument_list = AsyncMock(return_value=MOCK_INSTRUMENTS)
    return client

@pytest.mark.asyncio
async def test_load_instruments_filters_correctly(mock_rest_client):
    """
    Verify that the InstrumentManager correctly filters the raw instrument list
    based on the configuration for indices, instrument types, and expiry.
    """
    # Arrange
    # Override config to match our test case
    settings.strategy.trade_indices = ["NIFTY", "BANKNIFTY", "SENSEX"]
    settings.strategy.instrument_types = ["FUTIDX", "OPTIDX"]

    manager = InstrumentManager()

    # We patch datetime to control the "current" date for expiry filtering tests
    with patch('app.services.instrument_manager.datetime') as mock_datetime:
        # Set a fixed "today" for deterministic testing
        mock_datetime.now.return_value = datetime(2024, 8, 20)
        # The method uses strptime, so we need to make sure the real one is used
        mock_datetime.strptime = datetime.strptime

        # Act
        await manager.load_instruments(mock_rest_client)

    # Assert
    # Check that the final list contains only the 3 valid, near-term instruments
    assert len(manager.instruments) == 3

    final_symbols = {inst['symbol'] for inst in manager.instruments}
    expected_symbols = {
        "NIFTY24SEPFUT",
        "BANKNIFTY24SEP1250000CE",
        "SENSEX24SEP72000PE"
    }
    assert final_symbols == expected_symbols

    # Check that the symbol-to-token map is also built correctly from the filtered list
    assert manager.get_token("NIFTY24SEPFUT") == "1001"
    assert manager.get_token("BANKNIFTY24SEP1250000CE") == "2001"
    assert manager.get_token("SENSEX24SEP72000PE") == "3001"

    # Check that various filtered-out instruments are not in the map
    assert manager.get_token("NIFTY24JANFUT") is None  # Expired
    assert manager.get_token("NIFTY25DECFUT") is None  # Far-month
    assert manager.get_token("FINNIFTY24SEPFUT") is None # Wrong index
    assert manager.get_token("RELIANCE-EQ") is None # Wrong exchange/type
