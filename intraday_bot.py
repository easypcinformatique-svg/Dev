#!/usr/bin/env python3
"""
Intraday Fader Bot — Bot de trading intraday Polymarket.

Combine 3 stratégies:
1. News Fade: Surréaction à une news → fade le mouvement
2. Volume Spike Fade: Volume anormal sans news confirmée → fade
3. Mean Reversion: Prix extrême (>90% ou <10%) → retour au centre

Scan toutes les 30-60s, trade court terme (1-4h max).

Usage:
    # Paper trading (défaut)
    python intraday_bot.py

    # Avec capital custom et scan rapide
    python intraday_bot.py --capital 200 --scan-interval 30

    # Real money
    python intraday_bot.py --real-money --private-key 0x...

    # Avec Telegram
    python intraday_bot.py --telegram-token TOKEN --telegram-chat CHAT_ID
"""

import argparse
import json
import os
import sys
import time
import signal
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass

from news_engine import NewsEngine
from volume_detector import VolumeDetector
from intraday_fader import IntradayFader, RiskParams, Side
from backtest.polymarket_client import PolymarketTradingClient

# ── Logging ──────────────────────────────────────────────────
LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("intraday_bot")


@dataclass
class IntradayBotConfig:
    """Configuration du bot intraday."""

    # Capital
    initial_capital: float = 100.0
    max_position_usd: float = 15.0
    max_total_exposure: float = 50.0
    max_concurrent_trades: int = 5

    # Risk
    max_daily_loss: float = 25.0
    min_risk_reward: float = 1.5
    min_confidence: float = 0.30

    # Scan
    scan_interval_seconds: int = 45
    max_days_to_resolution: int = 7

    # Stratégies activées
    enable_news_fade: bool = True
    enable_volume_spike: bool = True
    enable_mean_reversion: bool = True

    # Exécution
    dry_run: bool = True
    order_type: str = "limit"
    limit_offset: float = 0.005

    # Notifications
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # Fichiers
    log_dir: str = "logs/intraday_bot"
    state_file: str = "logs/intraday_bot/state.json"


