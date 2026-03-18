#!/usr/bin/env python3
"""
Insurance Seller Bot — Réplique la stratégie d'anoin123 ($1.45M profit Polymarket).

Bot de trading autonome qui :
1. Scanne les marchés Polymarket en continu
2. Détecte la panique via le sentiment (News + VADER)
3. Achète du NO quand le YES est surévalué par la peur
4. Gère le risque avec stop-loss, trailing stop, daily limits
5. Envoie des notifications Telegram en temps réel

Usage :
    # Paper trading (défaut, aucune clé requise)
    python insurance_bot.py

    # Paper trading avec config custom
    python insurance_bot.py --capital 5000 --scan-interval 120

    # Real money trading
    python insurance_bot.py --real-money --private-key 0x... --capital 10000

    # Avec notifications Telegram
    python insurance_bot.py --telegram-token BOT_TOKEN --telegram-chat CHAT_ID
"""

import argparse
import json
import os
import sys
import time
import signal
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── Imports internes ────────────────────────────────────────────
from backtest.polymarket_client import (
    PolymarketClient,
    PolymarketTradingClient,
    PolymarketMarket,
)
from backtest.strategies import InsuranceSellerStrategy, Position
from backtest.sentiment import SentimentAnalyzer

# ── Logging ─────────────────────────────────────────────────────
LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("insurance_bot")


# ================================================================
#  CONFIGURATION
# ================================================================

@dataclass
class BotConfig:
    """Configuration complète du bot."""

    # ── Capital & Sizing ──
    initial_capital: float = 1000.0
    max_position_pct: float = 0.10        # 10% max par position (anoin123 taille gros)
    max_total_exposure_pct: float = 0.40   # 40% max d'exposition totale
    max_positions: int = 6

    # ── Filtres marchés ──
    min_market_volume: float = 20000       # Volume min ($)
    min_market_liquidity: float = 2000     # Liquidité min ($)
    max_markets_to_scan: int = 80          # Nombre de marchés à scanner
    min_spread: float = 0.003
    max_spread: float = 0.10

    # ── Stratégie Insurance Seller ──
    max_no_price: float = 0.35             # Acheter NO seulement si < 35 cents
    min_yes_price: float = 0.65            # YES doit être > 65%
    ideal_no_price: float = 0.10           # Zone idéale : NO < 10 cents
    panic_threshold: float = -0.15         # Sentiment < -0.15 = panique
    fear_multiplier: float = 1.5
    max_entries_per_market: int = 5
    entry_cooldown_bars: int = 12
    hard_stop_loss: float = 0.40           # Stop-loss dur (leçon anoin123)
    take_profit: float = 0.80

    # ── Exécution ──
    scan_interval_seconds: int = 300       # Scan toutes les 5 min
    history_fidelity: int = 60             # 1h par barre
    order_type: str = "limit"              # "limit" ou "market"
    limit_offset: float = 0.005

    # ── Risk ──
    daily_loss_limit_pct: float = 0.05     # Stop trading si -5% dans la journée

    # ── Mode ──
    dry_run: bool = True                   # Paper trading par défaut

    # ── Notifications ──
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # ── Fichiers ──
    log_dir: str = "logs/insurance_bot"
    state_file: str = "logs/insurance_bot/state.json"


# ================================================================
#  NOTIFICATIONS TELEGRAM
# ================================================================

