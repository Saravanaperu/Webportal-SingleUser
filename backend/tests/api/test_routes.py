import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.core.config import StrategyConfig

# Mock the services that the API endpoints depend on
@pytest.fixture
def mock_app_state():
    """Mocks the app.state for injecting dependencies into the API."""
    mock_strategy = MagicMock()
    mock_strategy.params = StrategyConfig(
        instruments=["TEST-EQ"],
        timeframe="1m",
        ema_short=9,
        ema_long=21,
        supertrend_period=10,
        supertrend_multiplier=3.0,
        atr_period=10
    )

    mock_risk_manager = MagicMock()
    mock_risk_manager.daily_pnl = 123.45
    mock_risk_manager.consecutive_losses = 1
    mock_risk_manager.is_trading_stopped = False

    app.state.strategy = mock_strategy
    app.state.risk_manager = mock_risk_manager
    yield
    # Teardown: remove mocked state
    del app.state.strategy
    del app.state.risk_manager


@pytest.mark.asyncio
async def test_get_stats_endpoint(mock_app_state):
    """
    Tests the GET /api/stats endpoint.
    """
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["pnl"] == 123.45
    assert data["consecutive_losses"] == 1
    assert data["is_trading_stopped"] is False

@pytest.mark.asyncio
async def test_get_strategy_parameters_endpoint(mock_app_state):
    """
    Tests the GET /api/strategy/parameters endpoint.
    """
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/strategy/parameters")

    assert response.status_code == 200
    data = response.json()
    assert data["ema_short"] == 9
    assert data["supertrend_multiplier"] == 3.0

@pytest.mark.asyncio
async def test_set_strategy_parameters_endpoint(mock_app_state):
    """
    Tests the POST /api/strategy/parameters endpoint.
    """
    new_params = {
        "instruments": ["TEST-EQ"],
        "timeframe": "1m",
        "ema_short": 10,
        "ema_long": 22,
        "supertrend_period": 11,
        "supertrend_multiplier": 3.5,
        "atr_period": 11
    }

    # Mock the update_parameters method on the strategy mock
    app.state.strategy.update_parameters = MagicMock()

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/strategy/parameters", json=new_params)

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Assert that the method on the mock object was called with the correct data
    app.state.strategy.update_parameters.assert_called_once()
    called_with_params = app.state.strategy.update_parameters.call_args[0][0]
    assert isinstance(called_with_params, StrategyConfig)
    assert called_with_params.ema_short == 10
    assert called_with_params.supertrend_multiplier == 3.5