class TelegramNotifier:
    """Notifications Telegram."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, message: str, silent: bool = False):
        if not self.enabled:
            return
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_notification": silent,
                },
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Telegram: {e}")

    def trade_alert(self, action: str, question: str, price: float,
                    size: float, signal_type: str):
        emoji = "🟢" if "ENTRY" in action else "🔴"
        self.send(
            f"{emoji} <b>{action}</b>\n"
            f"📊 {question[:60]}\n"
            f"💰 ${size:.2f} @ {price:.4f}\n"
            f"🎯 {signal_type}\n"
            f"⏰ {datetime.now(timezone.utc):%H:%M:%S} UTC"
        )


class IntradayBot:
    """
    Bot intraday Polymarket — orchestre les 3 stratégies.

    Architecture:
    ┌──────────────┐    ┌─────────────────┐    ┌────────────────┐
    │  NewsEngine  │───→│  IntradayFader   │───→│  Trade Exec    │
    │  (RSS feeds) │    │  (3 stratégies)  │    │  (CLOB/Paper)  │
    └──────────────┘    └─────────────────┘    └────────────────┘
                              ↑
    ┌──────────────┐          │
    │VolumeDetector│──────────┘
    │(Gamma + CLOB)│
    └──────────────┘
    """

    def __init__(self, config: IntradayBotConfig, private_key: str | None = None):
        self.config = config
        self._running = True
        self.start_time = datetime.now(timezone.utc)
        self.iteration = 0

        # ── Modules ──
        self.news_engine = NewsEngine(refresh_interval=120)
        self.volume_detector = VolumeDetector(
            scan_interval=config.scan_interval_seconds,
            max_days_to_resolution=config.max_days_to_resolution,
        )
        self.fader = IntradayFader(
            risk_params=RiskParams(
                max_position_usd=config.max_position_usd,
                max_total_exposure=config.max_total_exposure,
                max_concurrent_trades=config.max_concurrent_trades,
                max_daily_loss_usd=config.max_daily_loss,
                min_risk_reward=config.min_risk_reward,
                min_confidence=config.min_confidence,
            ),
            bankroll=config.initial_capital,
        )

        # ── Trading client ──
        self.trading_client = None
        if not config.dry_run and private_key:
            self.trading_client = PolymarketTradingClient(private_key)

        # ── Notifications ──
        self.notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)

        # ── Setup ──
        self._setup_logging()
        self._load_state()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("Signal reçu, arrêt propre...")
        self._running = False

    def _setup_logging(self):
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(LOG_FMT, LOG_DATE_FMT))

        fh = logging.FileHandler(
            log_dir / f"intraday_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.log"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(LOG_FMT, LOG_DATE_FMT))

        # Appliquer à tous les loggers pertinents
        for name in ["intraday_bot", "news_engine", "volume_detector", "intraday_fader"]:
            lg = logging.getLogger(name)
            lg.addHandler(ch)
            lg.addHandler(fh)
            lg.setLevel(logging.DEBUG)

    # ── State persistence ──

    def _save_state(self):
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iteration": self.iteration,
            "bankroll": self.fader.bankroll,
            "daily_pnl": self.fader.daily_pnl,
            "open_positions": self.fader.open_positions,
            "trade_history": self.fader.trade_history[-200:],
            "stats": self.fader.get_stats(),
        }
        state_path = Path(self.config.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self):
        state_path = Path(self.config.state_file)
        if not state_path.exists():
            return
        try:
            with open(state_path) as f:
                state = json.load(f)
            self.fader.bankroll = state.get("bankroll", self.config.initial_capital)
            self.fader.daily_pnl = state.get("daily_pnl", 0.0)
            self.fader.open_positions = state.get("open_positions", [])
            self.fader.trade_history = state.get("trade_history", [])
            self.iteration = state.get("iteration", 0)
            logger.info(f"État restauré: bankroll=${self.fader.bankroll:.2f}, "
                        f"{len(self.fader.open_positions)} positions ouvertes")
        except Exception as e:
            logger.warning(f"Erreur restauration: {e}")

    # ── Main loop ──

    def run(self):
        """Boucle principale du bot intraday."""
        mode = "PAPER" if self.config.dry_run else "REAL MONEY"

        logger.info("=" * 60)
        logger.info("  INTRADAY FADER BOT")
        logger.info("=" * 60)
        logger.info(f"  Mode:        {mode}")
        logger.info(f"  Capital:     ${self.config.initial_capital:.0f}")
        logger.info(f"  Max pos:     ${self.config.max_position_usd:.0f} x{self.config.max_concurrent_trades}")
        logger.info(f"  Daily stop:  ${self.config.max_daily_loss:.0f}")
        logger.info(f"  Scan:        toutes les {self.config.scan_interval_seconds}s")
        logger.info(f"  Strategies:  "
                     f"{'NEWS ' if self.config.enable_news_fade else ''}"
                     f"{'VOL_SPIKE ' if self.config.enable_volume_spike else ''}"
                     f"{'MEAN_REV ' if self.config.enable_mean_reversion else ''}")
        logger.info(f"  Marchés:     ≤{self.config.max_days_to_resolution}j de résolution")
        logger.info("=" * 60)

        # Démarrer les modules en arrière-plan
        logger.info("Démarrage NewsEngine...")
        self.news_engine.start_background()

        logger.info("Démarrage VolumeDetector...")
        self.volume_detector.start_background()

        # Attendre le premier scan
        logger.info("Attente du premier scan (30s)...")
        time.sleep(30)

        self.notifier.send(
            f"🤖 <b>Intraday Fader Bot Started</b>\n"
            f"💰 Capital: ${self.config.initial_capital:.0f}\n"
            f"📊 Mode: {mode}\n"
            f"⏱ Scan: {self.config.scan_interval_seconds}s"
        )

        while self._running:
            try:
                self.iteration += 1
                self._run_cycle()
                self._save_state()

                # Status toutes les 40 itérations (~30min)
                if self.iteration % 40 == 0:
                    self._send_status()

                if self._running:
                    for _ in range(self.config.scan_interval_seconds):
                        if not self._running:
                            break
                        time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Erreur cycle: {e}", exc_info=True)
                self.notifier.send(f"⚠️ Erreur: {str(e)[:200]}")
                time.sleep(15)

        self._shutdown()

    def _run_cycle(self):
        """Un cycle complet: check exits → scan → evaluate → trade."""
        now = datetime.now(timezone.utc)

        if self.iteration % 20 == 0:
            logger.info(f"\n{'─' * 50}")
            logger.info(f"  Cycle #{self.iteration} | {now:%H:%M:%S} UTC")
            logger.info(f"{'─' * 50}")

        # 1. Check exits sur positions ouvertes
        self._check_exits()

        # 2. Vérifier si on peut encore trader
        can_trade, reason = self.fader.is_trading_allowed()
        if not can_trade:
            if self.iteration % 20 == 0:
                logger.info(f"  Trading pausé: {reason}")
            return

        # 3. Évaluer les opportunités
        signals = []

        # 3a. News Fade
        if self.config.enable_news_fade:
            news_signals = self._evaluate_news_fades()
            signals.extend(news_signals)

        # 3b. Volume Spike Fade
        if self.config.enable_volume_spike:
            vol_signals = self._evaluate_volume_spikes()
            signals.extend(vol_signals)

        # 3c. Mean Reversion
        if self.config.enable_mean_reversion:
            mr_signals = self._evaluate_mean_reversion()
            signals.extend(mr_signals)

        # 4. Exécuter les meilleurs signaux
        if signals:
            signals.sort(key=lambda s: s.confidence, reverse=True)
            self._execute_signals(signals)

        # 5. Dashboard périodique
        if self.iteration % 20 == 0:
            self._print_dashboard()

    # ── Strategy evaluation ──

    def _evaluate_news_fades(self):
        """Évalue les opportunités de news fade."""
        signals = []
        fade_opps = self.volume_detector.get_fade_opportunities(
            min_confidence=self.config.min_confidence,
            minutes=15,
        )

        for move in fade_opps:
            # Vérifier s'il y a des news liées
            news = self.news_engine.search_news(move.question, minutes=30)

            # Éviter les doublons (déjà en position sur ce marché)
            already_in = any(
                p["condition_id"] == move.condition_id
                for p in self.fader.open_positions
            )
            if already_in:
                continue

            signal = self.fader.evaluate_news_fade(move, news)
            if signal:
                signals.append(signal)

        return signals

    def _evaluate_volume_spikes(self):
        """Évalue les opportunités de volume spike fade."""
        signals = []
        spikes = self.volume_detector.get_volume_spikes(min_ratio=5.0)

        for market in spikes[:10]:  # Top 10 spikes
            already_in = any(
                p["condition_id"] == market.condition_id
                for p in self.fader.open_positions
            )
            if already_in:
                continue

            # Récupérer le orderbook si possible
            orderbook = None
            if market.tokens:
                orderbook = self.volume_detector.get_orderbook(market.tokens[0])

            baseline = self.volume_detector.volume_baselines.get(
                market.condition_id, 0
            )
            if baseline == 0:
                continue
            vol_ratio = market.volume_24h / baseline

            signal = self.fader.evaluate_volume_spike(market, vol_ratio, orderbook)
            if signal:
                signals.append(signal)

        return signals

    def _evaluate_mean_reversion(self):
        """Évalue les opportunités de mean reversion."""
        signals = []
        now = datetime.now(timezone.utc)
        markets = self.volume_detector.get_short_term_markets()

        for cid, market in markets.items():
            # Filtrer les prix extrêmes
            if 0.08 < market.yes_price < 0.92:
                continue

            already_in = any(
                p["condition_id"] == cid
                for p in self.fader.open_positions
            )
            if already_in:
                continue

            if not market.end_date:
                continue

            hours_left = (market.end_date - now).total_seconds() / 3600
            signal = self.fader.evaluate_mean_reversion(market, hours_left)
            if signal:
                signals.append(signal)

        return signals

    # ── Trade execution ──

    def _execute_signals(self, signals):
        """Exécute les signaux de trade (meilleurs en premier)."""
        for signal in signals:
            can_trade, reason = self.fader.is_trading_allowed()
            if not can_trade:
                break

            logger.info(
                f"  🎯 SIGNAL [{signal.signal_type.value}] "
                f"{signal.side.value} | conf={signal.confidence:.0%} | "
                f"R/R={signal.risk_reward:.1f} | ${signal.size_usd:.2f} | "
                f"{signal.question[:45]}"
            )

            actual_price = signal.entry_price
            order_id = ""

            if self.trading_client and signal.token_id:
                try:
                    if self.config.order_type == "market":
                        result = self.trading_client.place_market_order(
                            token_id=signal.token_id,
                            amount_usd=signal.size_usd,
                            side="BUY",
                        )
                    else:
                        limit_price = round(
                            signal.entry_price + self.config.limit_offset, 2
                        )
                        limit_price = min(limit_price, 0.99)
                        shares = signal.size_usd / max(signal.entry_price, 0.01)
                        result = self.trading_client.place_limit_order(
                            token_id=signal.token_id,
                            price=limit_price,
                            size=shares,
                            side="BUY",
                        )
                    order_id = result.get("orderID", "")
                    logger.info(f"    Ordre placé: {order_id}")
                except Exception as e:
                    logger.error(f"    Erreur exécution: {e}")
                    continue
            else:
                order_id = f"PAPER-{int(time.time())}"

            # Enregistrer l'entrée
            self.fader.record_entry(signal, actual_price)

            self.notifier.trade_alert(
                "ENTRY",
                signal.question,
                actual_price,
                signal.size_usd,
                signal.signal_type.value,
            )

    def _check_exits(self):
        """Vérifie les conditions de sortie."""
        if not self.fader.open_positions:
            return

        # Récupérer les prix actuels depuis le volume detector
        current_prices = {}
        for pos in self.fader.open_positions:
            cid = pos["condition_id"]
            market = self.volume_detector.active_markets.get(cid)
            if market:
                current_prices[cid] = market.yes_price

        exits = self.fader.check_exits(current_prices)

        for exit_info in exits:
            pos = exit_info["position"]
            reason = exit_info["exit_reason"]
            exit_price = exit_info["exit_price"]
            pnl = exit_info["pnl_usd"]

            # Exécuter la vente si real money
            if self.trading_client and pos.get("token_id"):
                try:
                    self.trading_client.place_market_order(
                        token_id=pos["token_id"],
                        amount_usd=pos["size_usd"],
                        side="SELL",
                    )
                except Exception as e:
                    logger.error(f"Erreur vente: {e}")

            self.fader.record_exit(pos, exit_price, pnl, reason)

            emoji = "✅" if pnl >= 0 else "❌"
            self.notifier.send(
                f"{emoji} <b>EXIT [{reason}]</b>\n"
                f"📊 {pos['question'][:50]}\n"
                f"💰 PnL: ${pnl:+.2f}\n"
                f"⏱ {exit_info['hours_held']:.1f}h"
            )

    # ── Dashboard ──

    def _print_dashboard(self):
        stats = self.fader.get_stats()
        n_markets = len(self.volume_detector.active_markets)
        n_news = len(self.news_engine.get_recent_news(minutes=60))
        uptime = datetime.now(timezone.utc) - self.start_time

        logger.info("")
        logger.info("┌────────────────────────────────────────────────────┐")
        logger.info("│          INTRADAY FADER — DASHBOARD                │")
        logger.info("├────────────────────────────────────────────────────┤")
        logger.info(f"│  Bankroll:    ${self.fader.bankroll:>8.2f}                        │")
        logger.info(f"│  Daily PnL:   ${stats['daily_pnl']:>+8.2f}                        │")
        logger.info(f"│  Total PnL:   ${stats['total_pnl']:>+8.2f}                        │")
        logger.info(f"│  Positions:   {stats['open_positions']:>3d} / {self.config.max_concurrent_trades}                           │")
        logger.info(f"│  Trades:      {stats['total_trades']:>3d}  (Win: {stats['win_rate']:.0%})                  │")
        logger.info(f"│  Avg Win:     ${stats['avg_win']:>+8.2f}                        │")
        logger.info(f"│  Avg Loss:    ${stats['avg_loss']:>+8.2f}                        │")
        logger.info(f"│  Markets:     {n_markets:>3d} monitorés                       │")
        logger.info(f"│  News/1h:     {n_news:>3d}                                  │")
        logger.info(f"│  Uptime:      {str(uptime).split('.')[0]:>14s}                │")
        logger.info("├────────────────────────────────────────────────────┤")

        if self.fader.open_positions:
            logger.info("│  POSITIONS OUVERTES:                               │")
            for pos in self.fader.open_positions:
                q = pos["question"][:28]
                side = pos["side"][:6]
                size = pos["size_usd"]
                logger.info(f"│  {side} ${size:>5.2f} | {q:28s}      │")
        else:
            logger.info("│  Aucune position ouverte                           │")

        logger.info("└────────────────────────────────────────────────────┘")

    def _send_status(self):
        stats = self.fader.get_stats()
        self.notifier.send(
            f"📊 <b>Status Intraday</b>\n"
            f"💰 Bankroll: ${self.fader.bankroll:.2f}\n"
            f"📈 PnL jour: ${stats['daily_pnl']:+.2f}\n"
            f"📋 Positions: {stats['open_positions']}\n"
            f"🏆 Win rate: {stats['win_rate']:.0%} ({stats['total_trades']} trades)",
            silent=True,
        )

    def _shutdown(self):
        logger.info("\n" + "=" * 60)
        logger.info("  INTRADAY BOT SHUTDOWN")
        logger.info("=" * 60)

        self.news_engine.stop()
        self.volume_detector.stop()
        self._save_state()

        stats = self.fader.get_stats()
        logger.info(f"  Bankroll:    ${self.fader.bankroll:.2f}")
        logger.info(f"  Total PnL:   ${stats['total_pnl']:+.2f}")
        logger.info(f"  Trades:      {stats['total_trades']} (Win: {stats['win_rate']:.0%})")
        logger.info(f"  Positions:   {stats['open_positions']} ouvertes")

        # Sauvegarder l'historique complet
        if self.fader.trade_history:
            hist_path = Path(self.config.log_dir) / "trade_history.json"
            with open(hist_path, "w") as f:
                json.dump(self.fader.trade_history, f, indent=2, default=str)
            logger.info(f"  Historique: {hist_path}")

        self.notifier.send(
            f"🛑 <b>Intraday Bot Stopped</b>\n"
            f"💰 Bankroll: ${self.fader.bankroll:.2f}\n"
            f"📊 PnL: ${stats['total_pnl']:+.2f}\n"
            f"📋 {stats['open_positions']} positions ouvertes"
        )

        logger.info("=" * 60)


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Intraday Fader Bot — Trading intraday Polymarket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Paper trading (défaut)
  python intraday_bot.py

  # Capital custom, scan rapide
  python intraday_bot.py --capital 200 --scan-interval 30

  # Real money
  python intraday_bot.py --real-money --private-key 0x...

  # Seulement mean reversion
  python intraday_bot.py --no-news-fade --no-volume-spike

  # Avec Telegram
  python intraday_bot.py --telegram-token TOKEN --telegram-chat CHAT_ID
        """,
    )

    # Capital
    parser.add_argument("--capital", type=float, default=100,
                        help="Capital initial en $ (défaut: 100)")
    parser.add_argument("--max-position", type=float, default=15,
                        help="Taille max par position en $ (défaut: 15)")
    parser.add_argument("--max-exposure", type=float, default=50,
                        help="Exposition totale max en $ (défaut: 50)")
    parser.add_argument("--max-trades", type=int, default=5,
                        help="Nombre max de trades simultanés (défaut: 5)")
    parser.add_argument("--daily-stop", type=float, default=25,
                        help="Stop journalier en $ (défaut: 25)")

    # Scan
    parser.add_argument("--scan-interval", type=int, default=45,
                        help="Intervalle de scan en secondes (défaut: 45)")
    parser.add_argument("--max-days", type=int, default=7,
                        help="Max jours avant résolution (défaut: 7)")

    # Stratégies
    parser.add_argument("--no-news-fade", action="store_true",
                        help="Désactiver la stratégie News Fade")
    parser.add_argument("--no-volume-spike", action="store_true",
                        help="Désactiver la stratégie Volume Spike")
    parser.add_argument("--no-mean-reversion", action="store_true",
                        help="Désactiver la stratégie Mean Reversion")

    # Confidence
    parser.add_argument("--min-confidence", type=float, default=0.30,
                        help="Confidence minimum pour trader (défaut: 0.30)")
    parser.add_argument("--min-rr", type=float, default=1.5,
                        help="Risk/reward minimum (défaut: 1.5)")

    # Exécution
    parser.add_argument("--real-money", action="store_true",
                        help="Mode real money (ATTENTION)")
    parser.add_argument("--private-key", type=str, default=None,
                        help="Clé privée Polygon")

    # Telegram
    parser.add_argument("--telegram-token", type=str, default="",
                        help="Token bot Telegram")
    parser.add_argument("--telegram-chat", type=str, default="",
                        help="Chat ID Telegram")

    args = parser.parse_args()

    config = IntradayBotConfig(
        initial_capital=args.capital,
        max_position_usd=args.max_position,
        max_total_exposure=args.max_exposure,
        max_concurrent_trades=args.max_trades,
        max_daily_loss=args.daily_stop,
        min_risk_reward=args.min_rr,
        min_confidence=args.min_confidence,
        scan_interval_seconds=args.scan_interval,
        max_days_to_resolution=args.max_days,
        enable_news_fade=not args.no_news_fade,
        enable_volume_spike=not args.no_volume_spike,
        enable_mean_reversion=not args.no_mean_reversion,
        dry_run=not args.real_money,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat,
    )

    private_key = args.private_key or os.environ.get("POLYMARKET_PRIVATE_KEY")

    if args.real_money and not private_key:
        print("ERREUR: --real-money nécessite --private-key ou POLYMARKET_PRIVATE_KEY")
        sys.exit(1)

    if args.real_money:
        print("\n" + "=" * 60)
        print("  ⚠️  MODE REAL MONEY  ⚠️")
        print(f"  Capital: ${args.capital:.0f}")
        print(f"  Max position: ${args.max_position:.0f}")
        print(f"  Daily stop: ${args.daily_stop:.0f}")
        print("=" * 60)
        confirm = input("  Taper 'OUI' pour confirmer: ")
        if confirm.strip() != "OUI":
            print("Annulé.")
            sys.exit(0)

    bot = IntradayBot(config, private_key)
    bot.run()


if __name__ == "__main__":
    main()
