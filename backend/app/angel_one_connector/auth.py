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
        self.is_authenticated = False

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
                self.is_authenticated = True

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
            # Sanitize error message to prevent credential exposure
            sanitized_error = str(e).replace(self.password, "***").replace(self.totp_secret, "***")
            logger.error(f"An unexpected error occurred during login: {sanitized_error}")
            self.is_authenticated = False
            return None

    def get_smart_api_instance(self) -> SmartConnect | None:
        """Returns the authenticated SmartConnect instance if login was successful."""
        if not self.is_authenticated:
            logger.warning("Attempted to get SmartConnect instance without authentication")
            return None
        return self.smart_api
    
    def is_logged_in(self) -> bool:
        """Check if user is currently authenticated."""
        return self.is_authenticated
