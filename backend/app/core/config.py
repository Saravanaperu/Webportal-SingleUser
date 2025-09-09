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
ENV_FILE = BASE_DIR / ".env"

# Load environment variables from .env file in the project root
load_dotenv(dotenv_path=ENV_FILE)


def load_config(path: Path = CONFIG_FILE) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

# Load config from root directory
config_data = load_config()

settings = Settings(
    api_key=os.getenv("ANGEL_API_KEY"),
    api_secret=os.getenv("ANGEL_API_SECRET"),
    client_id=os.getenv("ANGEL_CLIENT_ID"),
    password=os.getenv("ANGEL_PASSWORD"),
    totp_secret=os.getenv("ANGEL_TOTP_SECRET"),
    **config_data
)
