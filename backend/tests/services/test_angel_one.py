import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.angel_one import AngelOneConnector

@pytest.fixture
def mock_auth_client():
    """Mocks the AngelAuth client."""
    auth = MagicMock()
    # Simulate a successful login response
    auth.login.return_value = {
        "jwt_token": "new_jwt",
        "refresh_token": "new_refresh",
        "feed_token": "new_feed"
    }
    auth.get_smart_api_instance.return_value = MagicMock()
    return auth

@pytest.mark.asyncio
@patch('app.services.angel_one.AngelAuth')
async def test_reconnect_method(MockAngelAuth, mock_auth_client):
    """
    Tests that the reconnect method calls the login flow and re-initializes clients.
    """
    # Arrange
    # Patch the AngelAuth class to return our mock instance
    MockAngelAuth.return_value = mock_auth_client

    connector = AngelOneConnector()

    # --- Pre-condition checks ---
    assert connector.rest_client is None
    assert connector.ws_client is None

    # Act
    is_success = await connector.reconnect()

    # Assert
    assert is_success is True

    # Check that the login method was called
    mock_auth_client.login.assert_called_once()

    # Check that new tokens were stored
    assert connector.jwt_token == "new_jwt"
    assert connector.feed_token == "new_feed"

    # Check that clients were re-initialized
    assert connector.rest_client is not None
    assert connector.ws_client is not None
    assert connector.ws_client.auth_token == "new_jwt"
    assert connector.ws_client.feed_token == "new_feed"
