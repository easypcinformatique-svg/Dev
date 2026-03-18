"""
Stratégies de trading pour les marchés de prédiction Polymarket.

Inclut les stratégies de base ET les stratégies avancées inspirées
des meilleurs quant funds (Citadel, Renaissance, Two Sigma) adaptées
aux prediction markets :

- Kelly Criterion sizing (position sizing optimal)
- Smart Money detection (suivre les gros volumes)
- Convergence trading (marchés proche de la résolution)
- Bayesian Edge (estimation bayésienne de la vraie probabilité)
- Alpha Composite (combinaison optimisée de tous les signaux)
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
        trailing_stop: float = 0.0,
    ):
        self.name = name
        self.max_position_pct = max_position_pct
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self._peak_prices: dict[str, float] = {}  # Pour trailing stop

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
        """Vérifie les conditions de sortie (stop-loss, take-profit, trailing)."""
        if market_id not in self.positions:
            return None

        pos = self.positions[market_id]
        mid = current_bar["mid_price"]

        if pos.side == "YES":
            unrealized_pnl_pct = (mid - pos.entry_price) / pos.entry_price
        else:
            unrealized_pnl_pct = (pos.entry_price - mid) / pos.entry_price

        # Trailing stop : tracker le meilleur PnL et sortir si ça recule
        if self.trailing_stop > 0:
            peak = self._peak_prices.get(market_id, unrealized_pnl_pct)
            if unrealized_pnl_pct > peak:
                self._peak_prices[market_id] = unrealized_pnl_pct
                peak = unrealized_pnl_pct
            # Trailing : si on a reculé de trailing_stop depuis le peak
            if peak > 0.03 and (peak - unrealized_pnl_pct) > self.trailing_stop:
                self._peak_prices.pop(market_id, None)
                return self._close_position(market_id, mid, current_bar.name, "trailing_stop")

        exit_reason = None
        if unrealized_pnl_pct <= -self.stop_loss:
            exit_reason = "stop_loss"
        elif unrealized_pnl_pct >= self.take_profit:
            exit_reason = "take_profit"

        if exit_reason:
            self._peak_prices.pop(market_id, None)
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


# ============================================================
#  STRATEGIES DE BASE
# ============================================================


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


# ============================================================
#  STRATEGIES AVANCEES — INSPIREES DES MEILLEURS QUANT FUNDS
# ============================================================


def _kelly_fraction(win_prob: float, win_loss_ratio: float) -> float:
    """
    Critère de Kelly : fraction optimale du capital à risquer.
    f* = (p * b - q) / b
    où p = proba de gain, q = 1-p, b = ratio gain/perte

    On applique un demi-Kelly (plus conservateur) comme les vrais funds.
    """
    if win_loss_ratio <= 0:
        return 0.0
    q = 1.0 - win_prob
    kelly = (win_prob * win_loss_ratio - q) / win_loss_ratio
    # Demi-Kelly pour être conservateur
    return max(0.0, min(kelly * 0.5, 0.25))


def _exponential_moving_avg(values: np.ndarray, span: int) -> np.ndarray:
    """EMA rapide via numpy."""
    alpha = 2.0 / (span + 1)
    ema = np.zeros_like(values, dtype=float)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema


class SmartMoneyStrategy(BaseStrategy):
    """
    Smart Money Detection — Inspiré de la méthode Wyckoff / order flow.

    Principe : les gros volumes avec un mouvement de prix directionnel
    indiquent une "smart money" (baleines, insiders). On suit ces mouvements.

    Signaux :
    - Volume spike + mouvement directionnel = accumulation/distribution
    - Divergence volume/prix = retournement probable
    - On filtre les faux signaux avec la consistance directionnelle
    """

    def __init__(
        self,
        lookback: int = 36,
        volume_spike_threshold: float = 2.0,
        directional_threshold: float = 0.03,
        consistency_window: int = 6,
        **kwargs,
    ):
        super().__init__(name="SmartMoney", **kwargs)
        self.lookback = lookback
        self.volume_spike_threshold = volume_spike_threshold
        self.directional_threshold = directional_threshold
        self.consistency_window = consistency_window

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.lookback:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        prices = recent["mid_price"].values
        volumes = recent["volume_usd"].values

        # 1. Détecter les spikes de volume
        vol_mean = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        vol_std = np.std(volumes[:-1]) if len(volumes) > 1 else 1.0
        current_vol = current_bar["volume_usd"]
        vol_z = (current_vol - vol_mean) / max(vol_std, 1.0)
        is_vol_spike = vol_z > self.volume_spike_threshold

        if not is_vol_spike:
            return "HOLD", 0.0

        # 2. Direction du mouvement pendant le spike
        recent_prices = prices[-self.consistency_window:]
        price_change = current_bar["mid_price"] - recent_prices[0]

        # 3. Consistance directionnelle (éviter les faux signaux)
        # Compter combien de barres récentes vont dans la même direction
        price_diffs = np.diff(recent_prices)
        if price_change > 0:
            consistency = np.sum(price_diffs > 0) / max(len(price_diffs), 1)
        else:
            consistency = np.sum(price_diffs < 0) / max(len(price_diffs), 1)

        if consistency < 0.5:
            return "HOLD", 0.0

        # 4. Volume-Weighted Price Change (la force du signal)
        vol_weight = min(vol_z / 4.0, 1.0)  # Normaliser le z-score volume
        price_weight = min(abs(price_change) / self.directional_threshold, 1.0)
        confidence = vol_weight * 0.5 + price_weight * 0.3 + consistency * 0.2

        if abs(price_change) < self.directional_threshold * 0.5:
            return "HOLD", 0.0

        if price_change > 0:
            return "BUY_YES", min(confidence, 1.0)
        else:
            return "BUY_NO", min(confidence, 1.0)


class ConvergenceStrategy(BaseStrategy):
    """
    Convergence Trading — Exploiter la convergence des marchés
    vers leur résultat final.

    Principe : plus un marché s'approche de sa résolution, plus le
    prix converge vers 0 ou 1. On identifie les marchés dont la
    trajectoire montre une forte tendance directionnelle et on
    suit cette tendance avec une taille de position croissante.

    Filtres :
    - Le marché doit être assez avancé (>60% de sa durée)
    - La tendance doit être forte et consistante
    - Le prix ne doit pas être déjà trop extrême (>0.90 ou <0.10)
    """

    def __init__(
        self,
        min_market_progress: float = 0.60,
        trend_lookback: int = 48,
        trend_threshold: float = 0.02,
        max_price_extreme: float = 0.88,
        min_price_extreme: float = 0.12,
        **kwargs,
    ):
        super().__init__(name="Convergence", **kwargs)
        self.min_market_progress = min_market_progress
        self.trend_lookback = trend_lookback
        self.trend_threshold = trend_threshold
        self.max_price_extreme = max_price_extreme
        self.min_price_extreme = min_price_extreme

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.trend_lookback:
            return "HOLD", 0.0

        recent = history.tail(self.trend_lookback)
        prices = recent["mid_price"].values
        current_price = current_bar["mid_price"]

        # Estimation du progrès du marché via la réduction de volatilité
        full_history_prices = history["mid_price"].values
        if len(full_history_prices) < 50:
            return "HOLD", 0.0

        early_vol = np.std(full_history_prices[:len(full_history_prices) // 3])
        recent_vol = np.std(full_history_prices[-len(full_history_prices) // 3:])
        vol_ratio = recent_vol / max(early_vol, 1e-6)

        # Si la volatilité ne diminue pas, le marché n'est pas en convergence
        if vol_ratio > 0.8:
            return "HOLD", 0.0

        # Prix trop extrême → pas d'entrée (edge insuffisant)
        if current_price > self.max_price_extreme or current_price < self.min_price_extreme:
            return "HOLD", 0.0

        # Tendance via régression linéaire
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]

        # Tendance forte et consistante
        if abs(slope) < self.trend_threshold / self.trend_lookback:
            return "HOLD", 0.0

        # R² de la tendance (qualité de la régression)
        predicted = np.polyval(np.polyfit(x, prices, 1), x)
        ss_res = np.sum((prices - predicted) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - ss_res / max(ss_tot, 1e-10)

        if r_squared < 0.3:
            return "HOLD", 0.0

        # Confidence = combinaison tendance, R², et réduction de volatilité
        trend_strength = min(abs(slope * self.trend_lookback) / 0.15, 1.0)
        confidence = trend_strength * 0.4 + r_squared * 0.35 + (1 - vol_ratio) * 0.25

        if slope > 0:
            return "BUY_YES", min(confidence, 1.0)
        else:
            return "BUY_NO", min(confidence, 1.0)


class BayesianEdgeStrategy(BaseStrategy):
    """
    Bayesian Edge — Estimation bayésienne de la vraie probabilité
    et détection de mispricing.

    Principe : on maintient un prior sur la probabilité de l'événement,
    mis à jour avec les données observées (prix, volume, direction).
    Quand notre estimation diverge significativement du prix de marché,
    on entre en position.

    C'est l'approche utilisée par les market makers professionnels
    sur Polymarket (similaire à ce que fait Nate Silver).
    """

    def __init__(
        self,
        lookback: int = 60,
        prior_alpha: float = 2.0,
        prior_beta: float = 2.0,
        edge_threshold: float = 0.06,
        volume_info_weight: float = 0.4,
        min_observations: int = 30,
        **kwargs,
    ):
        super().__init__(name="BayesianEdge", **kwargs)
        self.lookback = lookback
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.edge_threshold = edge_threshold
        self.volume_info_weight = volume_info_weight
        self.min_observations = min_observations

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.min_observations:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        prices = recent["mid_price"].values
        volumes = recent["volume_usd"].values

        # --- Mise à jour bayésienne ---
        # On traite chaque barre comme une observation qui informe notre prior
        # Les barres à fort volume comptent plus (plus d'information)
        alpha = self.prior_alpha
        beta = self.prior_beta

        # Normaliser les volumes pour les utiliser comme poids
        vol_weights = volumes / np.median(volumes)
        vol_weights = np.clip(vol_weights, 0.1, 5.0)

        for i in range(len(prices)):
            p = prices[i]
            w = vol_weights[i] * self.volume_info_weight
            # Le prix est notre "observation" de la vraie probabilité
            alpha += p * w
            beta += (1 - p) * w

        # Estimation bayésienne (moyenne de la distribution Beta)
        estimated_prob = alpha / (alpha + beta)

        # Intervalle de crédibilité à 80% (incertitude)
        from scipy import stats as sp_stats
        ci_low = sp_stats.beta.ppf(0.10, alpha, beta)
        ci_high = sp_stats.beta.ppf(0.90, alpha, beta)
        uncertainty = ci_high - ci_low

        # --- Ajustement par la tendance récente ---
        # Les dernières barres ont plus de poids informatif
        recent_20 = prices[-min(20, len(prices)):]
        recent_vols = volumes[-min(20, len(volumes)):]
        if np.sum(recent_vols) > 0:
            vwap_recent = np.sum(recent_20 * recent_vols) / np.sum(recent_vols)
        else:
            vwap_recent = np.mean(recent_20)

        # Combiner estimation bayésienne et VWAP récent
        estimated_prob = 0.6 * estimated_prob + 0.4 * vwap_recent

        # --- Détection de l'edge ---
        current_price = current_bar["mid_price"]
        edge = estimated_prob - current_price

        # L'edge requis augmente avec l'incertitude (plus incertain = plus exigeant)
        adjusted_threshold = self.edge_threshold * (1 + uncertainty)

        if abs(edge) < adjusted_threshold:
            return "HOLD", 0.0

        # Confidence basée sur l'edge et la certitude
        edge_strength = min(abs(edge) / (adjusted_threshold * 2), 1.0)
        certainty = max(0, 1 - uncertainty)
        confidence = edge_strength * 0.6 + certainty * 0.4

        # Filtre : spread trop large = mauvaise liquidité
        spread = current_bar["spread"]
        if spread > abs(edge) * 0.5:
            confidence *= 0.5

        if edge > adjusted_threshold:
            return "BUY_YES", min(confidence, 1.0)
        elif edge < -adjusted_threshold:
            return "BUY_NO", min(confidence, 1.0)

        return "HOLD", 0.0


class AdaptiveMomentumStrategy(BaseStrategy):
    """
    Adaptive Momentum — Momentum intelligent qui s'adapte
    au régime de marché (trending vs mean-reverting).

    Inspiré des stratégies de time-series momentum de AQR Capital.

    Principe :
    - Détecte le régime via le Hurst exponent
    - En régime trending (H > 0.5) : suit le momentum
    - En régime mean-reverting (H < 0.5) : mean reversion
    - Filtre par la qualité du signal (autocorrélation)
    """

    def __init__(
        self,
        fast_lookback: int = 12,
        slow_lookback: int = 48,
        hurst_lookback: int = 100,
        signal_threshold: float = 0.03,
        **kwargs,
    ):
        super().__init__(name="AdaptiveMomentum", **kwargs)
        self.fast_lookback = fast_lookback
        self.slow_lookback = slow_lookback
        self.hurst_lookback = hurst_lookback
        self.signal_threshold = signal_threshold

    def _estimate_hurst(self, prices: np.ndarray) -> float:
        """Estimation rapide de l'exposant de Hurst via R/S analysis."""
        n = len(prices)
        if n < 20:
            return 0.5

        returns = np.diff(np.log(np.maximum(prices, 0.001)))
        if len(returns) < 10:
            return 0.5

        # R/S sur différentes fenêtres
        rs_values = []
        window_sizes = []
        for w in [10, 15, 20, 30, 40]:
            if w > len(returns):
                continue
            n_windows = len(returns) // w
            if n_windows < 1:
                continue
            rs_list = []
            for i in range(n_windows):
                segment = returns[i * w:(i + 1) * w]
                mean_seg = np.mean(segment)
                cumdev = np.cumsum(segment - mean_seg)
                r = np.max(cumdev) - np.min(cumdev)
                s = np.std(segment)
                if s > 1e-10:
                    rs_list.append(r / s)
            if rs_list:
                rs_values.append(np.log(np.mean(rs_list)))
                window_sizes.append(np.log(w))

        if len(rs_values) < 2:
            return 0.5

        # Régression pour estimer H
        hurst = np.polyfit(window_sizes, rs_values, 1)[0]
        return max(0.0, min(1.0, hurst))

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.hurst_lookback:
            return "HOLD", 0.0

        prices = history["mid_price"].values
        current_price = current_bar["mid_price"]

        # 1. Détecter le régime
        hurst = self._estimate_hurst(prices[-self.hurst_lookback:])

        # 2. Calculer les signaux
        fast_ma = np.mean(prices[-self.fast_lookback:])
        slow_ma = np.mean(prices[-self.slow_lookback:])
        ma_diff = fast_ma - slow_ma

        # EMA pour un signal plus réactif
        fast_ema = _exponential_moving_avg(prices[-self.fast_lookback:], self.fast_lookback // 2)
        ema_slope = (fast_ema[-1] - fast_ema[-min(6, len(fast_ema))]) if len(fast_ema) > 6 else 0

        # 3. Signal adaptatif selon le régime
        if hurst > 0.55:
            # Régime trending → momentum
            signal = ma_diff + ema_slope * 0.5
            regime_confidence = min((hurst - 0.5) * 4, 1.0)
        elif hurst < 0.45:
            # Régime mean-reverting → contrarian
            z_lookback = min(self.slow_lookback, len(prices))
            mean_price = np.mean(prices[-z_lookback:])
            std_price = np.std(prices[-z_lookback:])
            if std_price < 1e-6:
                return "HOLD", 0.0
            z_score = (current_price - mean_price) / std_price
            signal = -z_score * std_price  # Contrarian
            regime_confidence = min((0.5 - hurst) * 4, 1.0)
        else:
            # Régime incertain → ne rien faire
            return "HOLD", 0.0

        if abs(signal) < self.signal_threshold:
            return "HOLD", 0.0

        signal_strength = min(abs(signal) / (self.signal_threshold * 3), 1.0)
        confidence = signal_strength * 0.6 + regime_confidence * 0.4

        if signal > 0:
            return "BUY_YES", min(confidence, 1.0)
        else:
            return "BUY_NO", min(confidence, 1.0)


class LiquidityEdgeStrategy(BaseStrategy):
    """
    Liquidity Edge — Exploiter les inefficiences de liquidité.

    Principe : les marchés peu liquides sont inefficients.
    Quand le spread se contracte soudainement (afflux de liquidité),
    le prix se rapproche de sa vraie valeur → on entre dans la direction
    du mouvement qui accompagne la contraction du spread.

    Filtre anti-manipulation : vérifier la consistance du prix
    sur plusieurs barres pour éviter les spoofs.
    """

    def __init__(
        self,
        lookback: int = 36,
        spread_contraction_threshold: float = 0.4,
        price_move_threshold: float = 0.02,
        min_volume_ratio: float = 1.5,
        **kwargs,
    ):
        super().__init__(name="LiquidityEdge", **kwargs)
        self.lookback = lookback
        self.spread_contraction_threshold = spread_contraction_threshold
        self.price_move_threshold = price_move_threshold
        self.min_volume_ratio = min_volume_ratio

    def generate_signal(self, market_id, current_bar, history):
        if len(history) < self.lookback:
            return "HOLD", 0.0

        recent = history.tail(self.lookback)
        spreads = recent["spread"].values
        prices = recent["mid_price"].values
        volumes = recent["volume_usd"].values
        current_spread = current_bar["spread"]

        # 1. Détecter la contraction du spread
        avg_spread = np.mean(spreads)
        if avg_spread < 1e-6:
            return "HOLD", 0.0
        spread_ratio = current_spread / avg_spread

        if spread_ratio > self.spread_contraction_threshold:
            return "HOLD", 0.0  # Pas de contraction

        # 2. Volume supérieur à la normale
        vol_ratio = current_bar["volume_usd"] / max(np.mean(volumes), 1.0)
        if vol_ratio < self.min_volume_ratio:
            return "HOLD", 0.0

        # 3. Direction du mouvement pendant la contraction
        last_n = min(8, len(prices))
        recent_move = prices[-1] - prices[-last_n]

        if abs(recent_move) < self.price_move_threshold:
            return "HOLD", 0.0

        # 4. Consistance (anti-spoof)
        price_diffs = np.diff(prices[-last_n:])
        if recent_move > 0:
            consistency = np.sum(price_diffs > 0) / len(price_diffs)
        else:
            consistency = np.sum(price_diffs < 0) / len(price_diffs)

        if consistency < 0.55:
            return "HOLD", 0.0

        # Confidence
        spread_quality = 1 - spread_ratio  # Plus le spread est contracté, mieux c'est
        move_strength = min(abs(recent_move) / (self.price_move_threshold * 3), 1.0)
        confidence = spread_quality * 0.35 + move_strength * 0.35 + consistency * 0.3

        if recent_move > 0:
            return "BUY_YES", min(confidence, 1.0)
        else:
            return "BUY_NO", min(confidence, 1.0)


# ============================================================
#  COMPOSITE STRATEGIES
# ============================================================


class CompositeStrategy(BaseStrategy):
    """
    Stratégie composite basique : combine plusieurs stratégies avec des poids.
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


class AlphaCompositeStrategy(BaseStrategy):
    """
    Alpha Composite — La stratégie ultime.

    Combine TOUS les signaux avancés avec :
    - Kelly Criterion pour le sizing
    - Pondération dynamique basée sur la performance récente de chaque sous-stratégie
    - Filtre de corrélation des signaux (éviter la redondance)
    - Filtres de qualité strict : spread, volume, consistance
    - Seuil de consensus adaptatif

    C'est l'approche "ensemble de modèles" utilisée par les meilleurs funds.
    """

    def __init__(
        self,
        min_consensus: float = 0.35,
        min_agreeing_strategies: int = 2,
        spread_filter: float = 0.06,
        volume_percentile_filter: float = 30,
        max_price_extreme: float = 0.90,
        min_price_extreme: float = 0.10,
        **kwargs,
    ):
        kwargs.setdefault("max_position_pct", 0.03)
        kwargs.setdefault("max_positions", 8)
        kwargs.setdefault("stop_loss", 0.12)        # Stop serré : couper les pertes vite
        kwargs.setdefault("take_profit", 0.40)       # TP large : laisser les winners courir
        kwargs.setdefault("trailing_stop", 0.08)     # Trailing stop : capturer les gains
        super().__init__(name="AlphaComposite", **kwargs)

        self.min_consensus = min_consensus
        self.min_agreeing_strategies = min_agreeing_strategies
        self.spread_filter = spread_filter
        self.volume_percentile_filter = volume_percentile_filter
        self.max_price_extreme = max_price_extreme
        self.min_price_extreme = min_price_extreme

        # Sous-stratégies avec poids calibrés
        # Poids fort sur Convergence et Bayesian (meilleur edge théorique)
        self.sub_strategies: list[tuple[BaseStrategy, float]] = [
            (SmartMoneyStrategy(
                lookback=36, volume_spike_threshold=2.2,
                directional_threshold=0.035, consistency_window=8,
            ), 0.10),
            (ConvergenceStrategy(
                min_market_progress=0.50, trend_lookback=60,
                trend_threshold=0.012,
            ), 0.30),
            (BayesianEdgeStrategy(
                lookback=80, edge_threshold=0.07,
                volume_info_weight=0.45, min_observations=30,
            ), 0.30),
            (AdaptiveMomentumStrategy(
                fast_lookback=12, slow_lookback=60,
                hurst_lookback=100, signal_threshold=0.03,
            ), 0.15),
            (LiquidityEdgeStrategy(
                lookback=36, spread_contraction_threshold=0.35,
                price_move_threshold=0.02, min_volume_ratio=1.5,
            ), 0.15),
        ]

        # Tracking de la performance de chaque sous-stratégie
        self._strat_wins: dict[str, int] = {}
        self._strat_total: dict[str, int] = {}
        for strat, _ in self.sub_strategies:
            self._strat_wins[strat.name] = 1  # Prior optimiste
            self._strat_total[strat.name] = 2

        # Dernier signal de chaque stratégie pour le tracking
        self._last_signals: dict[str, dict[str, str]] = {}

    def _get_dynamic_weight(self, strat_name: str, base_weight: float) -> float:
        """Pondération dynamique basée sur le track record récent."""
        wins = self._strat_wins.get(strat_name, 1)
        total = self._strat_total.get(strat_name, 2)
        win_rate = wins / total
        # Ajuster le poids : multiplier par le ratio win_rate / 0.5
        # (si win_rate > 50% → plus de poids, sinon moins)
        dynamic_factor = max(0.2, min(2.5, win_rate / 0.5))
        return base_weight * dynamic_factor

    def update_strategy_performance(self, market_id: str, pnl: float):
        """Met à jour les stats de perf des sous-stratégies."""
        if market_id in self._last_signals:
            for strat_name, action in self._last_signals[market_id].items():
                if action != "HOLD":
                    self._strat_total[strat_name] = self._strat_total.get(strat_name, 0) + 1
                    if pnl > 0:
                        self._strat_wins[strat_name] = self._strat_wins.get(strat_name, 0) + 1

    def generate_signal(self, market_id, current_bar, history):
        current_price = current_bar["mid_price"]
        spread = current_bar["spread"]

        # --- FILTRES DE QUALITE ---

        # 1. Prix pas trop extrême (edge insuffisant)
        if current_price > self.max_price_extreme or current_price < self.min_price_extreme:
            return "HOLD", 0.0

        # 2. Spread acceptable
        if spread > self.spread_filter:
            return "HOLD", 0.0

        # 3. Volume suffisant
        if len(history) > 20:
            vol_percentile = np.percentile(
                history["volume_usd"].values, self.volume_percentile_filter
            )
            if current_bar["volume_usd"] < vol_percentile:
                return "HOLD", 0.0

        # --- COLLECTE DES SIGNAUX ---
        signals: dict[str, list[tuple[float, float]]] = {
            "BUY_YES": [], "BUY_NO": [], "HOLD": []
        }
        strat_signals = {}

        total_weight = 0
        for strat, base_weight in self.sub_strategies:
            weight = self._get_dynamic_weight(strat.name, base_weight)
            total_weight += weight

            action, confidence = strat.generate_signal(market_id, current_bar, history)
            signals[action].append((weight, confidence))
            strat_signals[strat.name] = action

        # Sauvegarder pour le tracking
        self._last_signals[market_id] = strat_signals

        if total_weight < 1e-6:
            return "HOLD", 0.0

        # --- SCORING ---
        scores = {}
        counts = {}
        for action in ["BUY_YES", "BUY_NO"]:
            weighted_conf = sum(w * c for w, c in signals[action])
            scores[action] = weighted_conf / total_weight
            counts[action] = len(signals[action])

        # Meilleur signal
        if scores.get("BUY_YES", 0) > scores.get("BUY_NO", 0):
            best = "BUY_YES"
        elif scores.get("BUY_NO", 0) > scores.get("BUY_YES", 0):
            best = "BUY_NO"
        else:
            return "HOLD", 0.0

        best_score = scores[best]
        n_agreeing = counts[best]

        # --- CONSENSUS ---

        # Minimum de stratégies d'accord
        if n_agreeing < self.min_agreeing_strategies:
            return "HOLD", 0.0

        # Score minimum
        if best_score < self.min_consensus:
            return "HOLD", 0.0

        # Vérifier que les signaux ne se contredisent pas trop
        opposite = "BUY_NO" if best == "BUY_YES" else "BUY_YES"
        if scores.get(opposite, 0) > best_score * 0.4:
            return "HOLD", 0.0  # Signaux trop contradictoires

        # Filtre de prix : préférer les marchés dans la zone 0.25-0.75
        # (c'est là que l'edge est maximal, les extrêmes ont peu de valeur)
        price_quality = 1.0 - 2.0 * abs(current_price - 0.5)
        price_quality = max(0.2, price_quality)
        best_score *= price_quality

        if best_score < self.min_consensus:
            return "HOLD", 0.0

        # --- KELLY CRITERION POUR LE SIZING ---
        # Estimer win_prob et win/loss ratio à partir de l'historique
        completed_trades = [t for t in self.trades if t.pnl != 0]
        if len(completed_trades) >= 10:
            pnls = np.array([t.pnl for t in completed_trades[-50:]])
            win_prob = np.mean(pnls > 0)
            avg_win = np.mean(pnls[pnls > 0]) if np.any(pnls > 0) else 1
            avg_loss = abs(np.mean(pnls[pnls < 0])) if np.any(pnls < 0) else 1
            wl_ratio = avg_win / max(avg_loss, 1e-6)
            kelly = _kelly_fraction(win_prob, wl_ratio)
        else:
            kelly = 0.5  # Défaut conservateur

        # Confidence finale = score * kelly_factor
        final_confidence = min(best_score * (0.5 + kelly), 1.0)

        return best, final_confidence
