"""
Moteur de backtesting pour les marchés de prédiction Polymarket.

Simule l'exécution de stratégies sur des données historiques avec :
- Gestion du capital et du sizing des positions
- Slippage et frais de transaction réalistes
- Exécution chronologique barre par barre
- Tracking complet de l'equity curve et des trades
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

from .strategies import BaseStrategy, Position, Trade, AlphaCompositeStrategy
from .metrics import compute_metrics, PerformanceMetrics
from .data_generator import MarketConfig


@dataclass
class BacktestConfig:
    """Configuration du backtest."""
    initial_capital: float = 100000.0
    transaction_fee_pct: float = 0.002  # 0.2% frais
    slippage_pct: float = 0.001  # 0.1% slippage
    max_position_pct: float = 0.05  # 5% du capital max par position
    max_total_exposure_pct: float = 0.50  # 50% max d'exposition
    risk_free_rate: float = 0.04
    rebalance_freq: str = "1h"  # Fréquence d'évaluation


@dataclass
class BacktestResult:
    """Résultats complets du backtest."""
    metrics: PerformanceMetrics
    trades: pd.DataFrame
    equity_curve: pd.Series
    positions_over_time: pd.DataFrame
    daily_returns: pd.Series
    strategy_name: str
    config: BacktestConfig
    market_configs: list[MarketConfig]


class BacktestEngine:
    """
    Moteur de backtesting event-driven pour Polymarket.

    Parcourt les données chronologiquement et exécute la stratégie
    sur chaque barre de chaque marché actif.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        config: BacktestConfig | None = None,
    ):
        self.strategy = strategy
        self.config = config or BacktestConfig()
        self.capital = self.config.initial_capital
        self.equity_history: list[tuple[pd.Timestamp, float]] = []
        self.position_history: list[dict] = []

    def _get_total_exposure(self) -> float:
        return sum(p.size for p in self.strategy.positions.values())

    def _execute_entry(
        self,
        market_id: str,
        side: str,
        price: float,
        confidence: float,
        timestamp: pd.Timestamp,
        spread: float,
    ) -> bool:
        """Exécute une entrée en position."""
        if market_id in self.strategy.positions:
            return False
        if len(self.strategy.positions) >= self.strategy.max_positions:
            return False

        # Sizing basé sur la confiance et les limites
        max_size = self.capital * self.config.max_position_pct
        exposure = self._get_total_exposure()
        max_remaining = self.capital * self.config.max_total_exposure_pct - exposure
        if max_remaining <= 0:
            return False

        size = min(max_size * confidence, max_remaining)
        if size < 10:  # Minimum $10
            return False

        # Slippage + spread
        if side == "YES":
            exec_price = price + spread / 2 + price * self.config.slippage_pct
        else:
            exec_price = price - spread / 2 - price * self.config.slippage_pct
        exec_price = max(0.01, min(0.99, exec_price))

        # Frais
        fee = size * self.config.transaction_fee_pct
        total_cost = size + fee
        if total_cost > self.capital:
            return False

        self.capital -= total_cost
        self.strategy.positions[market_id] = Position(
            market_id=market_id,
            side=side,
            entry_price=exec_price,
            size=size,
            entry_time=timestamp,
        )
        return True

    def _execute_exit(
        self,
        market_id: str,
        price: float,
        timestamp: pd.Timestamp,
        reason: str,
    ) -> Trade | None:
        """Exécute une sortie de position."""
        if market_id not in self.strategy.positions:
            return None

        pos = self.strategy.positions[market_id]

        # Slippage
        if pos.side == "YES":
            exec_price = price - price * self.config.slippage_pct
        else:
            exec_price = price + price * self.config.slippage_pct
        exec_price = max(0.01, min(0.99, exec_price))

        trade = self.strategy._close_position(market_id, exec_price, timestamp, reason)

        # Frais de sortie
        fee = pos.size * self.config.transaction_fee_pct
        trade.pnl -= fee

        self.capital += pos.size + trade.pnl
        return trade

    def run(
        self,
        data: pd.DataFrame,
        market_configs: list[MarketConfig],
    ) -> BacktestResult:
        """
        Exécute le backtest sur l'ensemble des données.

        Args:
            data: DataFrame avec les données de tous les marchés
            market_configs: Liste des configurations de marchés
        """
        self.capital = self.config.initial_capital
        self.strategy.positions = {}
        self.strategy.trades = []
        self.equity_history = []
        self.position_history = []

        # Index des configs par market_id
        config_map = {c.market_id: c for c in market_configs}

        # Résolutions des marchés
        resolution_map = {
            c.market_id: (c.resolution_date, c.outcome) for c in market_configs
        }

        # Historique par marché — pré-indexé pour performance
        market_histories: dict[str, list[pd.Series]] = {}
        # Cache DataFrame pour éviter la reconstruction à chaque barre
        market_history_dfs: dict[str, pd.DataFrame] = {}
        _history_rebuild_interval = 50  # Rebuild le DF tous les N barres
        _history_counters: dict[str, int] = {}

        # Grouper par timestamp
        grouped = data.groupby("timestamp")
        timestamps = sorted(data["timestamp"].unique())

        for ts in timestamps:
            ts = pd.Timestamp(ts)
            group = grouped.get_group(ts)

            # 1. Vérifier les résolutions
            resolved_markets = []
            for mid in list(self.strategy.positions.keys()):
                if mid in resolution_map:
                    res_date, outcome = resolution_map[mid]
                    if ts >= pd.Timestamp(res_date):
                        # Résolution
                        final_price = 1.0 if outcome else 0.0
                        self._execute_exit(mid, final_price, ts, "resolution")
                        resolved_markets.append(mid)

            # 2. Parcourir chaque marché actif
            for _, bar in group.iterrows():
                mid = bar["market_id"]
                if mid in resolved_markets:
                    continue

                # Mettre à jour l'historique (optimisé)
                if mid not in market_histories:
                    market_histories[mid] = []
                    _history_counters[mid] = 0
                market_histories[mid].append(bar)
                _history_counters[mid] += 1

                # Rebuild le DataFrame seulement tous les N barres
                if _history_counters[mid] >= _history_rebuild_interval or mid not in market_history_dfs:
                    market_history_dfs[mid] = pd.DataFrame(market_histories[mid])
                    _history_counters[mid] = 0
                history_df = market_history_dfs[mid]

                # 3. Vérifier stop-loss / take-profit
                trade = self.strategy.check_exits(mid, bar, self.capital)
                if trade:
                    fee = trade.size * self.config.transaction_fee_pct
                    trade.pnl -= fee
                    pos_size = trade.size
                    self.capital += pos_size + trade.pnl
                    # Feedback pour AlphaComposite
                    if isinstance(self.strategy, AlphaCompositeStrategy):
                        self.strategy.update_strategy_performance(mid, trade.pnl)

                # 4. Générer signal et exécuter
                action, confidence = self.strategy.generate_signal(
                    mid, bar, history_df
                )

                if action == "SELL" and mid in self.strategy.positions:
                    self._execute_exit(mid, bar["mid_price"], ts, "signal")
                elif action in ("BUY_YES", "BUY_NO"):
                    side = "YES" if action == "BUY_YES" else "NO"
                    self._execute_entry(
                        mid, side, bar["mid_price"], confidence, ts, bar["spread"]
                    )

            # 5. Calculer l'equity
            total_equity = self.capital
            n_positions = len(self.strategy.positions)
            for mid, pos in self.strategy.positions.items():
                # Valeur mark-to-market
                market_data = group[group["market_id"] == mid]
                if len(market_data) > 0:
                    current_price = market_data.iloc[0]["mid_price"]
                    if pos.side == "YES":
                        mtm = pos.size * (1 + (current_price - pos.entry_price) / pos.entry_price)
                    else:
                        mtm = pos.size * (1 + (pos.entry_price - current_price) / pos.entry_price)
                    total_equity += mtm
                else:
                    total_equity += pos.size

            self.equity_history.append((ts, total_equity))
            self.position_history.append({
                "timestamp": ts,
                "n_positions": n_positions,
                "capital_cash": self.capital,
                "total_equity": total_equity,
                "exposure": self._get_total_exposure(),
                "exposure_pct": self._get_total_exposure() / total_equity if total_equity > 0 else 0,
            })

        # --- Construire les résultats ---
        # Equity curve
        eq_df = pd.DataFrame(self.equity_history, columns=["timestamp", "equity"])
        eq_df = eq_df.set_index("timestamp")
        equity_curve = eq_df["equity"]

        # Trades DataFrame
        if self.strategy.trades:
            trades_df = pd.DataFrame([{
                "market_id": t.market_id,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "size": t.size,
                "pnl": t.pnl,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "exit_reason": t.exit_reason,
                "return_pct": t.pnl / t.size if t.size > 0 else 0,
            } for t in self.strategy.trades])
        else:
            trades_df = pd.DataFrame(columns=[
                "market_id", "side", "entry_price", "exit_price",
                "size", "pnl", "entry_time", "exit_time", "exit_reason", "return_pct",
            ])

        # Positions over time
        positions_df = pd.DataFrame(self.position_history)

        # Métriques
        metrics = compute_metrics(
            trades=trades_df,
            equity_curve=equity_curve,
            initial_capital=self.config.initial_capital,
            risk_free_rate=self.config.risk_free_rate,
        )

        # Daily returns
        daily_eq = equity_curve.resample("D").last().dropna()
        daily_returns = daily_eq.pct_change().dropna()

        return BacktestResult(
            metrics=metrics,
            trades=trades_df,
            equity_curve=equity_curve,
            positions_over_time=positions_df,
            daily_returns=daily_returns,
            strategy_name=self.strategy.name,
            config=self.config,
            market_configs=market_configs,
        )
