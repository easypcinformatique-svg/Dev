"""
Bot autonome de trading Polymarket — Hedge Fund Mode.

Tourne en continu 24/7. Scanne les marches, execute les strategies,
gere le risque, et expose une API JSON pour le dashboard web.

Architecture :
    1. MarketScanner  — decouvre et filtre les marches actifs
    2. SignalEngine    — genere les signaux via AlphaComposite + Sentiment
    3. RiskManager     — position sizing, exposure limits, drawdown guard
    4. Executor        — place les ordres (dry-run ou live)
    5. StateStore      — etat persistant (JSON) pour reprendre apres crash
    6. API endpoint    — FastAPI/Flask pour le dashboard

Usage :
    # Paper trading (par defaut)
    python hedge_fund_bot.py

    # Live trading
    POLYMARKET_PRIVATE_KEY=0x... python hedge_fund_bot.py --live

    # Avec dashboard
    python hedge_fund_bot.py --dashboard --port 5050
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd

# Ajouter le repertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from backtest.polymarket_client import PolymarketClient, PolymarketTradingClient, PolymarketMarket
from backtest.strategies import AlphaCompositeStrategy, InsuranceSellerStrategy
from config_manager import ConfigManager
from trade_logger import TradeLogger, POLYMARKET_FEE_PCT
from signal_detector import SignalDetector

logger = logging.getLogger("hedge_fund_bot")


# ================================================================
#  DATA MODELS
# ================================================================

@dataclass
class BotPosition:
    """Position ouverte sur un marche."""
    market_id: str
    question: str
    side: str           # YES ou NO
    token_id: str
    entry_price: float
    size_usd: float
    shares: float
    entry_time: str
    order_id: str = ""
    peak_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class BotTrade:
    """Trade termine."""
    market_id: str
    question: str
    side: str
    entry_price: float
    exit_price: float
    size_usd: float
    pnl: float
    pnl_pct: float
    entry_time: str
    exit_time: str
    reason: str


@dataclass
class BotConfig:
    """Configuration complete du bot."""
    # Capital
    initial_capital: float = 1000.0
    max_position_pct: float = 0.05
    max_total_exposure_pct: float = 0.30
    max_positions: int = 8

    # Filtres marches
    min_volume: float = 50000.0
    min_liquidity: float = 5000.0
    min_spread: float = 0.005
    max_spread: float = 0.08

    # Timing
    scan_interval_seconds: int = 300
    history_fidelity: int = 60

    # Risk
    daily_loss_limit_pct: float = 0.05
    max_drawdown_pct: float = 0.15

    # Mode
    dry_run: bool = True
    strategy: str = "alpha_composite"  # alpha_composite ou insurance_seller

    # Persistence
    state_file: str = "bot_state.json"
    log_dir: str = "logs"


@dataclass
class BotState:
    """Etat persistant du bot."""
    capital: float = 1000.0
    positions: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    equity_history: list = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    peak_equity: float = 1000.0
    iteration: int = 0
    started_at: str = ""
    last_scan: str = ""
    markets_scanned: int = 0
    signals_generated: int = 0
    errors: list = field(default_factory=list)


# ================================================================
#  STATE STORE — Persistence JSON
# ================================================================

class StateStore:
    """Sauvegarde et charge l'etat du bot en JSON."""

    def __init__(self, path: str):
        self.path = Path(path)

    def save(self, state: BotState):
        data = {
            "capital": state.capital,
            "positions": state.positions,
            "trades": state.trades[-500:],  # Garder les 500 derniers
            "equity_history": state.equity_history[-2000:],
            "daily_pnl": state.daily_pnl,
            "total_pnl": state.total_pnl,
            "peak_equity": state.peak_equity,
            "iteration": state.iteration,
            "started_at": state.started_at,
            "last_scan": state.last_scan,
            "markets_scanned": state.markets_scanned,
            "signals_generated": state.signals_generated,
            "errors": state.errors[-50:],
        }
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(self.path)

    def load(self) -> BotState:
        if not self.path.exists():
            return BotState()
        try:
            with open(self.path) as f:
                data = json.load(f)
            state = BotState()
            for k, v in data.items():
                if hasattr(state, k):
                    setattr(state, k, v)
            return state
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Etat corrompu, reset: {e}")
            return BotState()


# ================================================================
#  RISK MANAGER
# ================================================================