class TelegramNotifier:
    """Envoie des alertes Telegram."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
        if self.enabled:
            logger.info("Telegram notifications ACTIVE")

    def send(self, message: str, silent: bool = False):
        if not self.enabled:
            return
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_notification": silent,
            }, timeout=10)
        except Exception as e:
            logger.warning(f"Telegram error: {e}")

    def trade_alert(self, action: str, market: str, price: float,
                    size: float, confidence: float):
        emoji = "🟢" if "OPEN" in action else "🔴"
        self.send(
            f"{emoji} <b>{action}</b>\n"
            f"📊 {market[:60]}\n"
            f"💰 ${size:.0f} @ {price:.3f} (conf: {confidence:.0%})\n"
            f"⏰ {datetime.now():%H:%M:%S}"
        )

    def status_alert(self, equity: float, pnl: float, n_positions: int):
        arrow = "📈" if pnl >= 0 else "📉"
        self.send(
            f"{arrow} <b>Status Update</b>\n"
            f"💼 Equity: ${equity:,.0f}\n"
            f"📊 PnL: ${pnl:+,.2f}\n"
            f"📋 Positions: {n_positions}",
            silent=True,
        )


# ================================================================
#  LIVE POSITION
# ================================================================

@dataclass
class BotPosition:
    """Position ouverte par le bot."""
    market: PolymarketMarket
    side: str              # "NO" (toujours NO pour cette stratégie)
    token_id: str
    entry_price: float     # Prix du NO
    size_usd: float
    shares: float
    entry_time: datetime
    confidence: float
    order_id: str = ""
    peak_price: float = 0.0
    entry_number: int = 1  # Numéro d'entrée sur ce marché

    def unrealized_pnl(self, current_no_price: float) -> float:
        """PnL non réalisé."""
        return (current_no_price - self.entry_price) * self.shares

    def unrealized_pnl_pct(self, current_no_price: float) -> float:
        """PnL non réalisé en %."""
        if self.entry_price <= 0:
            return 0.0
        return (current_no_price - self.entry_price) / self.entry_price


# ================================================================
#  BOT PRINCIPAL
# ================================================================

class InsuranceBot:
    """
    Bot de trading autonome basé sur la stratégie Insurance Seller.

    Réplique le comportement d'anoin123 :
    - Scanne les marchés Polymarket
    - Détecte la panique via le sentiment
    - Achète NO quand le YES est surévalué
    - Gère le risque strictement
    """

    def __init__(self, config: BotConfig, private_key: str | None = None):
        self.config = config
        self.capital = config.initial_capital
        self.positions: dict[str, BotPosition] = {}
        self.trade_log: list[dict] = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.start_time = datetime.now()
        self.iteration = 0
        self._running = True

        # ── Clients API ──
        self.client = PolymarketClient(rate_limit_delay=0.3)
        self.trading_client = None
        if not config.dry_run and private_key:
            self.trading_client = PolymarketTradingClient(private_key)

        # ── Stratégie ──
        self.strategy = InsuranceSellerStrategy(
            max_no_price=config.max_no_price,
            min_yes_price=config.min_yes_price,
            ideal_no_price=config.ideal_no_price,
            panic_threshold=config.panic_threshold,
            fear_multiplier=config.fear_multiplier,
            max_entries_per_market=config.max_entries_per_market,
            entry_cooldown_bars=config.entry_cooldown_bars,
            max_exposure_pct=config.max_total_exposure_pct,
            hard_stop_loss=config.hard_stop_loss,
            max_position_pct=config.max_position_pct,
            max_positions=config.max_positions,
            take_profit=config.take_profit,
            stop_loss=config.hard_stop_loss,
            trailing_stop=0.15,
        )

        # ── Notifications ──
        self.notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)

        # ── Cache historiques ──
        self._histories: dict[str, pd.DataFrame] = {}
        self._last_refresh: dict[str, datetime] = {}

        # ── Setup logging & fichiers ──
        self._setup_logging()
        self._load_state()

        # ── Signal handler ──
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("Signal reçu, arrêt propre...")
        self._running = False

    def _setup_logging(self):
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(LOG_FMT, LOG_DATE_FMT))

        # File handler
        fh = logging.FileHandler(
            log_dir / f"bot_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(LOG_FMT, LOG_DATE_FMT))

        logger.addHandler(ch)
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)

    # ================================================================
    #  STATE PERSISTENCE
    # ================================================================

    def _save_state(self):
        """Sauvegarde l'état du bot (positions, capital, PnL)."""
        state = {
            "timestamp": datetime.now().isoformat(),
            "capital": self.capital,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "iteration": self.iteration,
            "positions": {
                cid: {
                    "side": pos.side,
                    "token_id": pos.token_id,
                    "entry_price": pos.entry_price,
                    "size_usd": pos.size_usd,
                    "shares": pos.shares,
                    "entry_time": pos.entry_time.isoformat(),
                    "confidence": pos.confidence,
                    "order_id": pos.order_id,
                    "peak_price": pos.peak_price,
                    "market_question": pos.market.question,
                }
                for cid, pos in self.positions.items()
            },
            "trade_log": self.trade_log[-100:],  # Derniers 100 trades
        }

        state_path = Path(self.config.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self):
        """Restaure l'état du bot après un redémarrage."""
        state_path = Path(self.config.state_file)
        if not state_path.exists():
            return

        try:
            with open(state_path) as f:
                state = json.load(f)

            self.capital = state.get("capital", self.config.initial_capital)
            self.total_pnl = state.get("total_pnl", 0.0)
            self.trade_log = state.get("trade_log", [])
            self.iteration = state.get("iteration", 0)

            # Restaurer les positions (si le bot a redémarré)
            saved_positions = state.get("positions", {})
            if saved_positions:
                logger.info(f"Restauration de {len(saved_positions)} positions...")
                for cid, pdata in saved_positions.items():
                    try:
                        # Récupérer les infos du marché
                        market = self.client.get_market_by_condition(cid)
                        if market:
                            self.positions[cid] = BotPosition(
                                market=market,
                                side=pdata["side"],
                                token_id=pdata["token_id"],
                                entry_price=pdata["entry_price"],
                                size_usd=pdata["size_usd"],
                                shares=pdata["shares"],
                                entry_time=datetime.fromisoformat(pdata["entry_time"]),
                                confidence=pdata["confidence"],
                                order_id=pdata.get("order_id", ""),
                                peak_price=pdata.get("peak_price", pdata["entry_price"]),
                            )
                            logger.info(f"  Restauré: {pdata['market_question'][:50]}")
                    except Exception as e:
                        logger.warning(f"  Impossible de restaurer {cid}: {e}")

            logger.info(f"État restauré: capital=${self.capital:.0f}, "
                        f"PnL=${self.total_pnl:+.2f}, "
                        f"{len(self.positions)} positions")

        except Exception as e:
            logger.warning(f"Erreur restauration état: {e}")

    # ================================================================
    #  BOUCLE PRINCIPALE
    # ================================================================

    def run(self):
        """Boucle principale du bot."""
        mode = "PAPER" if self.config.dry_run else "REAL MONEY"

        logger.info("=" * 60)
        logger.info("  INSURANCE SELLER BOT")
        logger.info(f"  Inspiré d'anoin123 ($1.45M profit Polymarket)")
        logger.info("=" * 60)
        logger.info(f"  Mode:       {mode}")
        logger.info(f"  Capital:    ${self.capital:,.0f}")
        logger.info(f"  Max pos:    {self.config.max_positions}")
        logger.info(f"  Stop-loss:  {self.config.hard_stop_loss:.0%}")
        logger.info(f"  Scan:       toutes les {self.config.scan_interval_seconds}s")
        logger.info(f"  Sentiment:  {'ACTIF' if self.strategy._sentiment else 'DESACTIVE'}")
        logger.info("=" * 60)

        self.notifier.send(
            f"🤖 <b>Insurance Bot Started</b>\n"
            f"💰 Capital: ${self.capital:,.0f}\n"
            f"📊 Mode: {mode}"
        )

        while self._running:
            try:
                self.iteration += 1
                self._run_cycle()
                self._save_state()

                # Notification de statut toutes les 12 itérations (~1h)
                if self.iteration % 12 == 0:
                    equity = self._total_equity()
                    self.notifier.status_alert(equity, self.total_pnl, len(self.positions))

                if self._running:
                    logger.info(f"  Prochain scan dans {self.config.scan_interval_seconds}s...")
                    # Sleep interruptible
                    for _ in range(self.config.scan_interval_seconds):
                        if not self._running:
                            break
                        time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Erreur dans le cycle: {e}", exc_info=True)
                self.notifier.send(f"⚠️ <b>Erreur</b>: {str(e)[:200]}")
                time.sleep(30)  # Pause avant retry

        # Arrêt propre
        self._shutdown()

    def _run_cycle(self):
        """Un cycle complet du bot."""
        logger.info(f"\n{'─' * 50}")
        logger.info(f"  Cycle #{self.iteration} | {datetime.now():%Y-%m-%d %H:%M:%S}")
        logger.info(f"{'─' * 50}")

        # Reset daily PnL à minuit
        if datetime.now().hour == 0 and datetime.now().minute < 6:
            self.daily_pnl = 0.0
            logger.info("  Daily PnL reset")

        # Check daily loss limit
        if self._check_daily_loss():
            logger.warning("  DAILY LOSS LIMIT REACHED — skip cycle")
            return

        # 1. Scanner les marchés
        markets = self._scan_markets()
        if not markets:
            logger.info("  Aucun marché éligible")
            return

        # 2. Mettre à jour les positions existantes
        self._update_positions(markets)

        # 3. Chercher de nouvelles opportunités
        self._find_opportunities(markets)

        # 4. Afficher le dashboard
        self._print_dashboard()

    # ================================================================
    #  SCAN DES MARCHES
    # ================================================================

    def _scan_markets(self) -> list[PolymarketMarket]:
        """Scanne les marchés éligibles pour la stratégie."""
        try:
            markets = self.client.get_all_active_markets(
                min_volume=self.config.min_market_volume,
                min_liquidity=self.config.min_market_liquidity,
                max_markets=self.config.max_markets_to_scan,
            )
        except Exception as e:
            logger.error(f"Erreur scan marchés: {e}")
            return []

        # Pré-filtrer : on ne veut que les marchés avec YES > min_yes_price
        # (c'est là que le NO est cheap)
        eligible = []
        for m in markets:
            if m.yes_price >= self.config.min_yes_price:
                eligible.append(m)
            elif any(kw in m.question.lower() for kw in self.strategy.target_keywords):
                # Marchés de crise : on les inclut même si YES pas encore élevé
                # pour pouvoir les surveiller
                eligible.append(m)

        logger.info(f"  Scan: {len(markets)} marchés → {len(eligible)} éligibles "
                     f"(YES>{self.config.min_yes_price:.0%} ou crise)")

        return eligible

    # ================================================================
    #  POSITIONS
    # ================================================================

    def _update_positions(self, markets: list[PolymarketMarket]):
        """Met à jour les positions avec les prix actuels."""
        market_map = {m.condition_id: m for m in markets}

        for cid in list(self.positions.keys()):
            pos = self.positions[cid]

            try:
                # Récupérer le prix actuel du NO
                no_token = pos.token_id
                current_no_price = self.client.get_midpoint(no_token)
            except Exception:
                continue

            # Mise à jour peak
            if current_no_price > pos.peak_price:
                pos.peak_price = current_no_price

            # PnL
            pnl_pct = pos.unrealized_pnl_pct(current_no_price)

            should_exit = False
            exit_reason = ""

            # Stop-loss
            if pnl_pct <= -self.config.hard_stop_loss:
                should_exit = True
                exit_reason = "STOP_LOSS"

            # Take-profit
            elif pnl_pct >= self.config.take_profit:
                should_exit = True
                exit_reason = "TAKE_PROFIT"

            # Trailing stop (si on est en profit)
            elif pos.peak_price > pos.entry_price * 1.05:
                peak_pnl = (pos.peak_price - pos.entry_price) / pos.entry_price
                if (peak_pnl - pnl_pct) > 0.15:  # 15% trailing
                    should_exit = True
                    exit_reason = "TRAILING_STOP"

            # Marché fermé/résolu
            if cid in market_map and market_map[cid].closed:
                should_exit = True
                exit_reason = "RESOLVED"

            if should_exit:
                self._close_position(cid, current_no_price, exit_reason)

    def _close_position(self, cid: str, exit_price: float, reason: str):
        """Ferme une position."""
        pos = self.positions.pop(cid, None)
        if not pos:
            return

        pnl = pos.unrealized_pnl(exit_price)
        self.capital += pos.size_usd + pnl
        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Exécuter la vente sur Polymarket
        if self.trading_client:
            try:
                self.trading_client.place_market_order(
                    token_id=pos.token_id,
                    amount_usd=pos.size_usd,
                    side="SELL",
                )
            except Exception as e:
                logger.error(f"Erreur vente: {e}")

        # Logger
        trade = {
            "timestamp": datetime.now().isoformat(),
            "market_id": cid,
            "question": pos.market.question,
            "side": pos.side,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "size_usd": pos.size_usd,
            "shares": pos.shares,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pos.unrealized_pnl_pct(exit_price) * 100, 2),
            "reason": reason,
            "hold_time": str(datetime.now() - pos.entry_time),
        }
        self.trade_log.append(trade)

        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        icon = "✅" if pnl >= 0 else "❌"
        logger.info(f"  {icon} CLOSE [{reason}] {pnl_str} | {pos.market.question[:50]}")

        self.notifier.trade_alert(
            f"CLOSE ({reason})",
            pos.market.question,
            exit_price,
            pos.size_usd,
            pos.confidence,
        )

    # ================================================================
    #  RECHERCHE D'OPPORTUNITES
    # ================================================================

    def _find_opportunities(self, markets: list[PolymarketMarket]):
        """Évalue les marchés et ouvre des positions."""
        if len(self.positions) >= self.config.max_positions:
            logger.info(f"  Max positions atteint ({self.config.max_positions})")
            return

        opportunities = []

        for market in markets:
            if len(self.positions) >= self.config.max_positions:
                break

            # Skip si déjà une position sur ce marché
            if market.condition_id in self.positions:
                continue

            try:
                # Récupérer l'historique
                history = self._get_history(market)
                if history is None or len(history) < 30:
                    continue

                # Construire la barre actuelle avec la question du marché
                current_bar = history.iloc[-1].copy()
                current_bar["question"] = market.question

                # Générer le signal
                action, confidence = self.strategy.generate_signal(
                    market.condition_id,
                    current_bar,
                    history.iloc[:-1],
                )

                if action == "BUY_NO" and confidence > 0:
                    no_price = 1.0 - current_bar["mid_price"]
                    opportunities.append((market, confidence, no_price))
                    logger.info(
                        f"  📡 Signal: BUY_NO ({confidence:.0%}) "
                        f"NO={no_price:.3f} | {market.question[:50]}"
                    )

            except Exception as e:
                logger.debug(f"Erreur évaluation {market.condition_id}: {e}")

        # Trier par confiance et exécuter les meilleurs
        opportunities.sort(key=lambda x: x[1], reverse=True)

        for market, confidence, no_price in opportunities:
            if len(self.positions) >= self.config.max_positions:
                break
            self._open_position(market, confidence, no_price)

    def _open_position(self, market: PolymarketMarket, confidence: float,
                       no_price: float):
        """Ouvre une position NO sur un marché."""
        token_id = market.no_token_id

        # Sizing (proportionnel à la confiance)
        max_size = self.capital * self.config.max_position_pct
        current_exposure = sum(p.size_usd for p in self.positions.values())
        max_remaining = (self.capital * self.config.max_total_exposure_pct
                         - current_exposure)
        if max_remaining <= 0:
            return

        size_usd = min(max_size * confidence, max_remaining)
        if size_usd < 5:
            return

        shares = size_usd / max(no_price, 0.01)

        # Exécuter l'achat
        order_id = ""
        if self.trading_client:
            try:
                if self.config.order_type == "market":
                    result = self.trading_client.place_market_order(
                        token_id=token_id,
                        amount_usd=size_usd,
                        side="BUY",
                    )
                else:
                    limit_price = round(no_price + self.config.limit_offset, 2)
                    limit_price = min(limit_price, 0.99)
                    result = self.trading_client.place_limit_order(
                        token_id=token_id,
                        price=limit_price,
                        size=shares,
                        side="BUY",
                    )
                order_id = result.get("orderID", "")
            except Exception as e:
                logger.error(f"Erreur achat: {e}")
                return
        else:
            order_id = f"PAPER-{int(time.time())}"

        self.capital -= size_usd
        self.positions[market.condition_id] = BotPosition(
            market=market,
            side="NO",
            token_id=token_id,
            entry_price=no_price,
            size_usd=size_usd,
            shares=shares,
            entry_time=datetime.now(),
            confidence=confidence,
            order_id=order_id,
            peak_price=no_price,
        )

        logger.info(
            f"  🟢 OPEN NO | ${size_usd:.0f} @ {no_price:.3f} "
            f"(conf={confidence:.0%}) | {market.question[:50]}"
        )

        self.notifier.trade_alert(
            "OPEN NO", market.question, no_price, size_usd, confidence
        )

    # ================================================================
    #  HELPERS
    # ================================================================

    def _get_history(self, market: PolymarketMarket) -> pd.DataFrame | None:
        """Récupère l'historique d'un marché (avec cache 10 min)."""
        cid = market.condition_id
        now = datetime.now()

        if cid in self._histories:
            last = self._last_refresh.get(cid, datetime.min)
            if (now - last) < timedelta(minutes=10):
                return self._histories[cid]

        try:
            df = self.client.get_market_history_for_backtest(
                market, fidelity=self.config.history_fidelity
            )
            if not df.empty:
                self._histories[cid] = df
                self._last_refresh[cid] = now
                return df
        except Exception as e:
            logger.debug(f"Erreur historique {cid}: {e}")

        return self._histories.get(cid)

    def _total_equity(self) -> float:
        """Equity totale (capital + positions mark-to-market)."""
        return self.capital + sum(p.size_usd for p in self.positions.values())

    def _check_daily_loss(self) -> bool:
        """Vérifie le daily loss limit."""
        if self.config.initial_capital <= 0:
            return False
        return self.daily_pnl / self.config.initial_capital < -self.config.daily_loss_limit_pct

    # ================================================================
    #  DASHBOARD TERMINAL
    # ================================================================

    def _print_dashboard(self):
        """Affiche un dashboard dans le terminal."""
        equity = self._total_equity()
        exposure = sum(p.size_usd for p in self.positions.values())
        exposure_pct = (exposure / equity * 100) if equity > 0 else 0
        uptime = datetime.now() - self.start_time

        n_trades = len(self.trade_log)
        wins = sum(1 for t in self.trade_log if t.get("pnl", 0) > 0)
        win_rate = (wins / n_trades * 100) if n_trades > 0 else 0

        logger.info("")
        logger.info("┌─────────────────────────────────────────────────┐")
        logger.info("│         INSURANCE SELLER BOT — DASHBOARD        │")
        logger.info("├─────────────────────────────────────────────────┤")
        logger.info(f"│  Equity:     ${equity:>10,.0f}                       │")
        logger.info(f"│  Capital:    ${self.capital:>10,.0f}                       │")
        logger.info(f"│  Total PnL:  ${self.total_pnl:>+10,.2f}  ({self.total_pnl/self.config.initial_capital:>+.2%})       │")
        logger.info(f"│  Day PnL:    ${self.daily_pnl:>+10,.2f}                       │")
        logger.info(f"│  Exposure:   {exposure_pct:>9.1f}%                        │")
        logger.info(f"│  Positions:  {len(self.positions):>5d} / {self.config.max_positions}                          │")
        logger.info(f"│  Trades:     {n_trades:>5d}  (Win: {win_rate:.0f}%)                │")
        logger.info(f"│  Uptime:     {str(uptime).split('.')[0]:>14s}                  │")
        logger.info("├─────────────────────────────────────────────────┤")

        if self.positions:
            logger.info("│  POSITIONS OUVERTES :                           │")
            for cid, pos in self.positions.items():
                try:
                    current = self.client.get_midpoint(pos.token_id)
                    pnl = pos.unrealized_pnl(current)
                    pnl_str = f"+${pnl:.0f}" if pnl >= 0 else f"-${abs(pnl):.0f}"
                except Exception:
                    pnl_str = "?"
                q = pos.market.question[:30]
                logger.info(
                    f"│  NO ${pos.size_usd:>5.0f} @ {pos.entry_price:.3f} "
                    f"{pnl_str:>6s} | {q:30s}│"
                )
        else:
            logger.info("│  Aucune position ouverte                        │")

        logger.info("└─────────────────────────────────────────────────┘")

    # ================================================================
    #  SHUTDOWN
    # ================================================================

    def _shutdown(self):
        """Arrêt propre du bot."""
        logger.info("\n" + "=" * 60)
        logger.info("  BOT SHUTDOWN")
        logger.info("=" * 60)

        # Sauvegarder l'état
        self._save_state()

        # Résumé final
        equity = self._total_equity()
        n_trades = len(self.trade_log)
        logger.info(f"  Equity finale:  ${equity:,.0f}")
        logger.info(f"  PnL total:      ${self.total_pnl:+,.2f}")
        logger.info(f"  Trades:         {n_trades}")
        logger.info(f"  Positions:      {len(self.positions)} (ouvertes)")
        logger.info(f"  Uptime:         {datetime.now() - self.start_time}")

        # Sauvegarder le trade log complet
        if self.trade_log:
            log_path = Path(self.config.log_dir) / "trades_history.json"
            with open(log_path, "w") as f:
                json.dump(self.trade_log, f, indent=2, default=str)
            logger.info(f"  Trades sauvegardés: {log_path}")

        self.notifier.send(
            f"🛑 <b>Bot Stopped</b>\n"
            f"💼 Equity: ${equity:,.0f}\n"
            f"📊 PnL: ${self.total_pnl:+,.2f}\n"
            f"📋 {len(self.positions)} positions ouvertes"
        )

        logger.info("=" * 60)


