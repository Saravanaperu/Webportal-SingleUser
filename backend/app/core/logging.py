import sys
from loguru import logger

import os
from pathlib import Path

# The log file path is now absolute, based on the project's root directory.
# This ensures that logs are written to the correct location regardless of
# where the application is run from.
BASE_DIR = Path(__file__).resolve().parents[3]
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
log_file_path = LOG_DIR / "trading_portal.log"

logger.remove()
# Add a console logger.
logger.add(sys.stderr, level="INFO")
# Add a file logger.
logger.add(log_file_path, rotation="10 MB", compression="zip", level="DEBUG", enqueue=True, backtrace=True, diagnose=True)

# Example usage:
# from app.core.logging import logger
# logger.info("This is an info message")
# logger.debug("This is a debug message")