class RiskManager:
    """Gestion du risque avancee — inspiree des risk desks de hedge funds."""

    def __init__(self, config: BotConfig):
        self.config = config
        self._consecutive_losses = 0
        self._max_consecutive_losses = 0
        self._recent_pnls: list[float] = []  # 20 derniers PnL pour analyse

    def record_trade_result(self, pnl: float):
        """Enregistre le resultat d'un trade pour adapter le risk."""
        self._recent_pnls.append(pnl)
        if len(self._recent_pnls) > 20:
            self._recent_pnls.pop(0)
        if pnl < 0:
            self._consecutive_losses += 1
            self._max_consecutive_losses = max(
                self._max_consecutive_losses, self._consecutive_losses
            )
        else:
            self._consecutive_losses = 0

    def _get_risk_multiplier(self) -> float:
        """Multiplicateur de risque dynamique base sur la performance recente."""
        # Apres des pertes consecutives, reduire le risque (anti-tilt)
        if self._consecutive_losses >= 4:
            return 0.25  # Reduire a 25% apres 4 pertes de suite
        elif self._consecutive_losses >= 3:
            return 0.50
        elif self._consecutive_losses >= 2:
            return 0.75

        # Si on est en winning streak, augmenter legerement
        if len(self._recent_pnls) >= 5:
            recent_wins = sum(1 for p in self._recent_pnls[-5:] if p > 0)
            if recent_wins >= 4:
                return 1.15  # 15% bonus pendant les bonnes periodes

        return 1.0

    def can_open_position(
        self,
        state: BotState,
        size_usd: float,
    ) -> tuple[bool, str]:
        """Verifie si on peut ouvrir une nouvelle position."""
        # Max positions
        if len(state.positions) >= self.config.max_positions:
            return False, "max_positions_reached"

        # Exposition totale
        total_exposure = sum(
            p.get("size_usd", 0) if isinstance(p, dict) else p.size_usd
            for p in state.positions.values()
        )
        equity = state.capital + total_exposure
        if equity <= 0:
            return False, "no_equity"

        max_remaining = equity * self.config.max_total_exposure_pct - total_exposure
        if size_usd > max_remaining:
            return False, f"exposure_limit ({total_exposure:.0f}/{equity * self.config.max_total_exposure_pct:.0f})"

        # Capital disponible
        if size_usd > state.capital * 0.95:
            return False, "insufficient_capital"

        # Daily loss limit dynamique : se resserre si on perd beaucoup
        risk_mult = self._get_risk_multiplier()
        effective_daily_limit = self.config.daily_loss_limit_pct * risk_mult
        if state.daily_pnl < -(equity * effective_daily_limit):
            return False, f"daily_loss_limit (adjusted x{risk_mult:.2f})"

        # Max drawdown dynamique : warning zone avant le hard stop
        if state.peak_equity > 0:
            current_dd = (state.peak_equity - equity) / state.peak_equity
            if current_dd > self.config.max_drawdown_pct:
                return False, f"max_drawdown ({current_dd:.1%})"
            # Warning zone : reduire le sizing quand on approche du drawdown max
            if current_dd > self.config.max_drawdown_pct * 0.7:
                return True, "warning_drawdown"  # Autorise mais avec warning

        # Anti-correlation check : eviter de concentrer le risque
        # sur un seul type de marche (toutes les positions du meme cote)
        if len(state.positions) >= 3:
            sides = [
                p.get("side", "YES") if isinstance(p, dict) else p.side
                for p in state.positions.values()
            ]
            yes_count = sum(1 for s in sides if s == "YES")
            no_count = len(sides) - yes_count
            # Si > 80% du meme cote, reduire
            if max(yes_count, no_count) / len(sides) > 0.8:
                return True, "concentration_warning"

        return True, "ok"

    def compute_position_size(
        self,
        state: BotState,
        confidence: float,
    ) -> float:
        """Calcule la taille de position optimale avec sizing dynamique."""
        total_exposure = sum(
            p.get("size_usd", 0) if isinstance(p, dict) else p.size_usd
            for p in state.positions.values()
        )
        equity = state.capital + total_exposure

        max_size = equity * self.config.max_position_pct
        max_remaining = equity * self.config.max_total_exposure_pct - total_exposure

        # Sizing de base proportionnel a la confidence
        base_size = max_size * confidence

        # Multiplicateur de risque dynamique
        risk_mult = self._get_risk_multiplier()
        adjusted_size = base_size * risk_mult

        # Drawdown adjustment : reduire le sizing progressivement en drawdown
        if state.peak_equity > 0:
            current_dd = (state.peak_equity - equity) / state.peak_equity
            dd_ratio = current_dd / max(self.config.max_drawdown_pct, 0.01)
            if dd_ratio > 0.5:
                # Reduire lineairement de 50% a 100% du drawdown max
                dd_reduction = max(0.3, 1.0 - dd_ratio)
                adjusted_size *= dd_reduction

        size = min(adjusted_size, max_remaining, state.capital * 0.90)
        return max(0, size)


