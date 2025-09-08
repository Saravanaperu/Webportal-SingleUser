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

    def update_pnl(self, pnl: float):
        """Updates daily P&L and checks if any risk limits have been breached."""
        self.daily_pnl += pnl
        logger.info(f"Trade P&L: {pnl:.2f}, Daily P&L: {self.daily_pnl:.2f}")

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            # Reset on a winning trade
            self.consecutive_losses = 0

        logger.info(f"Consecutive losses: {self.consecutive_losses}")

        if self.daily_pnl <= -self.max_daily_loss_value:
            self.stop_trading(f"Max daily loss limit of ${self.max_daily_loss_value:.2f} reached.")

        if self.consecutive_losses >= self.consecutive_losses_stop:
            self.stop_trading(f"Max consecutive loss limit of {self.consecutive_losses_stop} reached.")

    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> int:
        """Calculates position size based on the risk per trade percentage."""
        risk_per_trade_value = self.equity * (self.risk_per_trade_percent / 100)
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 1e-9: # Avoid division by zero
            logger.warning("Risk per share is zero. Cannot calculate position size.")
            return 0

        position_size = int(risk_per_trade_value / risk_per_share)
        logger.debug(f"Calculated position size: {position_size} for entry={entry_price}, sl={stop_loss_price}")
        return position_size

    def can_place_trade(self) -> bool:
        """Checks if the system is in a state that allows placing new trades."""
        if self.is_trading_stopped:
            logger.warning("Trade blocked: Trading is currently stopped by Risk Manager.")
            return False
        return True
