"""
Module de trading live sur Polymarket.

Connecte les stratégies de backtesting au vrai Polymarket via :
- Scan continu des marchés actifs
- Exécution des signaux via la CLOB API
- Gestion des positions et du risque en temps réel
- Logging complet de toutes les opérations
- Mode dry-run (paper trading) pour tester sans risque

Architecture :
    Scanner → Stratégie → Risk Manager → Executor → Logger
"""

import json
import time
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .polymarket_client import PolymarketClient, PolymarketTradingClient, PolymarketMarket
from .strategies import BaseStrategy, AlphaCompositeStrategy, Position

logger = logging.getLogger(__name__)


@dataclass
class LivePosition:
    """Position live sur un marché Polymarket."""
    market: PolymarketMarket
    side: str  # "YES" ou "NO"
    token_id: str
    entry_price: float
    size_usd: float
    shares: float
    entry_time: datetime
    order_id: str = ""
    peak_price: float = 0.0


@dataclass
class LiveTraderConfig:
    """Configuration du trader live."""
    # Capital
    initial_capital: float = 1000.0
    max_position_pct: float = 0.05  # 5% max par position
    max_total_exposure_pct: float = 0.30  # 30% max d'exposition totale
    max_positions: int = 8

    # Filtres de marchés
    min_market_volume: float = 50000  # Volume minimum en $
    min_market_liquidity: float = 5000  # Liquidité minimum
    min_spread: float = 0.005  # Spread minimum acceptable
    max_spread: float = 0.08  # Spread maximum acceptable

    # Exécution
    scan_interval_seconds: int = 300  # Scanner toutes les 5 min
    history_fidelity_minutes: int = 60  # Granularité historique
    order_type: str = "limit"  # "limit" ou "market"
    limit_offset: float = 0.005  # Offset par rapport au midpoint pour les limits

    # Risk management
    daily_loss_limit_pct: float = 0.05  # Stop trading si -5% dans la journée

    # Mode
    dry_run: bool = True  # True = paper trading, False = real money
    log_dir: str = "logs"


