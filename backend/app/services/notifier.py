import os
import httpx
from app.core.logging import logger

class Notifier:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Notifier, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        self.is_configured = self.bot_token and self.chat_id
        if self.is_configured:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            logger.info("Telegram Notifier is configured.")
        else:
            logger.warning("Telegram Notifier is not configured. No notifications will be sent.")

        self._initialized = True

    async def send_message(self, message: str):
        """
        Sends a message to the configured Telegram chat.
        Fails silently if not configured.
        """
        if not self.is_configured:
            return

        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload)
                if response.status_code == 200:
                    logger.info(f"Sent notification to Telegram: '{message[:30]}...'")
                else:
                    logger.error(f"Failed to send Telegram notification. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Exception while sending Telegram notification: {e}", exc_info=True)

# Create a single instance of the notifier
notifier = Notifier()
