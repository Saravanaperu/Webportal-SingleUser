from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    def __init__(self, **kwargs):
        """
        Initializes the strategy with its parameters.
        Parameters are passed via kwargs from the config file.
        """
        self.params = kwargs
        # Example of setting a parameter with a default
        self.timeframe = self.params.get("timeframe", "1minute")
        pass

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all technical indicators required for the strategy.
        This method should be implemented by each concrete strategy.

        Args:
            df (pd.DataFrame): The input DataFrame with OHLCV data.

        Returns:
            pd.DataFrame: The DataFrame with appended indicator columns.
        """
        pass

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> str:
        """
        Generates a trading signal ('BUY', 'SELL', or 'HOLD') based on the indicator data.
        This method should be implemented by each concrete strategy.

        Args:
            df (pd.DataFrame): The DataFrame with OHLCV and indicator data.

        Returns:
            str: The trading signal, e.g., "BUY", "SELL", "HOLD".
        """
        pass
