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
    supertrend_multiplier: float # Can be float
    atr_period: int

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
# By default, load the .env file.
# If a .env.test file exists, load that instead. This is useful for running tests
# without needing a real .env file with production secrets.
ENV_FILE = BASE_DIR / ".env"
TEST_ENV_FILE = BASE_DIR / ".env.test"

if TEST_ENV_FILE.is_file():
    print("Loading test environment from .env.test")
    load_dotenv(dotenv_path=TEST_ENV_FILE)
elif ENV_FILE.is_file():
    print("Loading production environment from .env")
    load_dotenv(dotenv_path=ENV_FILE)
else:
    print("Warning: No .env or .env.test file found. Loading from environment variables.")
    # If no file is found, Pydantic will still try to load from actual env vars.
    pass


def load_config(path: Path = CONFIG_FILE) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

# Load config from root directory
config_data = load_config()

# Load config from root directory and merge with environment variables
config_data = load_config()

# Pydantic will automatically use environment variables to override values in BaseSettings.
# The names are matched case-insensitively.
# e.g., ANGEL_API_KEY in the .env file will map to the api_key field.
settings = Settings(
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    client_id=os.getenv("CLIENT_ID"),
    password=os.getenv("PASSWORD"),
    totp_secret=os.getenv("TOTP_SECRET"),
    **config_data
)
