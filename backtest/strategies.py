"""
Stratégies de trading pour les marchés de prédiction Polymarket.

Chaque stratégie hérite de BaseStrategy et implémente on_bar().
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Position:
    """Position ouverte sur un marché."""
    market_id: str
    side: str  # "YES" ou "NO"
    entry_price: float
    size: float  # En USD
    entry_time: pd.Timestamp


@dataclass
class Trade:
    """Trade terminé."""
    market_id: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    exit_reason: str  # "signal", "stop_loss", "take_profit", "resolution"


class BaseStrategy(ABC):
    """Classe de base pour les stratégies de trading Polymarket."""

    def __init__(
        self,
        name: str = "BaseStrategy",
        max_position_pct: float = 0.05,
        max_positions: int = 10,
        stop_loss: float = 0.15,
        take_profit: float = 0.30,
    ):
        self.name = name
        self.max_position_pct = max_position_pct
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []

    @abstractmethod
    def generate_signal(
        self,
        market_id: str,
        current_bar: pd.Series,
        history: pd.DataFrame,
    ) -> tuple[str, float]:
        """
        Génère un signal de trading.

        Returns:
            (action, confidence) où action ∈ {"BUY_YES", "BUY_NO", "SELL", "HOLD"}
            et confidence ∈ [0, 1]
        """
        pass

    def check_exits(
        self,
        market_id: str,
        current_bar: pd.Series,
        capital: float,
    ) -> Trade | None:
        """Vérifie les conditions de sortie (stop-loss, take-profit)."""
        if market_id not in self.positions:
            return None

        pos = self.positions[market_id]
        mid = current_bar["mid_price"]

        if pos.side == "YES":
            unrealized_pnl_pct = (mid - pos.entry_price) / pos.entry_price
        else:
            unrealized_pnl_pct = (pos.entry_price - mid) / pos.entry_price

        exit_reason = None
        if unrealized_pnl_pct <= -self.stop_loss:
            exit_reason = "stop_loss"
        elif unrealized_pnl_pct >= self.take_profit:
            exit_reason = "take_profit"

        if exit_reason:
            return self._close_position(market_id, mid, current_bar.name, exit_reason)
        return None

    def _close_position(
        self,
        market_id: str,
        exit_price: float,
        exit_time: pd.Timestamp,
        reason: str,
    ) -> Trade:
        pos = self.positions.pop(market_id)
        if pos.side == "YES":
            pnl = (exit_price - pos.entry_price) * pos.size / pos.entry_price
        else:
            pnl = (pos.entry_price - exit_price) * pos.size / pos.entry_price

        trade = Trade(
            market_id=market_id,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size=pos.size,
            pnl=pnl,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            exit_reason=reason,
        )
        self.trades.append(trade)
        return trade

    def resolve_position(
        self,
        market_id: str,
        outcome: bool,
        resolution_time: pd.Timestamp,
    ) -> Trade | None:
        """Résout une position quand le marché se termine."""
        if market_id not in self.positions:
            return None
        final_price = 1.0 if outcome else 0.0
        if self.positions[market_id].side == "NO":
            final_price = 1.0 - final_price
        return self._close_position(market_id, final_price, resolution_time, "resolution")


class MomentumStrategy(BaseStrategy):
    """
    Stratégie Momentum : achète quand le prix monte fortement,
    vend quand il descend. Suit la tendance.
    """

    def __init__(
        self,
        lookback: int = 24,
        momentum_threshold: float = 0.05,
        volume_filter: float = 1.2,
        **kwargs,
    ):
        super().__init__(name="Momentum", **kwargs)
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold
        self.volume_filter = volume_filter

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.lookback:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        price_change = current_bar["mid_price"] - recent["mid_price"].iloc[0]

        # Filtre volume : volume récent > moyenne * seuil
        avg_vol = history["volume_usd"].mean()
        recent_vol = recent["volume_usd"].mean()
        if recent_vol < avg_vol * self.volume_filter:
            return "HOLD", 0.0

        confidence = min(abs(price_change) / self.momentum_threshold, 1.0)

        if price_change > self.momentum_threshold:
            return "BUY_YES", confidence
        elif price_change < -self.momentum_threshold:
            return "BUY_NO", confidence

        return "HOLD", 0.0


class MeanReversionStrategy(BaseStrategy):
    """
    Stratégie Mean Reversion : parie sur le retour à la moyenne.
    Achète quand le prix est anormalement bas, vend quand il est haut.
    """

    def __init__(
        self,
        lookback: int = 48,
        z_score_threshold: float = 1.5,
        **kwargs,
    ):
        super().__init__(name="MeanReversion", **kwargs)
        self.lookback = lookback
        self.z_score_threshold = z_score_threshold

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.lookback:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        mean = recent["mid_price"].mean()
        std = recent["mid_price"].std()

        if std < 1e-6:
            return "HOLD", 0.0

        z_score = (current_bar["mid_price"] - mean) / std
        confidence = min(abs(z_score) / (self.z_score_threshold * 2), 1.0)

        if z_score < -self.z_score_threshold:
            return "BUY_YES", confidence  # Prix bas → acheter
        elif z_score > self.z_score_threshold:
            return "BUY_NO", confidence  # Prix haut → shorter

        return "HOLD", 0.0


class ValueStrategy(BaseStrategy):
    """
    Stratégie Value : identifie les marchés mal pricés en comparant
    le prix actuel à une estimation fondamentale basée sur la
    trajectoire historique et le volume.
    """

    def __init__(
        self,
        lookback: int = 72,
        edge_threshold: float = 0.08,
        volume_weight: float = 0.3,
        **kwargs,
    ):
        super().__init__(name="Value", **kwargs)
        self.lookback = lookback
        self.edge_threshold = edge_threshold
        self.volume_weight = volume_weight

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.lookback:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        prices = recent["mid_price"].values
        volumes = recent["volume_usd"].values

        # Prix moyen pondéré par le volume (VWAP)
        total_vol = volumes.sum()
        if total_vol < 1e-6:
            return "HOLD", 0.0
        vwap = np.sum(prices * volumes) / total_vol

        # Estimation fondamentale : combinaison VWAP + tendance
        trend = np.polyfit(np.arange(len(prices)), prices, 1)[0] * len(prices)
        fair_value = (1 - self.volume_weight) * vwap + self.volume_weight * (vwap + trend)
        fair_value = max(0.01, min(0.99, fair_value))

        edge = fair_value - current_bar["mid_price"]
        confidence = min(abs(edge) / (self.edge_threshold * 2), 1.0)

        if edge > self.edge_threshold:
            return "BUY_YES", confidence
        elif edge < -self.edge_threshold:
            return "BUY_NO", confidence

        return "HOLD", 0.0


class CompositeStrategy(BaseStrategy):
    """
    Stratégie composite : combine plusieurs stratégies avec des poids.
    Signal = moyenne pondérée des signaux individuels.
    """

    def __init__(
        self,
        strategies: list[tuple[BaseStrategy, float]] | None = None,
        consensus_threshold: float = 0.5,
        **kwargs,
    ):
        super().__init__(name="Composite", **kwargs)
        if strategies is None:
            strategies = [
                (MomentumStrategy(), 0.3),
                (MeanReversionStrategy(), 0.4),
                (ValueStrategy(), 0.3),
            ]
        self.sub_strategies = strategies
        self.consensus_threshold = consensus_threshold

    def generate_signal(self, market_id, current_bar, history):
        scores = {"BUY_YES": 0.0, "BUY_NO": 0.0, "HOLD": 0.0}

        total_weight = sum(w for _, w in self.sub_strategies)
        for strat, weight in self.sub_strategies:
            action, confidence = strat.generate_signal(market_id, current_bar, history)
            scores[action] += (weight / total_weight) * confidence

        best_action = max(scores, key=scores.get)
        best_score = scores[best_action]

        if best_action != "HOLD" and best_score >= self.consensus_threshold:
            return best_action, best_score

        return "HOLD", 0.0
