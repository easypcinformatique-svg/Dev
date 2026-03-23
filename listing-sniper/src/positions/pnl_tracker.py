"""PnL tracker — real-time mark-to-market, daily metrics, and performance analytics."""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from src.infra.database import Database
from src.infra.redis_cache import RedisCache
from src.models import DailyPnL, Position

logger = logging.getLogger(__name__)


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    avg_hold_hours: float = 0.0
    best_trade_usd: float = 0.0
    worst_trade_usd: float = 0.0


class PnLTracker:
    """Real-time PnL tracking and performance analytics."""

    def __init__(self, db: Database, redis: RedisCache) -> None:
        self._db = db
        self._redis = redis
        self._daily_pnl: dict[str, DailyPnL] = {}
        self._trade_returns: deque[float] = deque(maxlen=1000)  # Rolling returns
        self._equity_curve: deque[float] = deque(maxlen=10000)
        self._peak_equity: float = 0.0

    async def record_trade_result(
        self,
        position: Position,
        pnl_usd: float,
        pnl_pct: float,
    ) -> None:
        """Record a completed trade result."""
        today = date.today().isoformat()
        if today not in self._daily_pnl:
            self._daily_pnl[today] = DailyPnL(date=today)

        daily = self._daily_pnl[today]
        daily.trades_count += 1
        daily.total_pnl_usd += pnl_usd
        if pnl_usd > 0:
            daily.wins += 1
        else:
            daily.losses += 1

        self._trade_returns.append(pnl_pct)

        # Persist
        await self._db.upsert_daily_pnl({
            "date": today,
            "trades_count": daily.trades_count,
            "wins": daily.wins,
            "losses": daily.losses,
            "total_pnl_usd": daily.total_pnl_usd,
            "total_pnl_pct": daily.total_pnl_pct,
        })

        logger.info(
            "Trade recorded: %s PnL=$%.2f (%.1f%%), daily=$%.2f (%d/%d)",
            position.token_symbol,
            pnl_usd,
            pnl_pct * 100,
            daily.total_pnl_usd,
            daily.wins,
            daily.trades_count,
        )

    def update_equity(self, portfolio_value: float) -> None:
        """Update the equity curve for drawdown tracking."""
        self._equity_curve.append(portfolio_value)
        self._peak_equity = max(self._peak_equity, portfolio_value)

    def get_current_drawdown(self) -> float:
        """Get current drawdown from peak in percentage."""
        if self._peak_equity <= 0:
            return 0.0
        current = self._equity_curve[-1] if self._equity_curve else 0
        return (self._peak_equity - current) / self._peak_equity

    def get_max_drawdown(self) -> float:
        """Calculate max drawdown from the equity curve."""
        if len(self._equity_curve) < 2:
            return 0.0
        peak = self._equity_curve[0]
        max_dd = 0.0
        for val in self._equity_curve:
            peak = max(peak, val)
            dd = (peak - val) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sharpe ratio from trade returns."""
        if len(self._trade_returns) < 5:
            return 0.0
        returns = list(self._trade_returns)
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns))
        if std_r == 0:
            return 0.0
        # Assume ~2 trades per day, ~365 days/year
        annualization = math.sqrt(365 * 2)
        daily_rf = risk_free_rate / 365
        return (mean_r - daily_rf) / std_r * annualization

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.05) -> float:
        """Calculate Sortino ratio (penalizes only downside volatility)."""
        if len(self._trade_returns) < 5:
            return 0.0
        returns = list(self._trade_returns)
        mean_r = sum(returns) / len(returns)
        downside = [r for r in returns if r < 0]
        if not downside:
            return float("inf") if mean_r > 0 else 0.0
        downside_std = math.sqrt(sum(r ** 2 for r in downside) / len(downside))
        if downside_std == 0:
            return 0.0
        annualization = math.sqrt(365 * 2)
        daily_rf = risk_free_rate / 365
        return (mean_r - daily_rf) / downside_std * annualization

    def calculate_profit_factor(self) -> float:
        """Gross profits / gross losses."""
        returns = list(self._trade_returns)
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def get_performance_stats(self) -> PerformanceStats:
        """Get aggregated performance statistics."""
        returns = list(self._trade_returns)
        wins_r = [r for r in returns if r > 0]
        losses_r = [r for r in returns if r <= 0]

        stats = PerformanceStats(
            total_trades=len(returns),
            wins=len(wins_r),
            losses=len(losses_r),
            total_pnl_pct=sum(returns),
            win_rate=len(wins_r) / len(returns) if returns else 0,
            profit_factor=self.calculate_profit_factor(),
            avg_win_usd=sum(wins_r) / len(wins_r) if wins_r else 0,
            avg_loss_usd=sum(losses_r) / len(losses_r) if losses_r else 0,
            max_drawdown_pct=self.get_max_drawdown(),
            sharpe_ratio=self.calculate_sharpe_ratio(),
            sortino_ratio=self.calculate_sortino_ratio(),
            best_trade_usd=max(returns) if returns else 0,
            worst_trade_usd=min(returns) if returns else 0,
        )
        return stats

    async def get_today_pnl(self) -> DailyPnL:
        """Get today's PnL."""
        today = date.today().isoformat()
        return self._daily_pnl.get(today, DailyPnL(date=today))

    async def get_daily_loss_pct(self, portfolio_value: float) -> float:
        """Get today's loss as percentage of portfolio."""
        today_pnl = await self.get_today_pnl()
        if portfolio_value <= 0:
            return 0.0
        return today_pnl.total_pnl_usd / portfolio_value