# ================================================================
#  HEDGE FUND BOT
# ================================================================

class HedgeFundBot:
    """Bot de trading autonome pour Polymarket."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.store = StateStore(config.state_file)
        self.state = self.store.load()
        self.risk = RiskManager(config)
        self._running = False
        self._lock = threading.Lock()

        # Initialiser le capital si premier lancement
        if self.state.started_at == "":
            self.state.capital = config.initial_capital
            self.state.peak_equity = config.initial_capital
            self.state.started_at = datetime.now().isoformat()

        # Client Polymarket (read-only)
        self.client = PolymarketClient(rate_limit_delay=0.3)

        # Client trading (live seulement)
        self.trading_client = None
        if not config.dry_run:
            pk = os.environ.get("POLYMARKET_PRIVATE_KEY", "")
            if pk:
                try:
                    self.trading_client = PolymarketTradingClient(pk)
                    logger.info("LIVE TRADING MODE")
                except Exception as e:
                    logger.error(f"Impossible d'initialiser le trading client: {e}")
                    config.dry_run = True
            else:
                logger.warning("POLYMARKET_PRIVATE_KEY absent, passage en dry-run")
                config.dry_run = True

        # Strategie — parametres depuis le config manager si disponible
        try:
            _cm = ConfigManager()
            _sp = _cm.get_strategy_params()
        except Exception:
            _sp = {}

        if config.strategy == "insurance_seller":
            self.strategy = InsuranceSellerStrategy()
        else:
            self.strategy = AlphaCompositeStrategy(
                min_consensus=_sp.get("min_consensus", 0.14),
                min_agreeing_strategies=_sp.get("min_agreeing_strategies", 2),
                spread_filter=_sp.get("spread_filter", 0.10),
                volume_percentile_filter=_sp.get("volume_percentile_filter", 28),
                max_price_extreme=_sp.get("max_price_extreme", 0.89),
                min_price_extreme=_sp.get("min_price_extreme", 0.09),
                stop_loss=_sp.get("stop_loss", 0.25),
                take_profit=_sp.get("take_profit", 0.50),
                trailing_stop=_sp.get("trailing_stop", 0.17),
                max_position_pct=_sp.get("strategy_max_position_pct", 0.08),
                max_positions=_sp.get("strategy_max_positions", 12),
            )

        # Trade logger — logging propre des trades avec frais
        self.trade_logger = TradeLogger(output_dir=config.log_dir)

        # Signal detector — Twitter/News
        self.signal_detector = SignalDetector(
            signal_log_path=str(Path(config.log_dir) / "signals.json")
        )

        # Cache des historiques
        self._histories: dict[str, pd.DataFrame] = {}

        # Setup logging
        self._setup_logging()

        logger.info("=" * 60)
        logger.info("  HEDGE FUND BOT INITIALISE")
        logger.info(f"  Strategie : {self.strategy.name}")
        logger.info(f"  Capital   : ${self.state.capital:,.2f}")
        logger.info(f"  Mode      : {'DRY RUN' if config.dry_run else 'LIVE'}")
        logger.info(f"  Scan      : toutes les {config.scan_interval_seconds}s")
        logger.info("=" * 60)

    def _setup_logging(self):
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        ))

        # File handler
        fh = logging.FileHandler(
            log_dir / f"bot_{datetime.now():%Y%m%d}.log"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

        logger.addHandler(ch)
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)

    # ================================================================
    #  BOUCLE PRINCIPALE
    # ================================================================

    def run(self, max_iterations: int = 0):
        """Boucle principale du bot."""
        self._running = True

        def _handle_signal(sig, frame):
            logger.info("Signal d'arret recu, fermeture propre...")
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        try:
            while self._running:
                self.state.iteration += 1
                if max_iterations > 0 and self.state.iteration > max_iterations:
                    break

                self._run_iteration()

                # Sauvegarder l'etat
                self.store.save(self.state)

                if self._running:
                    logger.info(f"Attente {self.config.scan_interval_seconds}s...")
                    # Sleep interruptible
                    for _ in range(self.config.scan_interval_seconds):
                        if not self._running:
                            break
                        time.sleep(1)

        except Exception as e:
            logger.error(f"Erreur fatale: {e}", exc_info=True)
            self.state.errors.append({
                "time": datetime.now().isoformat(),
                "error": str(e),
                "type": "fatal",
            })
        finally:
            self.store.save(self.state)
            logger.info(f"Bot arrete. PnL total: ${self.state.total_pnl:+,.2f}")

    def _run_iteration(self):
        """Execute une iteration complete."""
        now = datetime.now()
        logger.info(f"\n{'='*50}")
        logger.info(f"  Iteration {self.state.iteration} | {now:%Y-%m-%d %H:%M:%S}")
        logger.info(f"{'='*50}")

        # Reset daily PnL a minuit
        if now.hour == 0 and now.minute < 6:
            if self.state.daily_pnl != 0:
                logger.info(f"Reset daily PnL (etait ${self.state.daily_pnl:+,.2f})")
                self.state.daily_pnl = 0.0

        try:
            # 1. Scanner les marches
            markets = self._scan_markets()

            # 2. Scanner Twitter/News pour signaux
            self._signal_boosts = {}
            try:
                twitter_signals = self.signal_detector.scan_and_match(markets)
                for sig in twitter_signals:
                    self._signal_boosts[sig.market_id] = {
                        "direction": sig.direction,
                        "confidence_boost": sig.confidence * 0.3,
                    }
                if twitter_signals:
                    logger.info(f"  Signaux Twitter: {len(twitter_signals)} detectes")
            except Exception as e:
                logger.debug(f"Scan Twitter echoue: {e}")

            # 3. Mettre a jour les positions existantes
            self._update_positions()

            # 4. Evaluer les signaux et ouvrir des positions
            self._evaluate_markets(markets)

            # 4. Mettre a jour l'equity
            self._update_equity()

            # 5. Afficher le statut
            self._log_status()

            self.state.last_scan = now.isoformat()

        except Exception as e:
            logger.error(f"Erreur iteration: {e}", exc_info=True)
            self.state.errors.append({
                "time": now.isoformat(),
                "error": str(e),
                "type": "iteration",
            })

    # ================================================================
    #  SCAN DES MARCHES
    # ================================================================

    def _scan_markets(self) -> list[PolymarketMarket]:
        """Scanne et filtre les marches actifs."""
        try:
            markets = self.client.get_all_active_markets(
                min_volume=self.config.min_volume,
                min_liquidity=self.config.min_liquidity,
                max_markets=100,
            )
        except Exception as e:
            logger.error(f"Scan marches echoue: {e}")
            return []

        # Filtrer par spread
        eligible = []
        for m in markets[:50]:  # Limiter les appels API
            try:
                spread_info = self.client.get_spread(m.yes_token_id)
                spread = spread_info["spread"]
                if self.config.min_spread <= spread <= self.config.max_spread:
                    eligible.append(m)
            except Exception:
                continue

        self.state.markets_scanned = len(eligible)
        logger.info(f"  Marches scannes: {len(markets)} total, {len(eligible)} eligibles")
        return eligible

    # ================================================================
    #  MISE A JOUR DES POSITIONS
    # ================================================================

    def _update_positions(self):
        """Met a jour les prix et verifie les sorties."""
        for cid in list(self.state.positions.keys()):
            pos = self.state.positions[cid]
            if isinstance(pos, dict):
                token_id = pos.get("token_id", "")
                entry_price = pos.get("entry_price", 0.5)
                side = pos.get("side", "YES")
                peak = pos.get("peak_price", entry_price)
                size_usd = pos.get("size_usd", 0)
                question = pos.get("question", "")
                entry_time = pos.get("entry_time", "")
            else:
                token_id = pos.token_id
                entry_price = pos.entry_price
                side = pos.side
                peak = pos.peak_price
                size_usd = pos.size_usd
                question = pos.question
                entry_time = pos.entry_time

            try:
                current_price = self.client.get_midpoint(token_id)
            except Exception:
                continue

            # Calculer PnL non realise
            if side == "YES":
                pnl_pct = (current_price - entry_price) / max(entry_price, 0.01)
            else:
                pnl_pct = (entry_price - current_price) / max(entry_price, 0.01)

            unrealized_pnl = pnl_pct * size_usd

            # Mettre a jour le peak price et loguer si nouveau peak
            if current_price > peak:
                old_peak = peak
                peak = current_price
                if old_peak > 0 and (peak - old_peak) / old_peak > 0.005:
                    logger.debug(
                        f"  Peak update {question[:30]}: {old_peak:.4f} -> {peak:.4f}"
                    )

            shares = pos.get("shares", size_usd / max(entry_price, 0.01)) if isinstance(pos, dict) else getattr(pos, "shares", size_usd / max(entry_price, 0.01))

            # Mettre a jour la position
            updated = {
                "market_id": cid,
                "question": question,
                "side": side,
                "token_id": token_id,
                "entry_price": entry_price,
                "size_usd": size_usd,
                "shares": shares,
                "entry_time": entry_time,
                "order_id": pos.get("order_id", "") if isinstance(pos, dict) else getattr(pos, "order_id", ""),
                "peak_price": peak,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": pnl_pct,
            }
            self.state.positions[cid] = updated

            # Verifier les conditions de sortie
            should_exit = False
            exit_reason = ""

            # Stop-loss
            if pnl_pct <= -self.strategy.stop_loss:
                should_exit = True
                exit_reason = "stop_loss"

            # Take-profit
            elif pnl_pct >= self.strategy.take_profit:
                should_exit = True
                exit_reason = "take_profit"

            # Trailing stop — calcul base sur le prix
            elif self.strategy.trailing_stop > 0 and peak > entry_price:
                trailing_stop_pct = self.strategy.trailing_stop
                trailing_stop_price = peak * (1 - trailing_stop_pct)
                if current_price < trailing_stop_price:
                    should_exit = True
                    exit_reason = "trailing_stop"
                    logger.info(
                        f"  Trailing stop declenche: prix {current_price:.4f} < "
                        f"stop {trailing_stop_price:.4f} (peak {peak:.4f})"
                    )

            if should_exit:
                self._close_position(cid, current_price, exit_reason)

    def _close_position(self, condition_id: str, exit_price: float, reason: str):
        """Ferme une position avec frais Polymarket 2%."""
        with self._lock:
            pos = self.state.positions.pop(condition_id, None)
        if not pos:
            return

        if isinstance(pos, dict):
            entry_price = pos.get("entry_price", 0.5)
            side = pos.get("side", "YES")
            size_usd = pos.get("size_usd", 0)
            question = pos.get("question", "")
            entry_time = pos.get("entry_time", "")
            token_id = pos.get("token_id", "")
            shares = pos.get("shares", size_usd / max(entry_price, 0.01))
        else:
            entry_price = pos.entry_price
            side = pos.side
            size_usd = pos.size_usd
            question = pos.question
            entry_time = pos.entry_time
            token_id = pos.token_id
            shares = pos.shares

        # PnL brut
        if side == "YES":
            pnl_gross = (exit_price - entry_price) * shares
        else:
            pnl_gross = (entry_price - exit_price) * shares

        # Frais Polymarket 2% entree + sortie
        fees_entry = size_usd * POLYMARKET_FEE_PCT
        fees_exit = shares * exit_price * POLYMARKET_FEE_PCT
        fees_total = fees_entry + fees_exit

        pnl = pnl_gross - fees_total
        pnl_pct = pnl / max(size_usd, 0.01)

        self.state.capital += size_usd + pnl
        self.state.daily_pnl += pnl
        self.state.total_pnl += pnl
        self.risk.record_trade_result(pnl)

        # Executer la vente sur Polymarket
        if self.trading_client and not self.config.dry_run:
            try:
                self.trading_client.place_market_order(
                    token_id=token_id,
                    amount_usd=size_usd,
                    side="SELL",
                )
            except Exception as e:
                logger.error(f"Echec de la fermeture sur Polymarket: {e}")

        # Logger via TradeLogger (CSV + JSON)
        self.trade_logger.log_exit(
            market_id=condition_id,
            exit_price=exit_price,
            exit_reason=reason,
        )

        trade = {
            "market_id": condition_id,
            "question": question,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "size_usd": size_usd,
            "pnl": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 4),
            "entry_time": entry_time,
            "exit_time": datetime.now().isoformat(),
            "reason": reason,
            "fees_total": round(fees_total, 4),
        }
        self.state.trades.append(trade)

        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        logger.info(
            f"  CLOSE [{reason}] {side} | PnL brut: ${pnl_gross:+.2f} | "
            f"Frais: ${fees_total:.2f} | Net: {pnl_str} ({pnl_pct:+.1%}) | {question[:50]}"
        )

    # ================================================================
    #  EVALUATION DES SIGNAUX
    # ================================================================

    def _evaluate_markets(self, markets: list[PolymarketMarket]):
        """Evalue les signaux et ouvre des positions."""
        if len(self.state.positions) >= self.config.max_positions:
            return

        signals_count = 0
        for market in markets:
            if market.condition_id in self.state.positions:
                continue
            if len(self.state.positions) >= self.config.max_positions:
                break

            try:
                # Recuperer l'historique
                history = self._get_history(market)
                if history is None or len(history) < 30:
                    continue

                # Construire la barre actuelle
                current_bar = history.iloc[-1].copy()

                # Generer le signal
                action, confidence = self.strategy.generate_signal(
                    market.condition_id,
                    current_bar,
                    history.iloc[:-1],
                )

                signals_count += 1

                # Booster la confiance si un signal Twitter correspond
                boost = self._signal_boosts.get(market.condition_id)
                if boost and action in ("BUY_YES", "BUY_NO"):
                    signal_dir = "BUY_YES" if boost["direction"] == "YES" else "BUY_NO"
                    if action == signal_dir:
                        confidence = min(1.0, confidence + boost["confidence_boost"])
                        logger.info(f"  Signal Twitter boost: +{boost['confidence_boost']:.2f} "
                                    f"-> conf={confidence:.2f}")

                if action in ("BUY_YES", "BUY_NO") and confidence > 0:
                    self._open_position(market, action, confidence, current_bar)

            except Exception as e:
                logger.debug(f"Erreur evaluation {market.condition_id[:8]}: {e}")
                continue

        self.state.signals_generated += signals_count
        if signals_count > 0:
            logger.info(f"  Signaux evalues: {signals_count}")

    def _get_history(self, market: PolymarketMarket) -> Optional[pd.DataFrame]:
        """Recupere ou met a jour l'historique d'un marche."""
        cid = market.condition_id

        # Cache: rafraichir si > 10 min
        if cid in self._histories:
            last_ts = self._histories[cid]["timestamp"].iloc[-1]
            age = datetime.now() - last_ts.to_pydatetime().replace(tzinfo=None)
            if age < timedelta(minutes=10):
                return self._histories[cid]

        try:
            df = self.client.get_market_history_for_backtest(
                market,
                fidelity=self.config.history_fidelity,
            )
            if not df.empty:
                self._histories[cid] = df
                return df
        except Exception as e:
            logger.debug(f"Historique echoue pour {cid[:8]}: {e}")

        return self._histories.get(cid)

    def _open_position(
        self,
        market: PolymarketMarket,
        action: str,
        confidence: float,
        current_bar: pd.Series,
    ):
        """Ouvre une nouvelle position."""
        side = "YES" if action == "BUY_YES" else "NO"
        token_id = market.yes_token_id if side == "YES" else market.no_token_id
        price = current_bar["mid_price"]

        # Sizing via le risk manager
        size_usd = self.risk.compute_position_size(self.state, confidence)

        # Verification risque
        can_open, reason = self.risk.can_open_position(self.state, size_usd)
        if not can_open:
            logger.debug(f"Position refusee: {reason}")
            return

        if size_usd < 5:
            return

        shares = size_usd / max(price, 0.01)

        # Executer l'achat
        order_id = ""
        if self.trading_client and not self.config.dry_run:
            try:
                limit_price = round(price + 0.005, 2)
                limit_price = min(limit_price, 0.99)
                result = self.trading_client.place_limit_order(
                    token_id=token_id,
                    price=limit_price,
                    size=shares,
                    side="BUY",
                )
                order_id = result.get("orderID", "")
            except Exception as e:
                logger.error(f"Echec placement ordre: {e}")
                return
        else:
            order_id = f"DRY-{int(time.time())}"

        self.state.capital -= size_usd

        entry_time = datetime.now().isoformat()

        with self._lock:
            self.state.positions[market.condition_id] = {
                "market_id": market.condition_id,
                "question": market.question,
                "side": side,
                "token_id": token_id,
                "entry_price": price,
                "size_usd": size_usd,
                "shares": shares,
                "entry_time": entry_time,
                "order_id": order_id,
                "peak_price": price,
                "current_price": price,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
            }

        # Logger via TradeLogger (CSV + JSON)
        self.trade_logger.log_entry(
            market_id=market.condition_id,
            token_id=token_id,
            question=market.question,
            side=side,
            entry_price=price,
            size_usd=size_usd,
            shares=shares,
            entry_time=entry_time,
            order_id=order_id,
        )

        logger.info(
            f"  OPEN {side} | ${size_usd:.0f} @ {price:.3f} "
            f"(conf={confidence:.2f}) | {market.question[:50]}"
        )

    # ================================================================
    #  EQUITY & REPORTING
    # ================================================================

    def _update_equity(self):
        """Met a jour l'equity curve."""
        total_exposure = sum(
            p.get("size_usd", 0) if isinstance(p, dict) else p.size_usd
            for p in self.state.positions.values()
        )
        total_unrealized = sum(
            p.get("unrealized_pnl", 0) if isinstance(p, dict) else p.unrealized_pnl
            for p in self.state.positions.values()
        )
        equity = self.state.capital + total_exposure + total_unrealized

        if equity > self.state.peak_equity:
            self.state.peak_equity = equity

        self.state.equity_history.append({
            "timestamp": datetime.now().isoformat(),
            "equity": equity,
            "capital": self.state.capital,
            "exposure": total_exposure,
            "unrealized_pnl": total_unrealized,
            "n_positions": len(self.state.positions),
        })

    def _log_status(self):
        """Affiche le statut actuel."""
        total_exposure = sum(
            p.get("size_usd", 0) if isinstance(p, dict) else p.size_usd
            for p in self.state.positions.values()
        )
        total_unrealized = sum(
            p.get("unrealized_pnl", 0) if isinstance(p, dict) else p.unrealized_pnl
            for p in self.state.positions.values()
        )
        equity = self.state.capital + total_exposure + total_unrealized
        dd = (self.state.peak_equity - equity) / self.state.peak_equity * 100 if self.state.peak_equity > 0 else 0

        logger.info(f"  --- STATUT ---")
        logger.info(f"  Capital cash    : ${self.state.capital:,.2f}")
        logger.info(f"  Equity totale   : ${equity:,.2f}")
        logger.info(f"  Positions       : {len(self.state.positions)}")
        logger.info(f"  Exposition      : ${total_exposure:,.2f} ({total_exposure/max(equity,1)*100:.1f}%)")
        logger.info(f"  PnL non realise : ${total_unrealized:+,.2f}")
        logger.info(f"  PnL journalier  : ${self.state.daily_pnl:+,.2f}")
        logger.info(f"  PnL total       : ${self.state.total_pnl:+,.2f}")
        logger.info(f"  Drawdown        : {dd:.1f}%")

        for cid, pos in self.state.positions.items():
            if isinstance(pos, dict):
                side = pos.get("side", "?")
                size = pos.get("size_usd", 0)
                entry = pos.get("entry_price", 0)
                current = pos.get("current_price", 0)
                upnl = pos.get("unrealized_pnl", 0)
                question = pos.get("question", "")
            else:
                side, size, entry = pos.side, pos.size_usd, pos.entry_price
                current, upnl = pos.current_price, pos.unrealized_pnl
                question = pos.question
            logger.info(
                f"    [{side}] ${size:.0f} @ {entry:.3f} -> {current:.3f} "
                f"({upnl:+.2f}) | {question[:40]}"
            )

    # ================================================================
    #  API POUR LE DASHBOARD
    # ================================================================

    def get_dashboard_data(self) -> dict:
        """Retourne toutes les donnees pour le dashboard."""
        total_exposure = sum(
            p.get("size_usd", 0) if isinstance(p, dict) else p.size_usd
            for p in self.state.positions.values()
        )
        total_unrealized = sum(
            p.get("unrealized_pnl", 0) if isinstance(p, dict) else p.unrealized_pnl
            for p in self.state.positions.values()
        )
        equity = self.state.capital + total_exposure + total_unrealized
        dd = (self.state.peak_equity - equity) / self.state.peak_equity if self.state.peak_equity > 0 else 0

        # Stats des trades
        trades = self.state.trades
        pnls = [t.get("pnl", 0) if isinstance(t, dict) else t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        return {
            "status": "running" if self._running else "stopped",
            "mode": "DRY RUN" if self.config.dry_run else "LIVE",
            "strategy": self.strategy.name,
            "started_at": self.state.started_at,
            "last_scan": self.state.last_scan,
            "iteration": self.state.iteration,
            "overview": {
                "capital": round(self.state.capital, 2),
                "equity": round(equity, 2),
                "total_pnl": round(self.state.total_pnl, 2),
                "daily_pnl": round(self.state.daily_pnl, 2),
                "unrealized_pnl": round(total_unrealized, 2),
                "exposure": round(total_exposure, 2),
                "exposure_pct": round(total_exposure / max(equity, 1) * 100, 1),
                "drawdown_pct": round(dd * 100, 2),
                "peak_equity": round(self.state.peak_equity, 2),
                "initial_capital": self.config.initial_capital,
                "total_return_pct": round((equity / self.config.initial_capital - 1) * 100, 2),
            },
            "positions": list(self.state.positions.values()),
            "recent_trades": trades[-20:],
            "all_trades": trades,
            "trade_stats": {
                "total_trades": len(trades),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": round(len(wins) / max(len(trades), 1) * 100, 1),
                "avg_win": round(np.mean(wins), 2) if wins else 0,
                "avg_loss": round(np.mean(losses), 2) if losses else 0,
                "profit_factor": round(abs(sum(wins) / sum(losses)), 2) if losses else 0,
                "largest_win": round(max(pnls), 2) if pnls else 0,
                "largest_loss": round(min(pnls), 2) if pnls else 0,
            },
            "equity_history": self.state.equity_history[-200:],
            "markets_scanned": self.state.markets_scanned,
            "signals_generated": self.state.signals_generated,
            "errors": self.state.errors[-10:],
        }


# ================================================================
#  MAIN
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Polymarket Hedge Fund Bot")
    parser.add_argument("--live", action="store_true", help="Mode live (vrai argent)")
    parser.add_argument("--capital", type=float, default=None, help="Capital initial ($)")
    parser.add_argument("--strategy", default=None,
                        choices=["alpha_composite", "insurance_seller"],
                        help="Strategie de trading")
    parser.add_argument("--interval", type=int, default=None, help="Intervalle de scan (secondes)")
    parser.add_argument("--max-positions", type=int, default=None, help="Nombre max de positions")
    parser.add_argument("--max-iterations", type=int, default=0, help="0 = infini")
    parser.add_argument("--dashboard", action="store_true", help="Lancer le dashboard web")
    parser.add_argument("--port", type=int, default=5050, help="Port du dashboard")
    parser.add_argument("--state-file", default="bot_state.json", help="Fichier d'etat")

    args = parser.parse_args()

    # Charger la config depuis le gestionnaire de profils
    cm = ConfigManager()
    active = cm.get_active()
    bot_cfg = active["bot"]
    strat_cfg = active["strategy"]

    # Les arguments CLI overrident la config sauvegardee
    config = BotConfig(
        initial_capital=args.capital if args.capital is not None else bot_cfg["initial_capital"],
        max_position_pct=bot_cfg["max_position_pct"],
        max_total_exposure_pct=bot_cfg["max_total_exposure_pct"],
        max_positions=args.max_positions if args.max_positions is not None else bot_cfg["max_positions"],
        min_volume=bot_cfg["min_volume"],
        min_liquidity=bot_cfg["min_liquidity"],
        min_spread=bot_cfg["min_spread"],
        max_spread=bot_cfg["max_spread"],
        scan_interval_seconds=args.interval if args.interval is not None else bot_cfg["scan_interval_seconds"],
        history_fidelity=bot_cfg["history_fidelity"],
        daily_loss_limit_pct=bot_cfg["daily_loss_limit_pct"],
        max_drawdown_pct=bot_cfg["max_drawdown_pct"],
        dry_run=not args.live if args.live else bot_cfg["dry_run"],
        strategy=args.strategy if args.strategy is not None else bot_cfg["strategy"],
        state_file=args.state_file,
    )

    bot = HedgeFundBot(config)

    # Render.com definit PORT automatiquement — priorite a $PORT
    port = int(os.environ.get("PORT", 0)) or args.port or 5050

    # Lancer le dashboard dans un thread separe
    if args.dashboard:
        try:
            from web_dashboard import create_dashboard_app, _start_keep_alive
            app = create_dashboard_app(bot, config_manager=cm)

            dash_thread = threading.Thread(
                target=lambda: app.run(
                    host="0.0.0.0",
                    port=port,
                    debug=False,
                    use_reloader=False,
                ),
                daemon=True,
            )
            dash_thread.start()
            logger.info(f"Dashboard demarre sur http://localhost:{port}")
            logger.info(f"  Parametres : http://localhost:{port}/settings")

            # Keep-alive pour les hebergeurs gratuits (Render, etc.)
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                _start_keep_alive(render_url)
                logger.info(f"  Keep-alive actif pour {render_url}")
        except ImportError as e:
            logger.warning(f"Dashboard non disponible: {e}")

    # Lancer le bot
    bot.run(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()
