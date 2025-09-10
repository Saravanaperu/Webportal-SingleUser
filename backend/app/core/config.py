import yaml
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path

class StrategyConfig(BaseModel):
    instruments: list[str]
    timeframe: str
    ema_short: int
    ema_long: int
    supertrend_period: int
    supertrend_multiplier: float
    atr_period: int
    # New scalping parameters
    min_confirmations: int = 7
    rsi_period: int = 7
    bb_period: int = 20
    stoch_k: int = 5
    stoch_d: int = 3
    volume_surge_threshold: float = 1.5
    min_volatility: float = 0.3
    max_volatility: float = 2.0

class VolatilityAdjustmentConfig(BaseModel):
    high_vol_threshold_percent: float
    risk_reduction_factor: float

class RiskConfig(BaseModel):
    risk_per_trade_percent: float
    max_daily_loss_percent: float
    consecutive_losses_stop: int
    trailing_stop: dict
    take_profit_atr: float
    volatility_adjustment: VolatilityAdjustmentConfig

class TradingConfig(BaseModel):
    hours: dict
    paper_trading: bool

class CooldownConfig(BaseModel):
    after_consecutive_losses_minutes: int

class Settings(BaseModel):
    # AngelOne Credentials
    api_key: str
    api_secret: str
    client_id: str
    password: str
    totp_secret: str

    # Config from YAML
    strategy: StrategyConfig
    risk: RiskConfig
    trading: TradingConfig
    cooldown: CooldownConfig

# --- Path Setup ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parents[3]
CONFIG_FILE = BASE_DIR / "config.yaml"

# --- Environment Loading ---
# This logic checks the ENV_STATE environment variable to decide which .env file to load.
# `test.sh` will set ENV_STATE=test, ensuring tests load the test configuration.
# `run.sh` will not set it, so it will load the production configuration.
ENV_STATE = os.getenv("ENV_STATE", "prod")

if ENV_STATE == "test":
    print("Loading test environment from .env.test")
    env_path = BASE_DIR / ".env.test"
    load_dotenv(dotenv_path=env_path)
else:
    print("Loading production environment from .env")
    env_path = BASE_DIR / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
    else:
        print("Warning: .env file not found. Loading from environment variables.")
        # If no file is found, Pydantic will still try to load from actual env vars.
        pass


def load_config(path: Path = CONFIG_FILE) -> dict:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        raise

# Load config from root directory
config_data = load_config()

# Load config from root directory and merge with environment variables
config_data = load_config()

# Pydantic will automatically use environment variables to override values in BaseSettings.
# The names are matched case-insensitively.
# e.g., ANGEL_API_KEY in the .env file will map to the api_key field.
# Validate required environment variables
required_env_vars = ["API_KEY", "API_SECRET", "CLIENT_ID", "PASSWORD", "TOTP_SECRET"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {missing_vars}")

settings = Settings(
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    client_id=os.getenv("CLIENT_ID"),
    password=os.getenv("PASSWORD"),
    totp_secret=os.getenv("TOTP_SECRET"),
    **config_data
)
