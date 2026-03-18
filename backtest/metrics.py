"""
Métriques de performance hedge fund pour le backtesting.

Inclut toutes les métriques standard des fonds quantitatifs :
- Rendements, PnL, drawdown
- Sharpe, Sortino, Calmar, Information Ratio
- Win rate, profit factor, expectancy
- VaR, CVaR (Expected Shortfall)
- Statistiques de trades
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Résultat complet des métriques de performance."""
    # --- Rendements ---
    total_return: float
    annualized_return: float
    cumulative_pnl: float
    best_day: float
    worst_day: float
    avg_daily_return: float
    return_std: float

    # --- Ratios risk-adjusted ---
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    omega_ratio: float
    tail_ratio: float

    # --- Drawdown ---
    max_drawdown: float
    max_drawdown_duration_days: int
    avg_drawdown: float
    current_drawdown: float

    # --- Risque ---
    volatility_annualized: float
    downside_deviation: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    skewness: float
    kurtosis: float

    # --- Trades ---
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration_hours: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_trades_per_day: float

    # --- Capital ---
    initial_capital: float
    final_capital: float
    peak_capital: float

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "       PERFORMANCE REPORT - HEDGE FUND METRICS",
            "=" * 60,
            "",
            "--- RENDEMENTS ---",
            f"  Return total:          {self.total_return:>10.2%}",
            f"  Return annualisé:      {self.annualized_return:>10.2%}",
            f"  PnL cumulé:            {self.cumulative_pnl:>10,.2f} $",
            f"  Meilleur jour:         {self.best_day:>10.2%}",
            f"  Pire jour:             {self.worst_day:>10.2%}",
            "",
            "--- RATIOS RISK-ADJUSTED ---",
            f"  Sharpe Ratio:          {self.sharpe_ratio:>10.3f}",
            f"  Sortino Ratio:         {self.sortino_ratio:>10.3f}",
            f"  Calmar Ratio:          {self.calmar_ratio:>10.3f}",
            f"  Omega Ratio:           {self.omega_ratio:>10.3f}",
            f"  Information Ratio:     {self.information_ratio:>10.3f}",
            f"  Tail Ratio:            {self.tail_ratio:>10.3f}",
            "",
            "--- DRAWDOWN ---",
            f"  Max Drawdown:          {self.max_drawdown:>10.2%}",
            f"  Durée max DD (jours):  {self.max_drawdown_duration_days:>10d}",
            f"  Drawdown moyen:        {self.avg_drawdown:>10.2%}",
            "",
            "--- RISQUE ---",
            f"  Volatilité annualisée: {self.volatility_annualized:>10.2%}",
            f"  Downside Deviation:    {self.downside_deviation:>10.2%}",
            f"  VaR 95%:               {self.var_95:>10.2%}",
            f"  VaR 99%:               {self.var_99:>10.2%}",
            f"  CVaR 95%:              {self.cvar_95:>10.2%}",
            f"  CVaR 99%:              {self.cvar_99:>10.2%}",
            f"  Skewness:              {self.skewness:>10.3f}",
            f"  Kurtosis:              {self.kurtosis:>10.3f}",
            "",
            "--- TRADES ---",
            f"  Total trades:          {self.total_trades:>10d}",
            f"  Win rate:              {self.win_rate:>10.2%}",
            f"  Profit factor:         {self.profit_factor:>10.3f}",
            f"  Expectancy:            {self.expectancy:>10.2f} $",
            f"  Gain moyen:            {self.avg_win:>10.2f} $",
            f"  Perte moyenne:         {self.avg_loss:>10.2f} $",
            f"  Plus gros gain:        {self.largest_win:>10.2f} $",
            f"  Plus grosse perte:     {self.largest_loss:>10.2f} $",
            f"  Consécutifs gagnants:  {self.max_consecutive_wins:>10d}",
            f"  Consécutifs perdants:  {self.max_consecutive_losses:>10d}",
            "",
            "--- CAPITAL ---",
            f"  Capital initial:       {self.initial_capital:>10,.2f} $",
            f"  Capital final:         {self.final_capital:>10,.2f} $",
            f"  Capital peak:          {self.peak_capital:>10,.2f} $",
            "=" * 60,
        ]
        return "\n".join(lines)


