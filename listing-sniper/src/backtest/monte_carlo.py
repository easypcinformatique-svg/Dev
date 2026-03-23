"""Monte Carlo simulation — stress-test the strategy with randomized scenarios."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field

from src.backtest.backtester import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Results of Monte Carlo simulation."""

    num_simulations: int
    original_return_pct: float
    # Distribution of final returns
    mean_return_pct: float
    median_return_pct: float
    std_return_pct: float
    percentile_5_pct: float      # Worst 5% scenario
    percentile_25_pct: float
    percentile_75_pct: float
    percentile_95_pct: float     # Best 5% scenario
    # Risk metrics
    prob_of_loss: float          # P(return < 0)
    prob_of_ruin: float          # P(drawdown > 50%)
    worst_case_return_pct: float
    best_case_return_pct: float
    # Drawdown
    mean_max_drawdown_pct: float
    worst_drawdown_pct: float
    # Sharpe distribution
    mean_sharpe: float
    percentile_5_sharpe: float


class MonteCarloSimulator:
    """Runs Monte Carlo simulations on backtest trade returns."""

    def __init__(self, num_simulations: int = 10000) -> None:
        self._num_sims = num_simulations

    def run(
        self,
        backtest_result: BacktestResult,
        initial_capital: float = 10000.0,
        num_trades: int | None = None,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation by resampling trades with replacement.

        This shuffles the order of trades to see how path-dependent the results are.
        """
        trade_returns = [t.pnl_pct for t in backtest_result.trades]
        if not trade_returns:
            return MonteCarloResult(
                num_simulations=0,
                original_return_pct=0,
                mean_return_pct=0,
                median_return_pct=0,
                std_return_pct=0,
                percentile_5_pct=0,
                percentile_25_pct=0,
                percentile_75_pct=0,
                percentile_95_pct=0,
                prob_of_loss=0,
                prob_of_ruin=0,
                worst_case_return_pct=0,
                best_case_return_pct=0,
                mean_max_drawdown_pct=0,
                worst_drawdown_pct=0,
                mean_sharpe=0,
                percentile_5_sharpe=0,
            )

        n_trades = num_trades or len(trade_returns)
        final_returns: list[float] = []
        max_drawdowns: list[float] = []
        sharpe_ratios: list[float] = []
        ruin_count = 0

        for _ in range(self._num_sims):
            # Resample trades with replacement
            sampled = random.choices(trade_returns, k=n_trades)

            # Simulate equity curve
            equity = initial_capital
            peak = equity
            max_dd = 0.0
            for ret in sampled:
                equity *= (1 + ret)
                peak = max(peak, equity)
                dd = (peak - equity) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)

            total_return = (equity - initial_capital) / initial_capital
            final_returns.append(total_return)
            max_drawdowns.append(max_dd)

            if max_dd > 0.50:
                ruin_count += 1

            # Sharpe
            mean_r = sum(sampled) / len(sampled)
            std_r = math.sqrt(
                sum((r - mean_r) ** 2 for r in sampled) / len(sampled)
            ) if len(sampled) > 1 else 0.001
            sharpe = mean_r / std_r * math.sqrt(365 * 2) if std_r > 0 else 0
            sharpe_ratios.append(sharpe)

        # Sort for percentiles
        final_returns.sort()
        max_drawdowns.sort()
        sharpe_ratios.sort()

        def pct(data: list[float], p: float) -> float:
            idx = int(len(data) * p)
            return data[min(idx, len(data) - 1)]

        prob_loss = sum(1 for r in final_returns if r < 0) / len(final_returns)

        result = MonteCarloResult(
            num_simulations=self._num_sims,
            original_return_pct=backtest_result.total_return_pct,
            mean_return_pct=sum(final_returns) / len(final_returns),
            median_return_pct=pct(final_returns, 0.50),
            std_return_pct=math.sqrt(
                sum((r - sum(final_returns) / len(final_returns)) ** 2 for r in final_returns)
                / len(final_returns)
            ),
            percentile_5_pct=pct(final_returns, 0.05),
            percentile_25_pct=pct(final_returns, 0.25),
            percentile_75_pct=pct(final_returns, 0.75),
            percentile_95_pct=pct(final_returns, 0.95),
            prob_of_loss=prob_loss,
            prob_of_ruin=ruin_count / self._num_sims,
            worst_case_return_pct=final_returns[0],
            best_case_return_pct=final_returns[-1],
            mean_max_drawdown_pct=sum(max_drawdowns) / len(max_drawdowns),
            worst_drawdown_pct=max_drawdowns[-1],
            mean_sharpe=sum(sharpe_ratios) / len(sharpe_ratios),
            percentile_5_sharpe=pct(sharpe_ratios, 0.05),
        )

        self._print_report(result)
        return result

    def _print_report(self, r: MonteCarloResult) -> None:
        """Print Monte Carlo simulation report."""
        report = f"""
{'=' * 60}
MONTE CARLO SIMULATION ({r.num_simulations:,} runs)
{'=' * 60}
Original Return:     {r.original_return_pct:+.1%}

Return Distribution:
  Mean:              {r.mean_return_pct:+.1%}
  Median:            {r.median_return_pct:+.1%}
  Std Dev:           {r.std_return_pct:.1%}
  5th percentile:    {r.percentile_5_pct:+.1%}  (worst 5%)
  25th percentile:   {r.percentile_25_pct:+.1%}
  75th percentile:   {r.percentile_75_pct:+.1%}
  95th percentile:   {r.percentile_95_pct:+.1%}  (best 5%)
  Worst case:        {r.worst_case_return_pct:+.1%}
  Best case:         {r.best_case_return_pct:+.1%}

Risk:
  P(loss):           {r.prob_of_loss:.1%}
  P(ruin > 50% DD):  {r.prob_of_ruin:.1%}
  Mean Max DD:       {r.mean_max_drawdown_pct:.1%}
  Worst DD:          {r.worst_drawdown_pct:.1%}

Sharpe:
  Mean:              {r.mean_sharpe:.2f}
  5th percentile:    {r.percentile_5_sharpe:.2f}
{'=' * 60}"""
        logger.info(report)
