#!/usr/bin/env python3
"""
Détecteur de volume spikes et mouvements de prix Polymarket.
Identifie les surréactions en temps réel pour le fading intraday.
"""

import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Dict, Optional, Tuple
from threading import Thread, Lock

logger = logging.getLogger("volume_detector")

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


@dataclass
class MarketSnapshot:
    """Snapshot d'un marché à un instant T."""
    condition_id: str
    question: str
    yes_price: float
    volume_24h: float
    liquidity: float
    timestamp: datetime
    end_date: Optional[datetime] = None
    slug: str = ""
    tokens: list = field(default_factory=list)
    category: str = ""


@dataclass
class PriceMove:
    """Un mouvement de prix significatif détecté."""
    condition_id: str
    question: str
    price_before: float
    price_now: float
    price_change_pct: float
    volume_spike_ratio: float
    time_window_minutes: int
    detected_at: datetime
    end_date: Optional[datetime] = None
    tokens: list = field(default_factory=list)
    slug: str = ""
    move_type: str = ""  # "SPIKE_UP", "SPIKE_DOWN", "REVERSAL"
    fade_confidence: float = 0.0  # 0-1, probabilité que le move se reverse


@dataclass
class OrderBookState:
    """État du carnet d'ordres."""
    condition_id: str
    best_bid: float
    best_ask: float
    spread: float
    bid_depth_usd: float
    ask_depth_usd: float
    imbalance: float  # >0 = plus d'acheteurs, <0 = plus de vendeurs


