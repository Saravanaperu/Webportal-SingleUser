from app.core.config import settings
from app.core.logging import logger

class RiskManager:
    """
    Manages trading risk by enforcing rules on trades and daily loss.
    """
    def __init__(self, account_equity: float):
        logger.info(f"Initializing Risk Manager with equity: {account_equity:.2f}")
        self.initial_equity = account_equity
        self.equity = account_equity

        # Load risk settings from config
        self.risk_params = settings.risk
        self.max_daily_loss_value = self.equity * (self.risk_params.max_daily_loss_percent / 100)

        # State variables for daily stats
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_trading_stopped = False
        self.wins = 0
        self.losses = 0
        self.total_win_pnl = 0.0
        self.total_loss_pnl = 0.0

        logger.info(f"Max daily loss set to: -${self.max_daily_loss_value:.2f}")
        logger.info(f"Stop trading after {self.risk_params.consecutive_losses_stop} consecutive losses.")

    @property
    def total_trades(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.wins / self.total_trades) * 100

    @property
    def avg_win_pnl(self) -> float:
        if self.wins == 0:
            return 0.0
        return self.total_win_pnl / self.wins

    @property
    def avg_loss_pnl(self) -> float:
        if self.losses == 0:
            return 0.0
        return self.total_loss_pnl / self.losses

    async def stop_trading(self, reason: str):
        """Activates the kill switch to stop all new trading activity."""
        if not self.is_trading_stopped:
            self.is_trading_stopped = True
            logger.critical(f"STOPPING TRADING. Reason: {reason}")
            # A future await call could go here, e.g., for notifications.

    async def record_trade(self, pnl: float):
        """Updates daily P&L and all other statistics, then checks risk limits."""
        self.daily_pnl += pnl
        self.equity += pnl
        logger.info(f"Trade P&L: {pnl:.2f}, Daily P&L: {self.daily_pnl:.2f}, New Equity: {self.equity:.2f}")

        if pnl > 0:
            self.wins += 1
            self.total_win_pnl += pnl
            self.consecutive_losses = 0
        elif pnl < 0:
            self.losses += 1
            self.total_loss_pnl += pnl
            self.consecutive_losses += 1

        logger.info(f"Consecutive losses: {self.consecutive_losses}. Win/Loss: {self.wins}/{self.losses}.")

        if self.daily_pnl <= -self.max_daily_loss_value:
            await self.stop_trading(f"Max daily loss limit of ${self.max_daily_loss_value:.2f} reached.")
        if self.consecutive_losses >= self.risk_params.consecutive_losses_stop:
            await self.stop_trading(f"Max consecutive loss limit of {self.risk_params.consecutive_losses_stop} reached.")

    def calculate_position_size(self, entry_price: float, stop_loss_price: float, atr: float) -> int:
        """Calculates position size based on risk per trade, adjusted for volatility."""
        base_risk_per_trade = self.equity * (self.risk_params.risk_per_trade_percent / 100)

        volatility_percent = (atr / entry_price) * 100
        vol_adj_params = self.risk_params.volatility_adjustment

        risk_per_trade_value = base_risk_per_trade
        if volatility_percent > vol_adj_params.high_vol_threshold_percent:
            risk_per_trade_value *= vol_adj_params.risk_reduction_factor
            logger.info(f"High volatility detected ({volatility_percent:.2f}%). Reducing risk per trade to ${risk_per_trade_value:.2f}.")

        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 1e-9:
            logger.warning("Risk per share is zero. Cannot calculate position size.")
            return 0

        position_size = int(risk_per_trade_value / risk_per_share)
        logger.debug(f"Calculated position size: {position_size} for entry={entry_price}, sl={stop_loss_price}, atr={atr}")
        return position_size

    def can_place_trade(self) -> bool:
        """Checks if the system is in a state that allows placing new trades."""
        if self.is_trading_stopped:
            logger.warning("Trade blocked: Trading is currently stopped by Risk Manager.")
            return False
        return True
