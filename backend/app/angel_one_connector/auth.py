import pyotp
from ..core.logging import logger
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

    def get_smart_api_instance(self) -> SmartConnect:
        """Returns the authenticated SmartConnect instance."""
        return self.smart_api