def compute_drawdown_series(equity_curve: np.ndarray) -> tuple[np.ndarray, int, float]:
    """
    Calcule la série de drawdown et la durée maximale.

    Returns:
        (drawdown_series, max_duration_days, avg_drawdown)
    """
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    drawdown = np.where(peak > 0, drawdown, 0)

    # Durée max du drawdown
    in_drawdown = drawdown < 0
    max_duration = 0
    current_duration = 0
    for is_dd in in_drawdown:
        if is_dd:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    avg_dd = np.mean(drawdown[drawdown < 0]) if np.any(drawdown < 0) else 0.0

    return drawdown, max_duration, avg_dd


def _consecutive_count(arr: np.ndarray, value: bool) -> int:
    """Max consécutifs d'une valeur dans un array booléen."""
    max_count = 0
    count = 0
    for v in arr:
        if v == value:
            count += 1
            max_count = max(max_count, count)
        else:
            count = 0
    return max_count


def compute_metrics(
    trades: pd.DataFrame,
    equity_curve: pd.Series,
    initial_capital: float = 100000.0,
    risk_free_rate: float = 0.04,
    benchmark_returns: pd.Series | None = None,
) -> PerformanceMetrics:
    """
    Calcule toutes les métriques de performance.

    Args:
        trades: DataFrame avec colonnes [entry_time, exit_time, pnl, side, market_id]
        equity_curve: Série temporelle du capital (indexée par datetime)
        initial_capital: Capital de départ
        risk_free_rate: Taux sans risque annualisé
        benchmark_returns: Rendements du benchmark (pour Information Ratio)
    """
    # --- Rendements quotidiens ---
    daily_equity = equity_curve.resample("D").last().dropna()
    daily_returns = daily_equity.pct_change().dropna()

    if len(daily_returns) == 0:
        daily_returns = pd.Series([0.0])

    n_days = max(len(daily_returns), 1)
    n_years = max(n_days / 252, 1 / 252)
    rf_daily = (1 + risk_free_rate) ** (1 / 252) - 1

    # --- Rendements de base ---
    total_return = (equity_curve.iloc[-1] / initial_capital) - 1
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    cumulative_pnl = equity_curve.iloc[-1] - initial_capital

    # --- Sharpe ---
    excess_returns = daily_returns - rf_daily
    sharpe = (
        np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        if excess_returns.std() > 0
        else 0.0
    )

    # --- Sortino ---
    downside = daily_returns[daily_returns < rf_daily] - rf_daily
    downside_dev = np.sqrt(np.mean(downside ** 2)) if len(downside) > 0 else 1e-10
    sortino = np.sqrt(252) * excess_returns.mean() / downside_dev

    # --- Drawdown ---
    equity_arr = equity_curve.values
    dd_series, max_dd_duration, avg_dd = compute_drawdown_series(equity_arr)
    max_dd = float(np.min(dd_series))
    current_dd = float(dd_series[-1]) if len(dd_series) > 0 else 0

    # Calmar
    calmar = annualized_return / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # --- Information Ratio ---
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        aligned = daily_returns.align(benchmark_returns, join="inner")
        active_returns = aligned[0] - aligned[1]
        info_ratio = (
            np.sqrt(252) * active_returns.mean() / active_returns.std()
            if active_returns.std() > 0
            else 0.0
        )
    else:
        info_ratio = sharpe  # Pas de benchmark → utilise Sharpe

    # --- Omega Ratio ---
    threshold = rf_daily
    gains = daily_returns[daily_returns > threshold] - threshold
    losses = threshold - daily_returns[daily_returns <= threshold]
    omega = float(gains.sum() / losses.sum()) if losses.sum() > 0 else 10.0

    # --- Tail Ratio ---
    p95 = np.percentile(daily_returns, 95)
    p5 = abs(np.percentile(daily_returns, 5))
    tail_ratio = p95 / p5 if p5 > 1e-10 else 10.0

    # --- VaR & CVaR ---
    var_95 = float(np.percentile(daily_returns, 5))
    var_99 = float(np.percentile(daily_returns, 1))
    cvar_95 = float(daily_returns[daily_returns <= var_95].mean()) if len(daily_returns[daily_returns <= var_95]) > 0 else var_95
    cvar_99 = float(daily_returns[daily_returns <= var_99].mean()) if len(daily_returns[daily_returns <= var_99]) > 0 else var_99

    # --- Statistiques de trades ---
    n_trades = len(trades)
    if n_trades > 0:
        pnls = trades["pnl"].values
        wins = pnls > 0
        losses_mask = pnls < 0
        n_wins = int(np.sum(wins))
        n_losses = int(np.sum(losses_mask))
        win_rate = n_wins / n_trades

        gross_profit = float(np.sum(pnls[wins])) if n_wins > 0 else 0
        gross_loss = float(abs(np.sum(pnls[losses_mask]))) if n_losses > 0 else 1e-10
        profit_factor = gross_profit / gross_loss if gross_loss > 1e-10 else 10.0

        avg_win = float(np.mean(pnls[wins])) if n_wins > 0 else 0
        avg_loss = float(np.mean(pnls[losses_mask])) if n_losses > 0 else 0
        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

        largest_win = float(np.max(pnls)) if n_trades > 0 else 0
        largest_loss = float(np.min(pnls)) if n_trades > 0 else 0

        max_consec_wins = _consecutive_count(wins, True)
        max_consec_losses = _consecutive_count(losses_mask, True)

        # Durée moyenne des trades
        if "entry_time" in trades.columns and "exit_time" in trades.columns:
            durations = (
                pd.to_datetime(trades["exit_time"]) - pd.to_datetime(trades["entry_time"])
            )
            avg_duration_h = float(durations.mean().total_seconds() / 3600)
        else:
            avg_duration_h = 0.0

        avg_trades_day = n_trades / max(n_days, 1)
    else:
        n_wins = n_losses = 0
        win_rate = profit_factor = expectancy = 0
        avg_win = avg_loss = largest_win = largest_loss = 0
        max_consec_wins = max_consec_losses = 0
        avg_duration_h = avg_trades_day = 0

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        cumulative_pnl=cumulative_pnl,
        best_day=float(daily_returns.max()),
        worst_day=float(daily_returns.min()),
        avg_daily_return=float(daily_returns.mean()),
        return_std=float(daily_returns.std()),
        sharpe_ratio=float(sharpe),
        sortino_ratio=float(sortino),
        calmar_ratio=float(calmar),
        information_ratio=float(info_ratio),
        omega_ratio=float(omega),
        tail_ratio=float(tail_ratio),
        max_drawdown=max_dd,
        max_drawdown_duration_days=max_dd_duration,
        avg_drawdown=avg_dd,
        current_drawdown=current_dd,
        volatility_annualized=float(daily_returns.std() * np.sqrt(252)),
        downside_deviation=float(downside_dev * np.sqrt(252)),
        var_95=var_95,
        var_99=var_99,
        cvar_95=cvar_95,
        cvar_99=cvar_99,
        skewness=float(daily_returns.skew()),
        kurtosis=float(daily_returns.kurtosis()),
        total_trades=n_trades,
        winning_trades=n_wins,
        losing_trades=n_losses,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        avg_trade_duration_hours=avg_duration_h,
        max_consecutive_wins=max_consec_wins,
        max_consecutive_losses=max_consec_losses,
        avg_trades_per_day=avg_trades_day,
        initial_capital=initial_capital,
        final_capital=float(equity_curve.iloc[-1]),
        peak_capital=float(equity_curve.max()),
    )
