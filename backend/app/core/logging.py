import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / "trading.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("trading_portal")

# --- Specific Logger for WebSocket Broadcasts ---
# This helps in debugging what is being sent to the frontend without cluttering the main log.
ws_broadcast_handler = logging.FileHandler(logs_dir / "ws_broadcast.log")
ws_broadcast_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

ws_broadcast_logger = logging.getLogger("ws_broadcast")
ws_broadcast_logger.setLevel(logging.INFO)
ws_broadcast_logger.addHandler(ws_broadcast_handler)
ws_broadcast_logger.propagate = False # Prevent messages from appearing in the main log