class VolumeDetector:
    """
    Monitore les marchés Polymarket en continu pour détecter :
    1. Volume spikes (5x+ la baseline)
    2. Mouvements de prix rapides (>5% en 15 min)
    3. Déséquilibres du carnet d'ordres
    """

    def __init__(self, scan_interval: int = 45, max_days_to_resolution: int = 7):
        self.scan_interval = scan_interval
        self.max_days_to_resolution = max_days_to_resolution
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.volume_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.volume_baselines: Dict[str, float] = defaultdict(float)
        self.active_markets: Dict[str, MarketSnapshot] = {}
        self.detected_moves: List[PriceMove] = []
        self._lock = Lock()
        self._running = False

    def start_background(self):
        """Lance le monitoring en arrière-plan."""
        self._running = True
        thread = Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        logger.info(f"VolumeDetector démarré (scan toutes les {self.scan_interval}s, "
                     f"marchés ≤{self.max_days_to_resolution}j)")

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            try:
                self._refresh_markets()
                self._check_price_moves()
                self._cleanup()
            except Exception as e:
                logger.error(f"VolumeDetector erreur: {e}")
            time.sleep(self.scan_interval)

    def _refresh_markets(self):
        """Récupère tous les marchés actifs à court terme."""
        try:
            markets = []
            offset = 0
            while True:
                resp = requests.get(
                    f"{GAMMA_API}/markets",
                    params={
                        "closed": "false",
                        "active": "true",
                        "limit": 100,
                        "offset": offset,
                    },
                    timeout=15,
                )
                if not resp.ok:
                    break
                batch = resp.json()
                if not batch:
                    break
                markets.extend(batch)
                if len(batch) < 100:
                    break
                offset += 100
                time.sleep(0.3)

            now = datetime.now(timezone.utc)
            updated = 0

            for m in markets:
                try:
                    end_str = m.get("endDate") or m.get("end_date_iso") or ""
                    if not end_str:
                        continue

                    end_date = datetime.fromisoformat(
                        end_str.replace("Z", "+00:00")
                    )
                    days_left = (end_date - now).total_seconds() / 86400

                    # Filtre: marchés à court terme uniquement
                    if days_left > self.max_days_to_resolution or days_left < 0:
                        continue

                    cid = m.get("conditionId") or m.get("condition_id", "")
                    if not cid:
                        continue

                    # Extraire les prix
                    yes_price = 0.5
                    outcomes = m.get("outcomePrices") or m.get("outcomes", "")
                    if isinstance(outcomes, str) and outcomes:
                        try:
                            import json
                            prices = json.loads(outcomes)
                            if prices:
                                yes_price = float(prices[0])
                        except (json.JSONDecodeError, IndexError, ValueError):
                            pass
                    elif isinstance(outcomes, list) and outcomes:
                        try:
                            yes_price = float(outcomes[0])
                        except (ValueError, IndexError):
                            pass

                    volume = float(m.get("volume", 0) or 0)
                    volume_24h = float(m.get("volume24hr", 0) or m.get("volume24h", 0) or 0)
                    liquidity = float(m.get("liquidity", 0) or 0)

                    # Minimum de liquidité pour être tradeable
                    if liquidity < 500 or volume < 1000:
                        continue

                    tokens = []
                    clob_ids = m.get("clobTokenIds") or ""
                    if isinstance(clob_ids, str) and clob_ids:
                        try:
                            import json
                            tokens = json.loads(clob_ids)
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(clob_ids, list):
                        tokens = clob_ids

                    snapshot = MarketSnapshot(
                        condition_id=cid,
                        question=m.get("question", ""),
                        yes_price=yes_price,
                        volume_24h=volume_24h,
                        liquidity=liquidity,
                        timestamp=now,
                        end_date=end_date,
                        slug=m.get("slug", ""),
                        tokens=tokens,
                        category=m.get("category", ""),
                    )

                    # Track price history
                    self.price_history[cid].append((now, yes_price))
                    self.volume_history[cid].append((now, volume_24h))

                    # Update baseline (EMA lente)
                    old_baseline = self.volume_baselines[cid]
                    if old_baseline == 0:
                        self.volume_baselines[cid] = volume_24h
                    else:
                        self.volume_baselines[cid] = 0.9 * old_baseline + 0.1 * volume_24h

                    with self._lock:
                        self.active_markets[cid] = snapshot
                    updated += 1

                except Exception:
                    continue

            logger.info(f"📊 {updated} marchés court terme monitorés "
                        f"(≤{self.max_days_to_resolution}j)")

        except Exception as e:
            logger.error(f"Refresh markets erreur: {e}")

    def _check_price_moves(self):
        """Détecte les mouvements de prix significatifs."""
        now = datetime.now(timezone.utc)
        new_moves = []

        for cid, history in self.price_history.items():
            if len(history) < 2:
                continue

            current_price = history[-1][1]
            market = self.active_markets.get(cid)
            if not market:
                continue

            # Vérifier sur différentes fenêtres de temps
            for window_min in [5, 15, 30, 60]:
                cutoff = now - timedelta(minutes=window_min)
                old_prices = [p for t, p in history if t < cutoff]
                if not old_prices:
                    continue

                ref_price = old_prices[-1]  # Prix le plus récent avant la fenêtre
                if ref_price == 0:
                    continue

                change_pct = (current_price - ref_price) / ref_price * 100

                # Seuil dynamique selon la fenêtre
                threshold = {5: 3.0, 15: 5.0, 30: 8.0, 60: 12.0}[window_min]

                if abs(change_pct) < threshold:
                    continue

                # Volume spike?
                baseline = self.volume_baselines.get(cid, 0)
                current_vol = market.volume_24h
                vol_ratio = current_vol / max(baseline, 1.0)

                # Déterminer le type de mouvement
                if change_pct > 0:
                    move_type = "SPIKE_UP"
                else:
                    move_type = "SPIKE_DOWN"

                # Vérifier s'il y a un reversal en cours
                if len(history) >= 3:
                    mid_price = history[-2][1]
                    if change_pct > 0 and mid_price > current_price:
                        move_type = "REVERSAL_DOWN"
                    elif change_pct < 0 and mid_price < current_price:
                        move_type = "REVERSAL_UP"

                # Confidence du fade
                fade_conf = self._calculate_fade_confidence(
                    change_pct, vol_ratio, window_min, market
                )

                # Éviter les doublons récents
                existing = [
                    m for m in self.detected_moves
                    if m.condition_id == cid
                    and now - m.detected_at < timedelta(minutes=max(window_min, 10))
                ]
                if existing:
                    continue

                move = PriceMove(
                    condition_id=cid,
                    question=market.question,
                    price_before=ref_price,
                    price_now=current_price,
                    price_change_pct=change_pct,
                    volume_spike_ratio=vol_ratio,
                    time_window_minutes=window_min,
                    detected_at=now,
                    end_date=market.end_date,
                    tokens=market.tokens,
                    slug=market.slug,
                    move_type=move_type,
                    fade_confidence=fade_conf,
                )
                new_moves.append(move)

        with self._lock:
            self.detected_moves.extend(new_moves)

        for move in new_moves:
            emoji = "🔴" if move.price_change_pct < 0 else "🟢"
            logger.warning(
                f"{emoji} MOVE: {move.move_type} | "
                f"{move.price_change_pct:+.1f}% en {move.time_window_minutes}min | "
                f"vol={move.volume_spike_ratio:.1f}x | "
                f"fade_conf={move.fade_confidence:.0%} | "
                f"{move.question[:60]}"
            )

    def _calculate_fade_confidence(self, change_pct: float,
                                     vol_ratio: float,
                                     window_min: int,
                                     market: MarketSnapshot) -> float:
        """
        Calcule la probabilité que le mouvement se reverse (fade).

        Principes des meilleurs faders:
        1. Plus le mouvement est rapide, plus il est probable qu'il se reverse
        2. Les spikes de volume sans confirmation multi-source sont souvent faux
        3. Les prix extrêmes (>90% ou <10%) ont une tendance naturelle à revenir
        4. Les marchés avec plus de liquidité sont plus efficients (moins de fading)
        """
        conf = 0.0

        # 1. Magnitude du mouvement (surréaction)
        abs_change = abs(change_pct)
        if abs_change > 20:
            conf += 0.30  # Mouvement extrême = forte probabilité de reversal
        elif abs_change > 10:
            conf += 0.20
        elif abs_change > 5:
            conf += 0.10

        # 2. Rapidité (mouvement rapide = moins réfléchi)
        speed_factor = abs_change / max(window_min, 1)
        if speed_factor > 2.0:
            conf += 0.20
        elif speed_factor > 1.0:
            conf += 0.10

        # 3. Volume spike (volume élevé sans news = panic/FOMO)
        if vol_ratio > 10:
            conf += 0.15
        elif vol_ratio > 5:
            conf += 0.10
        elif vol_ratio > 2:
            conf += 0.05

        # 4. Prix extrême (mean reversion)
        price = market.yes_price
        if price > 0.92 or price < 0.08:
            conf += 0.15  # Extrême
        elif price > 0.85 or price < 0.15:
            conf += 0.08

        # 5. Pénalité: marché très liquide = mouvement plus légitime
        if market.liquidity > 50000:
            conf -= 0.10
        elif market.liquidity > 20000:
            conf -= 0.05

        # 6. Pénalité: proche de la résolution (le marché a raison)
        if market.end_date:
            hours_left = (market.end_date - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_left < 2:
                conf -= 0.20  # Trop proche, probablement légitime
            elif hours_left < 6:
                conf -= 0.10

        return max(0.0, min(1.0, conf))

    def get_fade_opportunities(self, min_confidence: float = 0.25,
                                minutes: int = 30) -> List[PriceMove]:
        """Retourne les opportunités de fading triées par confidence."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        with self._lock:
            opps = [
                m for m in self.detected_moves
                if m.detected_at > cutoff
                and m.fade_confidence >= min_confidence
            ]
        return sorted(opps, key=lambda m: m.fade_confidence, reverse=True)

    def get_volume_spikes(self, min_ratio: float = 3.0) -> List[MarketSnapshot]:
        """Retourne les marchés avec volume spike actif."""
        with self._lock:
            markets_copy = dict(self.active_markets)
            baselines_copy = dict(self.volume_baselines)
        spikes = []
        for cid, market in markets_copy.items():
            baseline = baselines_copy.get(cid, 0)
            if baseline == 0:
                continue
            ratio = market.volume_24h / baseline
            if ratio >= min_ratio:
                spikes.append(market)
        return sorted(spikes, key=lambda m: m.volume_24h, reverse=True)

    def get_orderbook(self, token_id: str) -> Optional[OrderBookState]:
        """Récupère l'état du carnet d'ordres pour un token."""
        try:
            resp = requests.get(
                f"{CLOB_API}/book",
                params={"token_id": token_id},
                timeout=8,
            )
            if not resp.ok:
                return None

            book = resp.json()
            bids = book.get("bids", [])
            asks = book.get("asks", [])

            if not bids or not asks:
                return None

            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])

            bid_depth = sum(float(b["size"]) * float(b["price"]) for b in bids[:10])
            ask_depth = sum(float(a["size"]) * float(a["price"]) for a in asks[:10])

            total_depth = bid_depth + ask_depth
            imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0

            return OrderBookState(
                condition_id="",
                best_bid=best_bid,
                best_ask=best_ask,
                spread=best_ask - best_bid,
                bid_depth_usd=bid_depth,
                ask_depth_usd=ask_depth,
                imbalance=imbalance,
            )
        except Exception:
            return None

    def get_short_term_markets(self) -> Dict[str, MarketSnapshot]:
        """Retourne tous les marchés court terme monitorés."""
        with self._lock:
            return dict(self.active_markets)

    def _cleanup(self):
        """Nettoie les données anciennes."""
        now = datetime.now(timezone.utc)
        cutoff_history = now - timedelta(hours=6)
        cutoff_moves = now - timedelta(hours=2)

        for cid in list(self.price_history.keys()):
            self.price_history[cid] = [
                (t, p) for t, p in self.price_history[cid] if t > cutoff_history
            ]
            if not self.price_history[cid]:
                del self.price_history[cid]

        for cid in list(self.volume_history.keys()):
            self.volume_history[cid] = [
                (t, v) for t, v in self.volume_history[cid] if t > cutoff_history
            ]

        with self._lock:
            self.detected_moves = [
                m for m in self.detected_moves if m.detected_at > cutoff_moves
            ]

        # Retirer les marchés expirés
        with self._lock:
            for cid in list(self.active_markets.keys()):
                m = self.active_markets[cid]
                if m.end_date and m.end_date < now:
                    del self.active_markets[cid]
