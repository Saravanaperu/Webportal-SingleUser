import sys
from loguru import logger

# The log file path should be relative to where the app runs from.
# In the Docker container, the working directory is /app.
# The docker-compose file mounts a volume for logs at /app/logs.
log_file_path = "logs/trading_portal.log"

logger.remove()
# Add a console logger.
logger.add(sys.stderr, level="INFO")
# Add a file logger.
logger.add(log_file_path, rotation="10 MB", compression="zip", level="DEBUG", enqueue=True, backtrace=True, diagnose=True)

# Example usage:
# from app.core.logging import logger
# logger.info("This is an info message")
# logger.debug("This is a debug message")