class LiveTrader:
    """
    Trader live pour Polymarket.

    Usage:
        config = LiveTraderConfig(initial_capital=1000, dry_run=True)
        trader = LiveTrader(
            strategy=AlphaCompositeStrategy(),
            config=config,
            private_key="0x..." if not dry_run else None,
        )
        trader.run()  # Boucle infinie
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        config: LiveTraderConfig | None = None,
        private_key: str | None = None,
    ):
        self.strategy = strategy
        self.config = config or LiveTraderConfig()
        self.capital = self.config.initial_capital
        self.positions: dict[str, LivePosition] = {}
        self.trade_log: list[dict] = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

        # Client read-only (toujours disponible)
        self.client = PolymarketClient(rate_limit_delay=0.3)

        # Client trading (seulement si pas dry_run)
        self.trading_client = None
        if not self.config.dry_run and private_key:
            self.trading_client = PolymarketTradingClient(private_key)
            logger.info("LIVE TRADING MODE - Real money!")
        else:
            logger.info("DRY RUN MODE - Paper trading")

        # Historiques par marché (cache)
        self._market_histories: dict[str, pd.DataFrame] = {}

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure le logging dans un fichier."""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)

        fh = logging.FileHandler(
            log_dir / f"trader_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)

    # ================================================================
    #  BOUCLE PRINCIPALE
    # ================================================================

    def run(self, max_iterations: int = 0):
        """
        Boucle principale du trader.

        Args:
            max_iterations: 0 = infini, >0 = nombre d'itérations
        """
        logger.info("=" * 60)
        logger.info("  POLYMARKET LIVE TRADER STARTED")
        logger.info(f"  Strategy: {self.strategy.name}")
        logger.info(f"  Capital: ${self.capital:,.2f}")
        logger.info(f"  Mode: {'DRY RUN' if self.config.dry_run else 'LIVE'}")
        logger.info("=" * 60)

        iteration = 0
        try:
            while True:
                iteration += 1
                if max_iterations > 0 and iteration > max_iterations:
                    break

                logger.info(f"\n--- Iteration {iteration} | {datetime.now():%H:%M:%S} ---")

                # Reset daily PnL à minuit (robuste : tracker la date du dernier reset)
                today = datetime.now().date()
                if not hasattr(self, '_last_reset_date') or self._last_reset_date != today:
                    self._last_reset_date = today
                    self.daily_pnl = 0.0

                # Check daily loss limit
                if self._check_daily_loss_limit():
                    logger.warning("Daily loss limit reached, skipping iteration")
                    time.sleep(self.config.scan_interval_seconds)
                    continue

                # 1. Scanner les marchés
                markets = self._scan_markets()
                logger.info(f"  Found {len(markets)} eligible markets")

                # 2. Mettre à jour les positions existantes
                self._update_positions(markets)

                # 3. Évaluer les signaux et trader
                self._evaluate_and_trade(markets)

                # 4. Afficher le statut
                self._print_status()

                # 5. Sauvegarder le log
                self._save_trade_log()

                logger.info(f"  Sleeping {self.config.scan_interval_seconds}s...")
                time.sleep(self.config.scan_interval_seconds)

        except KeyboardInterrupt:
            logger.info("\nTrader stopped by user")
        finally:
            self._save_trade_log()
            logger.info(f"Final PnL: ${self.total_pnl:,.2f}")

    # ================================================================
    #  SCAN DES MARCHES
    # ================================================================

    def _scan_markets(self) -> list[PolymarketMarket]:
        """Scan les marchés éligibles."""
        try:
            markets = self.client.get_all_active_markets(
                min_volume=self.config.min_market_volume,
                min_liquidity=self.config.min_market_liquidity,
                max_markets=100,
            )
        except Exception as e:
            logger.error(f"Failed to scan markets: {e}")
            return []

        # Filtrer par spread
        eligible = []
        for m in markets:
            try:
                spread_info = self.client.get_spread(m.yes_token_id)
                spread = spread_info["spread"]
                if self.config.min_spread <= spread <= self.config.max_spread:
                    eligible.append(m)
            except Exception:
                continue

        return eligible

    # ================================================================
    #  GESTION DES POSITIONS
    # ================================================================

    def _update_positions(self, markets: list[PolymarketMarket]):
        """Met à jour les positions avec les prix actuels."""
        market_map = {m.condition_id: m for m in markets}

        for cid in list(self.positions.keys()):
            pos = self.positions[cid]
            try:
                current_price = self.client.get_midpoint(pos.token_id)
            except Exception:
                continue

            # Pour les positions NO, on raisonne en "effective price" (valeur NO)
            if pos.side == "YES":
                effective_price = current_price
                unrealized_pnl_pct = (current_price - pos.entry_price) / max(pos.entry_price, 0.01)
            else:
                effective_price = 1.0 - current_price  # Prix effectif du NO
                no_entry = 1.0 - pos.entry_price
                unrealized_pnl_pct = (effective_price - no_entry) / max(no_entry, 0.01)

            # Mise à jour peak price (pour trailing stop) — en espace effectif
            if effective_price > pos.peak_price:
                pos.peak_price = effective_price

            should_exit = False
            exit_reason = ""

            # Stop-loss
            if unrealized_pnl_pct <= -self.strategy.stop_loss:
                should_exit = True
                exit_reason = "stop_loss"

            # Take-profit
            elif unrealized_pnl_pct >= self.strategy.take_profit:
                should_exit = True
                exit_reason = "take_profit"

            # Trailing stop — raisonne en effective price
            elif self.strategy.trailing_stop > 0:
                if pos.side == "YES":
                    entry_eff = pos.entry_price
                else:
                    entry_eff = 1.0 - pos.entry_price
                if pos.peak_price > entry_eff:
                    peak_pnl = (pos.peak_price - entry_eff) / max(entry_eff, 0.01)
                    if peak_pnl > 0.03 and (peak_pnl - unrealized_pnl_pct) > self.strategy.trailing_stop:
                        should_exit = True
                        exit_reason = "trailing_stop"

            # Marché fermé
            if cid in market_map and market_map[cid].closed:
                should_exit = True
                exit_reason = "market_closed"

            if should_exit:
                self._close_position(cid, current_price, exit_reason)

    def _close_position(self, condition_id: str, exit_price: float, reason: str):
        """Ferme une position."""
        pos = self.positions.pop(condition_id, None)
        if not pos:
            return

        if pos.side == "YES":
            pnl = (exit_price - pos.entry_price) * pos.shares
        else:
            pnl = (pos.entry_price - exit_price) * pos.shares

        self.capital += pos.size_usd + pnl
        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Exécuter la vente sur Polymarket
        if self.trading_client and not self.config.dry_run:
            try:
                self.trading_client.place_market_order(
                    token_id=pos.token_id,
                    amount_usd=pos.size_usd,
                    side="SELL",
                )
            except Exception as e:
                logger.error(f"Failed to close position: {e}")

        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "market_id": condition_id,
            "question": pos.market.question,
            "side": pos.side,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "size_usd": pos.size_usd,
            "shares": pos.shares,
            "pnl": pnl,
            "reason": reason,
        }
        self.trade_log.append(trade_record)

        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        logger.info(f"  CLOSE [{reason}] {pos.side} | {pnl_str} | {pos.market.question[:50]}")

    # ================================================================
    #  EVALUATION DES SIGNAUX
    # ================================================================

    def _evaluate_and_trade(self, markets: list[PolymarketMarket]):
        """Évalue les signaux et ouvre des positions."""
        if len(self.positions) >= self.config.max_positions:
            return

        for market in markets:
            if market.condition_id in self.positions:
                continue
            if len(self.positions) >= self.config.max_positions:
                break

            try:
                # Récupérer l'historique
                history = self._get_or_update_history(market)
                if history is None or len(history) < 30:
                    continue

                # Construire la barre actuelle
                current_bar = history.iloc[-1].copy()

                # Générer le signal
                action, confidence = self.strategy.generate_signal(
                    market.condition_id,
                    current_bar,
                    history.iloc[:-1],  # Historique sans la dernière barre
                )

                if action in ("BUY_YES", "BUY_NO") and confidence > 0:
                    self._open_position(market, action, confidence, current_bar)

            except Exception as e:
                logger.debug(f"Error evaluating {market.condition_id}: {e}")
                continue

    def _get_or_update_history(self, market: PolymarketMarket) -> pd.DataFrame | None:
        """Récupère ou met à jour l'historique d'un marché."""
        cid = market.condition_id

        # Rafraîchir si > 5 min
        if cid in self._market_histories:
            last_ts = self._market_histories[cid]["timestamp"].iloc[-1]
            if (datetime.now() - last_ts.to_pydatetime().replace(tzinfo=None)) < timedelta(minutes=10):
                return self._market_histories[cid]

        try:
            df = self.client.get_market_history_for_backtest(
                market,
                fidelity=self.config.history_fidelity_minutes,
            )
            if not df.empty:
                self._market_histories[cid] = df
                return df
        except Exception as e:
            logger.debug(f"Failed to fetch history for {cid}: {e}")

        return self._market_histories.get(cid)

    def _open_position(
        self,
        market: PolymarketMarket,
        action: str,
        confidence: float,
        current_bar: pd.Series,
    ):
        """Ouvre une position."""
        side = "YES" if action == "BUY_YES" else "NO"
        token_id = market.yes_token_id if side == "YES" else market.no_token_id
        price = current_bar["mid_price"]

        # Sizing
        max_size = self.capital * self.config.max_position_pct
        current_exposure = sum(p.size_usd for p in self.positions.values())
        max_remaining = self.capital * self.config.max_total_exposure_pct - current_exposure
        if max_remaining <= 0:
            return

        size_usd = min(max_size * confidence, max_remaining)
        if size_usd < 5:  # Minimum $5
            return

        # Vérifier que le capital est suffisant
        if size_usd > self.capital:
            size_usd = self.capital
            if size_usd < 5:
                return

        shares = size_usd / max(price, 0.01)

        # Exécuter l'achat
        order_id = ""
        if self.trading_client and not self.config.dry_run:
            try:
                if self.config.order_type == "market":
                    result = self.trading_client.place_market_order(
                        token_id=token_id,
                        amount_usd=size_usd,
                        side="BUY",
                    )
                else:
                    # Limit order légèrement au-dessus du mid pour fill rapide
                    limit_price = round(price + self.config.limit_offset, 2)
                    limit_price = min(limit_price, 0.99)
                    result = self.trading_client.place_limit_order(
                        token_id=token_id,
                        price=limit_price,
                        size=shares,
                        side="BUY",
                    )
                order_id = result.get("orderID", "")
            except Exception as e:
                logger.error(f"Failed to open position: {e}")
                return
        else:
            order_id = f"DRY-{int(time.time())}"

        self.capital -= size_usd
        self.positions[market.condition_id] = LivePosition(
            market=market,
            side=side,
            token_id=token_id,
            entry_price=price,
            size_usd=size_usd,
            shares=shares,
            entry_time=datetime.now(),
            order_id=order_id,
            peak_price=price,
        )

        logger.info(
            f"  OPEN {side} | ${size_usd:.0f} @ {price:.3f} "
            f"(conf={confidence:.2f}) | {market.question[:50]}"
        )

    # ================================================================
    #  RISK MANAGEMENT
    # ================================================================

    def _check_daily_loss_limit(self) -> bool:
        """Vérifie si la limite de perte journalière est atteinte."""
        if self.config.initial_capital <= 0:
            return False
        daily_loss_pct = self.daily_pnl / self.config.initial_capital
        return daily_loss_pct < -self.config.daily_loss_limit_pct

    # ================================================================
    #  REPORTING
    # ================================================================

    def _print_status(self):
        """Affiche le statut actuel."""
        total_equity = self.capital + sum(p.size_usd for p in self.positions.values())
        n_pos = len(self.positions)
        exposure_pct = sum(p.size_usd for p in self.positions.values()) / total_equity * 100 if total_equity > 0 else 0

        logger.info(f"  Status: Capital=${self.capital:.0f} | "
                     f"Equity=${total_equity:.0f} | "
                     f"Positions={n_pos} | "
                     f"Exposure={exposure_pct:.1f}% | "
                     f"DayPnL=${self.daily_pnl:+.2f} | "
                     f"TotalPnL=${self.total_pnl:+.2f}")

        for cid, pos in self.positions.items():
            logger.info(f"    [{pos.side}] ${pos.size_usd:.0f} @ {pos.entry_price:.3f} | {pos.market.question[:40]}")

    def _save_trade_log(self):
        """Sauvegarde le log des trades."""
        if not self.trade_log:
            return

        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / "trades.json"

        with open(log_path, "w") as f:
            json.dump(self.trade_log, f, indent=2, default=str)

    def get_summary(self) -> dict:
        """Résumé des performances."""
        if not self.trade_log:
            return {"total_trades": 0, "total_pnl": 0}

        pnls = [t["pnl"] for t in self.trade_log]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        return {
            "total_trades": len(pnls),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / len(pnls) if pnls else 0,
            "total_pnl": sum(pnls),
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
            "profit_factor": abs(sum(wins) / sum(losses)) if losses else float("inf"),
            "capital": self.capital,
        }