# ================================================================
#  CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Insurance Seller Bot — Stratégie anoin123 sur Polymarket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Paper trading (défaut)
  python insurance_bot.py

  # Avec plus de capital
  python insurance_bot.py --capital 5000

  # Scan rapide (2 min au lieu de 5)
  python insurance_bot.py --scan-interval 120

  # Real money trading
  python insurance_bot.py --real-money --private-key 0x...

  # Avec Telegram
  python insurance_bot.py --telegram-token TOKEN --telegram-chat CHAT_ID

  # Mode agressif (plus d'exposition, stop-loss plus lâche)
  python insurance_bot.py --max-exposure 0.50 --stop-loss 0.50 --max-positions 10
        """,
    )

    # Capital
    parser.add_argument("--capital", type=float, default=1000,
                        help="Capital initial en $ (défaut: 1000)")
    parser.add_argument("--max-position-pct", type=float, default=0.10,
                        help="Taille max par position en %% du capital (défaut: 0.10)")
    parser.add_argument("--max-exposure", type=float, default=0.40,
                        help="Exposition totale max en %% (défaut: 0.40)")
    parser.add_argument("--max-positions", type=int, default=6,
                        help="Nombre max de positions ouvertes (défaut: 6)")

    # Stratégie
    parser.add_argument("--max-no-price", type=float, default=0.35,
                        help="Prix max du NO pour acheter (défaut: 0.35)")
    parser.add_argument("--min-yes-price", type=float, default=0.65,
                        help="Prix min du YES requis (défaut: 0.65)")
    parser.add_argument("--stop-loss", type=float, default=0.40,
                        help="Stop-loss en %% (défaut: 0.40)")
    parser.add_argument("--take-profit", type=float, default=0.80,
                        help="Take-profit en %% (défaut: 0.80)")

    # Exécution
    parser.add_argument("--scan-interval", type=int, default=300,
                        help="Intervalle de scan en secondes (défaut: 300)")
    parser.add_argument("--real-money", action="store_true",
                        help="Mode real money (ATTENTION)")
    parser.add_argument("--private-key", type=str, default=None,
                        help="Clé privée Polygon (pour real money)")

    # Notifications
    parser.add_argument("--telegram-token", type=str, default="",
                        help="Token du bot Telegram")
    parser.add_argument("--telegram-chat", type=str, default="",
                        help="Chat ID Telegram")

    # Filtres
    parser.add_argument("--min-volume", type=float, default=20000,
                        help="Volume min des marchés (défaut: 20000)")
    parser.add_argument("--min-liquidity", type=float, default=2000,
                        help="Liquidité min (défaut: 2000)")

    args = parser.parse_args()

    # Build config
    config = BotConfig(
        initial_capital=args.capital,
        max_position_pct=args.max_position_pct,
        max_total_exposure_pct=args.max_exposure,
        max_positions=args.max_positions,
        max_no_price=args.max_no_price,
        min_yes_price=args.min_yes_price,
        hard_stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        scan_interval_seconds=args.scan_interval,
        dry_run=not args.real_money,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat,
        min_market_volume=args.min_volume,
        min_market_liquidity=args.min_liquidity,
    )

    # Résoudre la clé privée
    private_key = args.private_key or os.environ.get("POLYMARKET_PRIVATE_KEY")

    if args.real_money and not private_key:
        print("ERREUR: --real-money nécessite --private-key ou POLYMARKET_PRIVATE_KEY")
        sys.exit(1)

    if args.real_money:
        print("\n" + "=" * 60)
        print("  ⚠️  MODE REAL MONEY  ⚠️")
        print(f"  Capital: ${args.capital:,.0f}")
        print("  Vous allez trader avec de l'argent réel.")
        print("=" * 60)
        confirm = input("  Taper 'OUI' pour confirmer: ")
        if confirm.strip() != "OUI":
            print("Annulé.")
            sys.exit(0)

    bot = InsuranceBot(config, private_key)
    bot.run()


if __name__ == "__main__":
    main()
