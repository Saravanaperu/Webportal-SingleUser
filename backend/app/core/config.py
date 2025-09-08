import yaml
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class StrategyConfig(BaseModel):
    instruments: list[str]
    timeframe: str
    ema_short: int
    ema_long: int
    supertrend_period: int
    supertrend_multiplier: float # Can be float
    atr_period: int

class RiskConfig(BaseModel):
    risk_per_trade_percent: float
    max_daily_loss_percent: float
    consecutive_losses_stop: int
    trailing_stop: dict
    take_profit_atr: float

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

def load_config(path: str = "config.yaml") -> dict:
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
