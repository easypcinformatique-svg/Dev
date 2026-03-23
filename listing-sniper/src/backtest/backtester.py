"""Backtester — simulates the sniping strategy on historical listing data."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from src.backtest.data_collector import HistoricalListing

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """A simulated trade."""

    token_symbol: str
    entry_price: float
    exit_price: float
    amount_usd: float
    pnl_usd: float
    pnl_pct: float
    hold_hours: float
    exit_reason: str
    fees_usd: float


@dataclass
class BacktestResult:
    """Results of a backtest run."""

    initial_capital: float
    final_capital: float
    total_return_pct: float
    trades: list[BacktestTrade] = field(default_factory=list)
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    avg_hold_hours: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    total_fees_usd: float = 0.0


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    initial_capital: float = 10000.0
    max_position_pct: float = 0.05
    stop_loss_pct: float = 0.20
    take_profit_levels: list[dict] = field(default_factory=lambda: [
        {"pct": 0.25, "sell_fraction": 0.30},
        {"pct": 0.50, "sell_fraction": 0.30},
        {"pct": 1.00, "sell_fraction": 0.20},
    ])
    max_hold_hours: float = 24.0
    swap_fee_pct: float = 0.003        # 0.3% swap fee
    slippage_pct: float = 0.02          # 2% average slippage
    gas_fee_usd: float = 0.01           # ~$0.01 per Solana tx
    min_liquidity_usd: float = 5000.0
    max_risk_score: int = 80


class Backtester:
    """Simulates the listing sniping strategy on historical data."""

    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        self._config = config or BacktestConfig()

    def run(self, listings: list[HistoricalListing]) -> BacktestResult:
        """Run backtest on a list of historical listings."""
        capital = self._config.initial_capital
        trades: list[BacktestTrade] = []
        equity_curve: list[float] = [capital]

        for listing in listings:
            if listing.price_at_listing <= 0:
                continue
            if listing.liquidity_at_listing < self._config.min_liquidity_usd:
                continue

            # Simulate position sizing
            position_usd = min(
                capital * self._config.max_position_pct,
                listing.liquidity_at_listing * 0.02,  # 2% of liquidity
                5000.0,  # Max $5000
            )

            if position_usd < 100 or position_usd > capital * 0.95:
                continue

            # Simulate entry with slippage and fees
            entry_cost = position_usd * (1 + self._config.slippage_pct / 2)
            swap_fee = position_usd * self._config.swap_fee_pct
            total_cost = entry_cost + swap_fee + self._config.gas_fee_usd

            # Determine exit based on available price data
            exit_price_mult, exit_reason, hold_hours = self._simulate_exit(listing)

            # Simulate exit with slippage and fees
            exit_value = position_usd * exit_price_mult * (1 - self._config.slippage_pct / 2)
            exit_fee = exit_value * self._config.swap_fee_pct
            net_exit = exit_value - exit_fee - self._config.gas_fee_usd

            pnl = net_exit - total_cost
            pnl_pct = pnl / total_cost if total_cost > 0 else 0

            trade = BacktestTrade(
                token_symbol=listing.token_symbol,
                entry_price=listing.price_at_listing,
                exit_price=listing.price_at_listing * exit_price_mult,
                amount_usd=position_usd,
                pnl_usd=pnl,
                pnl_pct=pnl_pct,
                hold_hours=hold_hours,
                exit_reason=exit_reason,
                fees_usd=swap_fee * 2 + self._config.gas_fee_usd * 2,
            )
            trades.append(trade)
            capital += pnl
            equity_curve.append(capital)

        # Calculate metrics
        return self._calculate_results(
            self._config.initial_capital, capital, trades, equity_curve
        )

    def _simulate_exit(
        self, listing: HistoricalListing
    ) -> tuple[float, str, float]:
        """
        Simulate exit based on price data.
        Returns: (exit_price_multiplier, reason, hold_hours)
        """
        entry = listing.price_at_listing
        if entry <= 0:
            return (1.0, "no_data", 0)

        # Check take profit levels on available data
        prices_timeline = [
            (listing.price_1h_after, 1.0, "1h"),
            (listing.price_4h_after, 4.0, "4h"),
            (listing.price_24h_after, 24.0, "24h"),
        ]

        # Check stop-loss first at each point
        for price, hours, label in prices_timeline:
            if price <= 0:
                continue
            change = (price - entry) / entry

            # Stop loss
            if change <= -self._config.stop_loss_pct:
                return (1 - self._config.stop_loss_pct, "stop_loss", hours)

            # Take profit levels (simplified — check highest)
            for tp in self._config.take_profit_levels:
                if change >= tp["pct"]:
                    # Approximate: sell fraction at this level
                    return (1 + tp["pct"] * 0.8, f"tp_{tp['pct']:.0%}", hours)

        # Check peak
        if listing.price_peak_24h > 0:
            peak_gain = (listing.price_peak_24h - entry) / entry
            if peak_gain >= self._config.take_profit_levels[-1]["pct"]:
                # Would have hit highest TP
                return (
                    1 + self._config.take_profit_levels[-1]["pct"] * 0.8,
                    "tp_peak",
                    12.0,
                )

        # Time exit — use 24h price or last available
        for price, hours, label in reversed(prices_timeline):
            if price > 0:
                return (price / entry, f"time_exit_{label}", hours)

        return (1.0, "no_exit_data", 24.0)

    def _calculate_results(
        self,
        initial: float,
        final: float,
        trades: list[BacktestTrade],
        equity: list[float],
    ) -> BacktestResult:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return BacktestResult(
                initial_capital=initial,
                final_capital=final,
                total_return_pct=0,
            )

        wins = [t for t in trades if t.pnl_usd > 0]
        losses = [t for t in trades if t.pnl_usd <= 0]
        returns = [t.pnl_pct for t in trades]

        gross_profit = sum(t.pnl_usd for t in wins)
        gross_loss = abs(sum(t.pnl_usd for t in losses))

        # Sharpe
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 1
        sharpe = (mean_r / std_r * math.sqrt(365 * 2)) if std_r > 0 else 0

        # Sortino
        downside = [r for r in returns if r < 0]
        downside_std = (
            math.sqrt(sum(r ** 2 for r in downside) / len(downside))
            if downside
            else 0.001
        )
        sortino = (mean_r / downside_std * math.sqrt(365 * 2)) if downside_std > 0 else 0

        # Max drawdown
        peak = equity[0]
        max_dd = 0.0
        for val in equity:
            peak = max(peak, val)
            dd = (peak - val) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return BacktestResult(
            initial_capital=initial,
            final_capital=final,
            total_return_pct=(final - initial) / initial,
            trades=trades,
            total_trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=len(wins) / len(trades),
            profit_factor=gross_profit / gross_loss if gross_loss > 0 else float("inf"),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown_pct=max_dd,
            avg_pnl_pct=mean_r,
            avg_hold_hours=sum(t.hold_hours for t in trades) / len(trades),
            best_trade_pct=max(returns),
            worst_trade_pct=min(returns),
            total_fees_usd=sum(t.fees_usd for t in trades),
        )

    def print_report(self, result: BacktestResult) -> str:
        """Generate a human-readable backtest report."""
        lines = [
            "=" * 60,
            "BACKTEST REPORT",
            "=" * 60,
            f"Initial Capital:   ${result.initial_capital:,.2f}",
            f"Final Capital:     ${result.final_capital:,.2f}",
            f"Total Return:      {result.total_return_pct:+.1%}",
            "",
            f"Total Trades:      {result.total_trades}",
            f"Wins / Losses:     {result.wins} / {result.losses}",
            f"Win Rate:          {result.win_rate:.1%}",
            f"Profit Factor:     {result.profit_factor:.2f}",
            "",
            f"Sharpe Ratio:      {result.sharpe_ratio:.2f}",
            f"Sortino Ratio:     {result.sortino_ratio:.2f}",
            f"Max Drawdown:      {result.max_drawdown_pct:.1%}",
            "",
            f"Avg PnL/Trade:     {result.avg_pnl_pct:+.2%}",
            f"Avg Hold Time:     {result.avg_hold_hours:.1f}h",
            f"Best Trade:        {result.best_trade_pct:+.1%}",
            f"Worst Trade:       {result.worst_trade_pct:+.1%}",
            f"Total Fees:        ${result.total_fees_usd:,.2f}",
            "=" * 60,
        ]
        report = "\n".join(lines)
        logger.info("\n%s", report)
        return report
