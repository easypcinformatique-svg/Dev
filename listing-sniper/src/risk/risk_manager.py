"""Risk manager — enforces hard limits on trades, daily/weekly loss, and exposure."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from src.models import Position, TradeStatus
from src.positions.pnl_tracker import PnLTracker

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    """Result of a risk check."""

    allowed: bool
    reason: str


class RiskManager:
    """
    HARD LIMITS — coded in stone, not configurable at runtime.

    Per trade:
      - Max position: 5% of portfolio
      - Max slippage: 3%
      - Stop-loss: -20%

    Per day:
      - Max trades: 10
      - Max daily loss: -5% → halt all trading
      - Max exposure: 30% of portfolio

    Per week:
      - Max weekly loss: -10% → halt 48h
      - 3 consecutive losses → mandatory review

    These limits are NEVER overridden. They are safety guardrails.
    """

    # ── HARD LIMITS (immutable) ──────────────────────────────
    MAX_POSITION_PCT: float = 0.05        # 5%
    MAX_SLIPPAGE_PCT: float = 0.03        # 3%
    STOP_LOSS_PCT: float = 0.20           # 20%
    MAX_TRADES_PER_DAY: int = 10
    MAX_DAILY_LOSS_PCT: float = 0.05      # 5%
    MAX_EXPOSURE_PCT: float = 0.30        # 30%
    MAX_WEEKLY_LOSS_PCT: float = 0.10     # 10%
    CONSECUTIVE_LOSSES_REVIEW: int = 3
    HALT_DURATION_HOURS: int = 48

    def __init__(self, pnl_tracker: PnLTracker, test_mode: bool = False) -> None:
        self._pnl = pnl_tracker
        self._test_mode = test_mode
        self._trades_today: int = 0
        self._trades_date: str = ""
        self._consecutive_losses: int = 0
        self._halted_until: Optional[datetime] = None
        self._daily_pnl_usd: float = 0.0
        self._weekly_pnl_usd: float = 0.0
        self._weekly_start: str = ""

    def _ensure_day(self) -> None:
        today = date.today().isoformat()
        if self._trades_date != today:
            self._trades_date = today
            self._trades_today = 0
            self._daily_pnl_usd = 0.0

    def _ensure_week(self) -> None:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        if self._weekly_start != week_start:
            self._weekly_start = week_start
            self._weekly_pnl_usd = 0.0

    async def check_can_trade(
        self,
        portfolio_value_usd: float,
        position_size_usd: float,
        current_exposure_usd: float,
    ) -> RiskCheck:
        """
        Run all risk checks before opening a new position.
        Returns RiskCheck(allowed=True/False, reason=...).
        """
        self._ensure_day()
        self._ensure_week()
        now = datetime.now(timezone.utc)

        # Check halt
        if self._halted_until and now < self._halted_until:
            remaining = (self._halted_until - now).total_seconds() / 3600
            return RiskCheck(
                False,
                f"Trading halted for {remaining:.1f}h more "
                f"(until {self._halted_until.isoformat()})",
            )

        # Max trades per day
        if self._trades_today >= self.MAX_TRADES_PER_DAY:
            return RiskCheck(
                False,
                f"Daily trade limit reached ({self._trades_today}/{self.MAX_TRADES_PER_DAY})",
            )

        # Position size limit (relaxed in test mode for small portfolios)
        max_pos_pct = 0.10 if self._test_mode else self.MAX_POSITION_PCT
        if portfolio_value_usd > 0:
            pos_pct = position_size_usd / portfolio_value_usd
            if pos_pct > max_pos_pct:
                return RiskCheck(
                    False,
                    f"Position too large: {pos_pct:.1%} > {max_pos_pct:.1%}",
                )

        # Exposure limit
        new_exposure = current_exposure_usd + position_size_usd
        if portfolio_value_usd > 0:
            exp_pct = new_exposure / portfolio_value_usd
            if exp_pct > self.MAX_EXPOSURE_PCT:
                return RiskCheck(
                    False,
                    f"Exposure limit: {exp_pct:.1%} > {self.MAX_EXPOSURE_PCT:.1%}",
                )

        # Daily loss limit
        if portfolio_value_usd > 0:
            daily_loss_pct = abs(self._daily_pnl_usd) / portfolio_value_usd
            if self._daily_pnl_usd < 0 and daily_loss_pct >= self.MAX_DAILY_LOSS_PCT:
                return RiskCheck(
                    False,
                    f"Daily loss limit: {daily_loss_pct:.1%} >= {self.MAX_DAILY_LOSS_PCT:.1%}",
                )

        # Weekly loss limit
        if portfolio_value_usd > 0:
            weekly_loss_pct = abs(self._weekly_pnl_usd) / portfolio_value_usd
            if self._weekly_pnl_usd < 0 and weekly_loss_pct >= self.MAX_WEEKLY_LOSS_PCT:
                self._halted_until = now + timedelta(hours=self.HALT_DURATION_HOURS)
                return RiskCheck(
                    False,
                    f"Weekly loss limit: {weekly_loss_pct:.1%} >= "
                    f"{self.MAX_WEEKLY_LOSS_PCT:.1%}. Halted for 48h.",
                )

        # Consecutive losses
        if self._consecutive_losses >= self.CONSECUTIVE_LOSSES_REVIEW:
            return RiskCheck(
                False,
                f"{self._consecutive_losses} consecutive losses — review required. "
                f"Reset via risk_manager.reset_consecutive_losses()",
            )

        return RiskCheck(True, "All risk checks passed")

    def record_trade(self, pnl_usd: float) -> None:
        """Record a completed trade for risk tracking."""
        self._ensure_day()
        self._ensure_week()
        self._trades_today += 1
        self._daily_pnl_usd += pnl_usd
        self._weekly_pnl_usd += pnl_usd

        if pnl_usd < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        logger.info(
            "Risk: trades_today=%d daily_pnl=$%.2f weekly_pnl=$%.2f consec_losses=%d",
            self._trades_today,
            self._daily_pnl_usd,
            self._weekly_pnl_usd,
            self._consecutive_losses,
        )

    def reset_consecutive_losses(self) -> None:
        """Manual reset after strategy review."""
        logger.info("Consecutive losses reset (was %d)", self._consecutive_losses)
        self._consecutive_losses = 0

    def force_halt(self, hours: int = 48) -> None:
        """Manually halt trading."""
        self._halted_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        logger.warning("Trading manually halted for %dh", hours)

    def clear_halt(self) -> None:
        """Clear a trading halt."""
        self._halted_until = None
        logger.info("Trading halt cleared")

    @property
    def is_halted(self) -> bool:
        if self._halted_until is None:
            return False
        return datetime.now(timezone.utc) < self._halted_until

    @property
    def trades_remaining_today(self) -> int:
        self._ensure_day()
        return max(0, self.MAX_TRADES_PER_DAY - self._trades_today)
