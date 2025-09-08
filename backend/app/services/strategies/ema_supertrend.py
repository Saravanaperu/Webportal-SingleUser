import pandas as pd
import pandas_ta as ta
from app.services.strategies.base import Strategy

class EMACrossoverSupertrendStrategy(Strategy):
    """
    A strategy that uses EMA crossover, VWAP, and Supertrend to generate trading signals.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Specific parameters for this strategy, with defaults
        self.ema_short = int(self.params.get("ema_short", 9))
        self.ema_long = int(self.params.get("ema_long", 21))
        self.supertrend_period = int(self.params.get("supertrend_period", 10))
        self.supertrend_multiplier = float(self.params.get("supertrend_multiplier", 3.0))

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates EMA, VWAP, and Supertrend indicators.
        """
        if df.empty:
            return df

        df.ta.ema(length=self.ema_short, append=True, col_names=(f'EMA_{self.ema_short}',))
        df.ta.ema(length=self.ema_long, append=True, col_names=(f'EMA_{self.ema_long}',))
        df.ta.vwap(append=True, col_names=('VWAP',))
        df.ta.supertrend(period=self.supertrend_period,
                         multiplier=self.supertrend_multiplier,
                         append=True,
                         col_names=('SUPERT', 'SUPERTd', 'SUPERTl', 'SUPERTs'))
        return df

    def generate_signal(self, df: pd.DataFrame) -> str:
        """
        Generates a signal based on the EMA crossover, VWAP, and Supertrend.
        """
        if df.empty or len(df) < self.ema_long:
            return "HOLD"

        latest = df.iloc[-1]

        # Ensure all required indicators are present and not NaN
        required_cols = [f'EMA_{self.ema_short}', f'EMA_{self.ema_long}', 'VWAP', 'SUPERTd']
        if latest.get(required_cols) is None or latest[required_cols].hasnans:
            return "HOLD"

        # Bullish entry conditions
        is_bullish = (latest[f'EMA_{self.ema_short}'] > latest[f'EMA_{self.ema_long}'] and
                      latest['close'] > latest['VWAP'] and
                      latest['SUPERTd'] == 1)

        # Bearish entry conditions
        is_bearish = (latest[f'EMA_{self.ema_short}'] < latest[f'EMA_{self.ema_long}'] and
                      latest['close'] < latest['VWAP'] and
                      latest['SUPERTd'] == -1)

        if is_bullish:
            return "BUY"
        elif is_bearish:
            return "SELL"
        else:
            return "HOLD"
