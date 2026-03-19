#!/usr/bin/env python3
"""
Stratégie Intraday Fader — 3 sous-stratégies combinées.

1. News Fade: Surréaction à une news → fade le mouvement
2. Volume Spike Fade: Volume anormal sans news confirmée → fade
3. Mean Reversion: Prix extrême (>90% ou <10%) → pari sur le retour

Gestion du risque intégrée: sizing dynamique, stop-loss, take-profit.
"""

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

logger = logging.getLogger("intraday_fader")


class SignalType(Enum):
    NEWS_FADE = "NEWS_FADE"
    VOLUME_SPIKE_FADE = "VOLUME_SPIKE_FADE"
    MEAN_REVERSION = "MEAN_REVERSION"


class Side(Enum):
    BUY_YES = "BUY_YES"   # On pense que le prix YES va monter
    BUY_NO = "BUY_NO"     # On pense que le prix YES va baisser


@dataclass
class TradeSignal:
    """Signal de trade généré par le fader."""
    signal_type: SignalType
    condition_id: str
    question: str
    side: Side
    entry_price: float       # Prix d'entrée cible
    target_price: float      # Take profit
    stop_price: float        # Stop loss
    size_usd: float          # Taille en USD
    confidence: float        # 0-1
    reasoning: str
    token_id: str = ""
    slug: str = ""
    max_hold_hours: float = 4.0  # Durée max de détention
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    risk_reward: float = 0.0


@dataclass
class RiskParams:
    """Paramètres de gestion du risque."""
    max_position_usd: float = 15.0      # Max par position
    min_position_usd: float = 3.0       # Min par position
    max_total_exposure: float = 50.0    # Exposure totale max
    max_concurrent_trades: int = 5
    max_daily_loss_usd: float = 25.0    # Stop journalier
    min_risk_reward: float = 1.5        # R/R minimum
    max_spread_pct: float = 5.0         # Spread max acceptable
    min_liquidity_usd: float = 1000.0   # Liquidité min
    min_confidence: float = 0.30        # Confidence min pour trader


