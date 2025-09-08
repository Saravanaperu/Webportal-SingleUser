import pyotp
from app.core.logging import logger
from SmartApi import SmartConnect

class AngelAuth:
    """
    Handles the authentication flow with AngelOne using the smartapi-python library.
    """
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.feed_token = None

    def login(self) -> dict | None:
        """
        Performs the login flow to get session tokens.
        """
        logger.info("Attempting to log in to AngelOne...")
        try:
            totp = pyotp.TOTP(self.totp_secret).now()
            login_data = self.smart_api.generateSession(self.client_id, self.password, totp)

            if login_data.get("status") and login_data.get("data"):
                data = login_data["data"]
                self.feed_token = self.smart_api.getfeedToken()

                logger.info("AngelOne login successful.")
                return {
                    "jwt_token": data.get("jwtToken"),
                    "refresh_token": data.get("refreshToken"),
                    "feed_token": self.feed_token,
                }
            else:
                error_message = login_data.get("message", "Unknown error during login.")
                logger.error(f"AngelOne login failed: {error_message}")
                return None

        except Exception as e:
            logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
            return None

    def refresh_session(self, refresh_token: str) -> str | None:
        """
        Refreshes the session using the refresh token.
        """
        logger.info("Refreshing AngelOne session...")
        try:
            # The smart_api object should be instantiated for this call.
            # The generateToken method refreshes the token and updates it internally.
            response = self.smart_api.generateToken(refresh_token)

            if response.get("status") and response.get("data"):
                new_jwt_token = response["data"]["jwtToken"]
                # Update the internal state of the smart_api object with the new token
                self.smart_api.set_access_token(new_jwt_token)
                logger.info("AngelOne session refreshed successfully.")
                return new_jwt_token
            else:
                error_message = response.get("message", "Unknown error during token refresh.")
                logger.error(f"Failed to refresh AngelOne session: {error_message}")
                return None

        except Exception as e:
            logger.error(f"An error occurred during session refresh: {e}", exc_info=True)
            return None

    def get_smart_api_instance(self) -> SmartConnect:
        """Returns the authenticated SmartConnect instance."""
        return self.smart_api
