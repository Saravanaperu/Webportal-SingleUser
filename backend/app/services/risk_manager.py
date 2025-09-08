from app.core.config import settings
from app.core.logging import logger

class RiskManager:
    """
    Manages trading risk by enforcing rules on trades and daily loss.
    """
    def __init__(self, account_equity: float):
        logger.info(f"Initializing Risk Manager with equity: {account_equity:.2f}")
        self.equity = account_equity

        # Load risk settings from config
        self.risk_per_trade_percent = settings.risk.risk_per_trade_percent
        self.max_daily_loss_percent = settings.risk.max_daily_loss_percent
        self.max_daily_loss_value = self.equity * (self.max_daily_loss_percent / 100)
        self.consecutive_losses_stop = settings.risk.consecutive_losses_stop

        # State variables
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_trading_stopped = False

        logger.info(f"Max daily loss set to: -${self.max_daily_loss_value:.2f}")
        logger.info(f"Stop trading after {self.consecutive_losses_stop} consecutive losses.")

    def stop_trading(self, reason: str):
        """Activates the kill switch to stop all new trading activity."""
        if not self.is_trading_stopped:
            self.is_trading_stopped = True
            logger.critical(f"STOPPING TRADING. Reason: {reason}")

    def record_trade(self, pnl: float):
        """Records the P&L of a completed trade and checks risk limits."""
        self.daily_pnl += pnl
        logger.info(f"Trade P&L: {pnl:.2f}, Daily P&L: {self.daily_pnl:.2f}")

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        logger.info(f"Consecutive losses: {self.consecutive_losses}")

        if self.daily_pnl <= -self.max_daily_loss_value:
            self.stop_trading(f"Max daily loss limit of ${self.max_daily_loss_value:.2f} reached.")

        if self.consecutive_losses >= self.consecutive_losses_stop:
            self.stop_trading(f"Max consecutive loss limit of {self.consecutive_losses_stop} reached.")

    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Calculates position size. For options, this is simplified to a fixed
        number of lots. For equities, it's based on risk per trade.
        """
        # A simple way to distinguish options from equities is by the nature of the signal.
        # For now, we'll assume any signal with a very high entry price is not an option
        # and revert to the old logic. A more robust way would be to pass the instrument type.
        if entry_price > 1000: # Assuming options premium are less than 1000
            risk_per_trade_value = self.equity * (self.risk_per_trade_percent / 100)
            risk_per_share = abs(entry_price - stop_loss_price)

            if risk_per_share <= 1e-9:
                return 0

            position_size = int(risk_per_trade_value / risk_per_share)
            logger.debug(f"Calculated equity position size: {position_size}")
            return position_size
        else:
            # For options, we'll use a fixed size of 1 lot for simplicity.
            # The lot size itself is part of the instrument data, but we'll assume a quantity.
            # Nifty lot size is 50, BankNifty is 15. We'll use a placeholder quantity of 1 for now.
            # The actual quantity will be determined by the lot size of the instrument.
            # For now, we'll return a quantity of 1 (which will be interpreted as 1 lot).
            logger.debug("Using fixed lot size for options trade.")
            return 1 # Placeholder for 1 lot

    def can_place_trade(self) -> bool:
        """Checks if the system is in a state that allows placing new trades."""
        if self.is_trading_stopped:
            logger.warning("Trade blocked: Trading is currently stopped by Risk Manager.")
            return False
        return True