class IntradayFader:
    """
    Moteur de décision du fader intraday.
    Combine les 3 sous-stratégies et génère des signaux de trade.
    """

    def __init__(self, risk_params: Optional[RiskParams] = None,
                 bankroll: float = 100.0):
        self.risk = risk_params or RiskParams()
        self.bankroll = bankroll
        self.daily_pnl = 0.0
        self.open_positions: List[dict] = []
        self.trade_history: List[dict] = []
        self._last_reset = datetime.now(timezone.utc).date()

    def _reset_daily(self):
        """Reset PnL journalier à minuit UTC."""
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset:
            logger.info(f"Reset journalier. PnL hier: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self._last_reset = today

    def is_trading_allowed(self) -> Tuple[bool, str]:
        """Vérifie si on peut encore trader aujourd'hui."""
        self._reset_daily()

        if self.daily_pnl <= -self.risk.max_daily_loss_usd:
            return False, f"Stop journalier atteint (${self.daily_pnl:.2f})"

        current_exposure = sum(p.get("size_usd", 0) for p in self.open_positions)
        if current_exposure >= self.risk.max_total_exposure:
            return False, f"Exposure max atteinte (${current_exposure:.2f})"

        if len(self.open_positions) >= self.risk.max_concurrent_trades:
            return False, f"Max {self.risk.max_concurrent_trades} trades simultanés"

        return True, "OK"

    # ── Sous-stratégie 1: News Fade ──

    def evaluate_news_fade(self, price_move, news_items: list) -> Optional[TradeSignal]:
        """
        Stratégie: Une news sort → le marché surréagit → on fade.

        Conditions:
        - Mouvement >5% en <30 min
        - News identifiée mais sentiment exagéré
        - Volume spike confirme la panique/FOMO
        """
        if abs(price_move.price_change_pct) < 5:
            return None

        if price_move.fade_confidence < self.risk.min_confidence:
            return None

        # Déterminer le côté
        if price_move.price_change_pct > 0:
            # Prix a monté → on pense qu'il va redescendre → BUY NO
            side = Side.BUY_NO
            entry = price_move.price_now
            # Target: retour partiel (50% du mouvement)
            revert = abs(price_move.price_change_pct) * 0.5 / 100
            target = entry - revert
            stop = entry + revert * 0.7  # Stop plus serré
        else:
            # Prix a baissé → on pense qu'il va remonter → BUY YES
            side = Side.BUY_YES
            entry = price_move.price_now
            revert = abs(price_move.price_change_pct) * 0.5 / 100
            target = entry + revert
            stop = entry - revert * 0.7

        # Risk/reward
        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk == 0:
            return None
        rr = reward / risk

        if rr < self.risk.min_risk_reward:
            return None

        # Bonus confidence si news multiples confirment surréaction
        conf = price_move.fade_confidence
        if news_items:
            # News existe mais mouvement excessif
            conf = min(1.0, conf + 0.1)

        size = self._calculate_size(conf, risk)

        reasoning_parts = [
            f"Move {price_move.price_change_pct:+.1f}% en {price_move.time_window_minutes}min",
            f"Vol spike {price_move.volume_spike_ratio:.1f}x",
        ]
        if news_items:
            reasoning_parts.append(f"{len(news_items)} news liées")
        reasoning_parts.append(f"R/R={rr:.1f}")

        token_id = ""
        if price_move.tokens:
            # YES token = index 0, NO token = index 1
            idx = 0 if side == Side.BUY_YES else (1 if len(price_move.tokens) > 1 else 0)
            token_id = price_move.tokens[idx]

        return TradeSignal(
            signal_type=SignalType.NEWS_FADE,
            condition_id=price_move.condition_id,
            question=price_move.question,
            side=side,
            entry_price=entry,
            target_price=target,
            stop_price=stop,
            size_usd=size,
            confidence=conf,
            reasoning=" | ".join(reasoning_parts),
            token_id=token_id,
            slug=price_move.slug,
            risk_reward=rr,
            max_hold_hours=2.0,
        )

    # ── Sous-stratégie 2: Volume Spike Fade ──

    def evaluate_volume_spike(self, market, vol_ratio: float,
                                orderbook=None) -> Optional[TradeSignal]:
        """
        Stratégie: Volume spike sans news claire → probablement du bruit.

        Conditions:
        - Volume >5x baseline
        - Pas de news majeure identifiée
        - Carnet d'ordres déséquilibré
        """
        if vol_ratio < 5.0:
            return None

        price = market.yes_price

        # Détecter la direction du déséquilibre
        if orderbook:
            imbalance = orderbook.imbalance
            spread = orderbook.spread

            if spread / max(price, 0.01) > self.risk.max_spread_pct / 100:
                return None  # Spread trop large

            # Imbalance positive = trop d'acheteurs = prix va monter artificiellement
            # → on vend (BUY NO)
            if abs(imbalance) < 0.15:
                return None  # Pas assez de déséquilibre

            if imbalance > 0.15:
                side = Side.BUY_NO
                entry = price
                target = price - 0.03
                stop = price + 0.02
            else:
                side = Side.BUY_YES
                entry = price
                target = price + 0.03
                stop = price - 0.02
        else:
            # Sans orderbook, on utilise le prix pour deviner
            if price > 0.65:
                side = Side.BUY_NO
                entry = price
                target = price - 0.04
                stop = price + 0.025
            elif price < 0.35:
                side = Side.BUY_YES
                entry = price
                target = price + 0.04
                stop = price - 0.025
            else:
                return None  # Prix neutre, pas de signal

        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk == 0:
            return None
        rr = reward / risk

        if rr < self.risk.min_risk_reward:
            return None

        # Confidence basée sur le ratio de volume
        conf = min(0.6, 0.2 + (vol_ratio - 5) * 0.04)

        size = self._calculate_size(conf, risk)

        token_id = ""
        if market.tokens:
            idx = 0 if side == Side.BUY_YES else (1 if len(market.tokens) > 1 else 0)
            token_id = market.tokens[idx]

        return TradeSignal(
            signal_type=SignalType.VOLUME_SPIKE_FADE,
            condition_id=market.condition_id,
            question=market.question,
            side=side,
            entry_price=entry,
            target_price=target,
            stop_price=stop,
            size_usd=size,
            confidence=conf,
            reasoning=f"Vol spike {vol_ratio:.1f}x | "
                      f"{'OB imbalance ' + f'{orderbook.imbalance:.2f}' if orderbook else 'No OB'} | "
                      f"R/R={rr:.1f}",
            token_id=token_id,
            slug=market.slug,
            risk_reward=rr,
            max_hold_hours=1.5,
        )

    # ── Sous-stratégie 3: Mean Reversion ──

    def evaluate_mean_reversion(self, market,
                                  hours_to_resolution: float) -> Optional[TradeSignal]:
        """
        Stratégie: Prix extrême (>90% ou <10%) → pari sur le retour au centre.

        Conditions:
        - Prix >90¢ ou <10¢
        - Résolution dans >6h (pas trop proche)
        - Pas de raison fondamentale claire pour l'extrême
        """
        price = market.yes_price

        if hours_to_resolution < 6:
            return None  # Trop proche de la résolution

        if hours_to_resolution > 72:
            return None  # Trop loin, pas assez de edge

        if market.liquidity < self.risk.min_liquidity_usd:
            return None

        # Seuils de mean reversion
        if price >= 0.92:
            side = Side.BUY_NO
            entry = 1.0 - price  # Prix du NO
            target_yes = 0.85  # On vise un retour à 85¢
            target = 1.0 - target_yes
            stop_yes = 0.97
            stop = 1.0 - stop_yes
        elif price <= 0.08:
            side = Side.BUY_YES
            entry = price
            target = 0.15
            stop = 0.03
        else:
            return None

        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk == 0:
            return None
        rr = reward / risk

        if rr < self.risk.min_risk_reward:
            return None

        # Plus le prix est extrême, plus la confidence est haute
        extremity = max(price, 1.0 - price)  # Distance from 50%
        conf = min(0.55, 0.15 + (extremity - 0.85) * 3)

        if conf < self.risk.min_confidence:
            return None

        size = self._calculate_size(conf, risk)

        token_id = ""
        if market.tokens:
            idx = 0 if side == Side.BUY_YES else (1 if len(market.tokens) > 1 else 0)
            token_id = market.tokens[idx]

        return TradeSignal(
            signal_type=SignalType.MEAN_REVERSION,
            condition_id=market.condition_id,
            question=market.question,
            side=side,
            entry_price=entry,
            target_price=target,
            stop_price=stop,
            size_usd=size,
            confidence=conf,
            reasoning=f"Prix extrême {price:.0%} | {hours_to_resolution:.0f}h avant résolution | R/R={rr:.1f}",
            token_id=token_id,
            slug=market.slug,
            risk_reward=rr,
            max_hold_hours=min(hours_to_resolution * 0.5, 8.0),
        )

    # ── Position management ──

    def check_exits(self, current_prices: dict) -> List[dict]:
        """
        Vérifie les conditions de sortie pour toutes les positions ouvertes.
        Retourne les positions à fermer.
        """
        now = datetime.now(timezone.utc)
        exits = []

        for pos in self.open_positions:
            cid = pos["condition_id"]
            current_price = current_prices.get(cid)
            if current_price is None:
                continue

            exit_reason = None

            # Take profit
            if pos["side"] == Side.BUY_YES.value:
                if current_price >= pos["target_price"]:
                    exit_reason = "TAKE_PROFIT"
                elif current_price <= pos["stop_price"]:
                    exit_reason = "STOP_LOSS"
            else:  # BUY_NO
                no_price = 1.0 - current_price
                if no_price >= pos["target_price"]:
                    exit_reason = "TAKE_PROFIT"
                elif no_price <= pos["stop_price"]:
                    exit_reason = "STOP_LOSS"

            # Time stop
            entry_time = datetime.fromisoformat(pos["entry_time"])
            hours_held = (now - entry_time).total_seconds() / 3600
            if hours_held >= pos.get("max_hold_hours", 4.0):
                exit_reason = "TIME_STOP"

            if exit_reason:
                pnl = self._estimate_pnl(pos, current_price)
                exits.append({
                    "position": pos,
                    "exit_reason": exit_reason,
                    "exit_price": current_price,
                    "pnl_usd": pnl,
                    "hours_held": hours_held,
                })

        return exits

    def record_exit(self, pos: dict, exit_price: float, pnl: float, reason: str):
        """Enregistre une sortie de position."""
        self.daily_pnl += pnl
        pos["exit_price"] = exit_price
        pos["exit_reason"] = reason
        pos["pnl"] = pnl
        pos["exit_time"] = datetime.now(timezone.utc).isoformat()
        self.trade_history.append(pos)
        self.open_positions = [
            p for p in self.open_positions if p["condition_id"] != pos["condition_id"]
        ]
        logger.info(
            f"EXIT [{reason}] PnL=${pnl:+.2f} | "
            f"Daily=${self.daily_pnl:+.2f} | {pos['question'][:50]}"
        )

    def record_entry(self, signal: TradeSignal, actual_price: float):
        """Enregistre une entrée de position."""
        pos = {
            "condition_id": signal.condition_id,
            "question": signal.question,
            "side": signal.side.value,
            "entry_price": actual_price,
            "target_price": signal.target_price,
            "stop_price": signal.stop_price,
            "size_usd": signal.size_usd,
            "token_id": signal.token_id,
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
            "max_hold_hours": signal.max_hold_hours,
            "entry_time": datetime.now(timezone.utc).isoformat(),
        }
        self.open_positions.append(pos)
        logger.info(
            f"ENTRY [{signal.signal_type.value}] {signal.side.value} "
            f"${signal.size_usd:.2f} @ {actual_price:.4f} | "
            f"TP={signal.target_price:.4f} SL={signal.stop_price:.4f} | "
            f"{signal.question[:50]}"
        )

    # ── Helpers ──

    def _calculate_size(self, confidence: float, risk_per_unit: float) -> float:
        """
        Position sizing basé sur Kelly Criterion simplifié.
        size = bankroll * edge * confidence / risk
        """
        # Kelly fraction (conservative: half-Kelly)
        edge = confidence * 0.5  # On assume un edge proportionnel à confidence
        kelly = edge / max(risk_per_unit, 0.01)
        raw_size = self.bankroll * kelly * 0.5  # Half Kelly

        # Clamp aux limites
        size = max(self.risk.min_position_usd, min(self.risk.max_position_usd, raw_size))

        # Réduire si proche du stop journalier
        remaining = self.risk.max_daily_loss_usd + self.daily_pnl
        if remaining < size:
            size = max(self.risk.min_position_usd, remaining * 0.5)

        return round(size, 2)

    def _estimate_pnl(self, pos: dict, current_price: float) -> float:
        """Estime le PnL d'une position."""
        entry = pos["entry_price"]
        size = pos["size_usd"]

        if pos["side"] == Side.BUY_YES.value:
            # Acheté YES à entry, maintenant vaut current_price
            shares = size / max(entry, 0.01)
            pnl = shares * (current_price - entry)
        else:
            # Acheté NO à (1-entry), NO vaut maintenant (1-current_price)
            no_entry = 1.0 - entry
            no_current = 1.0 - current_price
            shares = size / max(no_entry, 0.01)
            pnl = shares * (no_current - no_entry)

        return round(pnl, 2)

    def get_stats(self) -> dict:
        """Retourne les stats de trading."""
        wins = [t for t in self.trade_history if t.get("pnl", 0) > 0]
        losses = [t for t in self.trade_history if t.get("pnl", 0) <= 0]
        total_pnl = sum(t.get("pnl", 0) for t in self.trade_history)

        return {
            "total_trades": len(self.trade_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / max(len(self.trade_history), 1),
            "total_pnl": round(total_pnl, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "open_positions": len(self.open_positions),
            "avg_win": round(sum(t.get("pnl", 0) for t in wins) / max(len(wins), 1), 2),
            "avg_loss": round(sum(t.get("pnl", 0) for t in losses) / max(len(losses), 1), 2),
        }
