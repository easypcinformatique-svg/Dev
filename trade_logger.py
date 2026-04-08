"""
Module de logging propre pour les trades du bot Polymarket.

Enregistre chaque entree et sortie de position avec toutes les donnees reelles :
- market_id reel (hash Polymarket), token_id, question, side, prix, taille, timestamps ISO
- Frais Polymarket 2%, PnL brut et net
- Sauvegarde en CSV (trades_real.csv) et JSON (trades_real.json)
- Statistiques completes via get_stats()

Usage :
    logger = TradeLogger()
    logger.log_entry(entry_data)
    logger.log_exit(market_id, exit_data)
    stats = logger.get_stats()
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional

import re

import numpy as np

logger = logging.getLogger("trade_logger")

POLYMARKET_FEE_PCT = 0.02  # 2%

# Regex pour valider un market_id reel Polymarket (hash hex 64 chars avec prefixe 0x)
_REAL_MARKET_ID_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


def _validate_market_id(market_id: str) -> None:
    """Valide que le market_id est un hash Polymarket reel, pas un ID synthetique."""
    if not market_id:
        raise ValueError("market_id ne peut pas etre vide")
    if market_id.startswith("PM-") or not _REAL_MARKET_ID_RE.match(market_id):
        raise ValueError(
            f"market_id invalide: {market_id!r}. "
            f"Attendu: hash hex 0x + 64 chars (ex: 0xabc...def)"
        )


def _validate_exit_time(exit_time: str) -> None:
    """Valide que exit_time n'est pas une date epoch ou invalide."""
    if not exit_time:
        return
    try:
        dt = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
        if dt.year < 2020:
            raise ValueError(
                f"exit_time invalide: {exit_time!r}. "
                f"La date est anterieure a 2020 (date epoch?)."
            )
    except (ValueError, TypeError) as e:
        if "exit_time invalide" in str(e):
            raise
        raise ValueError(f"exit_time format invalide: {exit_time!r}") from e

CSV_COLUMNS = [
    "trade_id", "market_id", "token_id", "question", "side",
    "entry_price", "exit_price", "size_usd", "shares",
    "entry_time", "exit_time", "exit_reason",
    "pnl_gross", "fees_entry", "fees_exit", "fees_total", "pnl_net",
    "pnl_pct", "order_id",
]


@dataclass
class OpenTrade:
    """Trade en cours (position ouverte)."""
    trade_id: str
    market_id: str
    token_id: str
    question: str
    side: str
    entry_price: float
    size_usd: float
    shares: float
    entry_time: str
    order_id: str = ""


@dataclass
class ClosedTrade:
    """Trade termine avec tous les details."""
    trade_id: str
    market_id: str
    token_id: str
    question: str
    side: str
    entry_price: float
    exit_price: float
    size_usd: float
    shares: float
    entry_time: str
    exit_time: str
    exit_reason: str
    pnl_gross: float
    fees_entry: float
    fees_exit: float
    fees_total: float
    pnl_net: float
    pnl_pct: float
    order_id: str = ""


class TradeLogger:
    """Enregistre les trades du bot dans CSV + JSON avec donnees reelles."""

    def __init__(self, output_dir: str = ".", csv_file: str = "trades_real.csv",
                 json_file: str = "trades_real.json"):
        """Initialise le logger avec les chemins de sortie CSV et JSON."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / csv_file
        self.json_path = self.output_dir / json_file

        # Trades ouverts indexes par market_id
        self._open_trades: dict[str, OpenTrade] = {}

        # Historique des trades fermes
        self._closed_trades: list[ClosedTrade] = []

        # Compteur auto-increment
        self._trade_counter = 0

        # Charger l'historique existant
        self._load_existing()

    # ------------------------------------------------------------------
    #  PERSISTENCE
    # ------------------------------------------------------------------

    def _load_existing(self):
        """Charge les trades existants depuis le JSON."""
        if not self.json_path.exists():
            return
        try:
            with open(self.json_path) as f:
                data = json.load(f)
            for t in data.get("closed_trades", []):
                self._closed_trades.append(ClosedTrade(**t))
            for t in data.get("open_trades", []):
                self._open_trades[t["market_id"]] = OpenTrade(**t)
            self._trade_counter = data.get("trade_counter", len(self._closed_trades))
            logger.info(f"TradeLogger: charge {len(self._closed_trades)} trades fermes, "
                        f"{len(self._open_trades)} positions ouvertes")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"TradeLogger: impossible de charger {self.json_path}: {e}")

    def _save_json(self):
        """Sauvegarde l'etat complet en JSON."""
        data = {
            "trade_counter": self._trade_counter,
            "open_trades": [asdict(t) for t in self._open_trades.values()],
            "closed_trades": [asdict(t) for t in self._closed_trades],
            "last_updated": datetime.now().isoformat(),
        }
        tmp = self.json_path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(self.json_path)

    def _append_csv(self, trade: ClosedTrade):
        """Ajoute un trade au fichier CSV."""
        write_header = not self.csv_path.exists()
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerow(asdict(trade))

    # ------------------------------------------------------------------
    #  LOGGING DES ENTREES
    # ------------------------------------------------------------------

    def log_entry(
        self,
        market_id: str,
        token_id: str,
        question: str,
        side: str,
        entry_price: float,
        size_usd: float,
        shares: float,
        entry_time: Optional[str] = None,
        order_id: str = "",
    ) -> str:
        """
        Enregistre l'ouverture d'une position.

        Returns:
            trade_id unique pour cette position.
        """
        _validate_market_id(market_id)

        if not entry_time:
            entry_time = datetime.now().isoformat()

        self._trade_counter += 1
        trade_id = f"T-{self._trade_counter:06d}"

        open_trade = OpenTrade(
            trade_id=trade_id,
            market_id=market_id,
            token_id=token_id,
            question=question,
            side=side,
            entry_price=entry_price,
            size_usd=size_usd,
            shares=shares,
            entry_time=entry_time,
            order_id=order_id,
        )
        self._open_trades[market_id] = open_trade
        self._save_json()

        logger.info(
            f"[ENTRY] {trade_id} | {side} {question[:50]} | "
            f"${size_usd:.2f} @ {entry_price:.4f} | {shares:.2f} shares"
        )
        return trade_id

    # ------------------------------------------------------------------
    #  LOGGING DES SORTIES
    # ------------------------------------------------------------------

    def log_exit(
        self,
        market_id: str,
        exit_price: float,
        exit_reason: str,
        exit_time: Optional[str] = None,
    ) -> Optional[ClosedTrade]:
        """
        Enregistre la fermeture d'une position.

        Returns:
            ClosedTrade avec tous les details, ou None si la position n'existe pas.
        """
        open_trade = self._open_trades.pop(market_id, None)
        if open_trade is None:
            logger.warning(f"log_exit: position {market_id} introuvable")
            return None

        if not exit_time:
            exit_time = datetime.now().isoformat()
        _validate_exit_time(exit_time)

        # Calcul PnL brut
        if open_trade.side == "YES":
            pnl_gross = (exit_price - open_trade.entry_price) * open_trade.shares
        else:
            pnl_gross = (open_trade.entry_price - exit_price) * open_trade.shares

        # Frais Polymarket 2%
        fees_entry = open_trade.size_usd * POLYMARKET_FEE_PCT
        fees_exit = open_trade.shares * exit_price * POLYMARKET_FEE_PCT
        fees_total = fees_entry + fees_exit

        pnl_net = pnl_gross - fees_total
        pnl_pct = pnl_net / max(open_trade.size_usd, 0.01)

        closed = ClosedTrade(
            trade_id=open_trade.trade_id,
            market_id=open_trade.market_id,
            token_id=open_trade.token_id,
            question=open_trade.question,
            side=open_trade.side,
            entry_price=open_trade.entry_price,
            exit_price=exit_price,
            size_usd=open_trade.size_usd,
            shares=open_trade.shares,
            entry_time=open_trade.entry_time,
            exit_time=exit_time,
            exit_reason=exit_reason,
            pnl_gross=round(pnl_gross, 4),
            fees_entry=round(fees_entry, 4),
            fees_exit=round(fees_exit, 4),
            fees_total=round(fees_total, 4),
            pnl_net=round(pnl_net, 4),
            pnl_pct=round(pnl_pct, 4),
            order_id=open_trade.order_id,
        )

        self._closed_trades.append(closed)
        self._append_csv(closed)
        self._save_json()

        emoji = "+" if pnl_net >= 0 else ""
        logger.info(
            f"[EXIT] {closed.trade_id} | {closed.side} {closed.question[:50]} | "
            f"PnL brut: {emoji}${pnl_gross:.2f} | Frais: ${fees_total:.2f} | "
            f"PnL net: {emoji}${pnl_net:.2f} ({pnl_pct:+.1%}) | Raison: {exit_reason}"
        )
        return closed

    # ------------------------------------------------------------------
    #  STATISTIQUES
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Retourne les statistiques completes des trades fermes.

        Returns:
            dict avec total_trades, win_rate, total_pnl_net, sharpe_ratio,
            max_drawdown, profit_factor, avg_win, avg_loss, fees_total.
        """
        trades = self._closed_trades
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl_gross": 0.0,
                "total_pnl_net": 0.0,
                "total_fees": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }

        pnls_net = [t.pnl_net for t in trades]
        pnls_gross = [t.pnl_gross for t in trades]
        fees = [t.fees_total for t in trades]

        wins = [p for p in pnls_net if p > 0]
        losses = [p for p in pnls_net if p < 0]

        # Sharpe ratio (annualise, 365 jours de trading)
        pnl_arr = np.array(pnls_net)
        sharpe = 0.0
        if len(pnl_arr) > 1 and np.std(pnl_arr) > 0:
            sharpe = float(np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(365))

        # Max drawdown sur la courbe cumulative des PnL
        cumulative = np.cumsum(pnl_arr)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        return {
            "total_trades": len(trades),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "total_pnl_gross": round(sum(pnls_gross), 2),
            "total_pnl_net": round(sum(pnls_net), 2),
            "total_fees": round(sum(fees), 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(np.mean(wins), 2) if wins else 0.0,
            "avg_loss": round(np.mean(losses), 2) if losses else 0.0,
            "largest_win": round(max(pnls_net), 2) if pnls_net else 0.0,
            "largest_loss": round(min(pnls_net), 2) if pnls_net else 0.0,
        }

    # ------------------------------------------------------------------
    #  ACCESSEURS
    # ------------------------------------------------------------------

    @property
    def open_trades(self) -> dict[str, OpenTrade]:
        """Copie des trades actuellement ouverts, indexes par market_id."""
        return dict(self._open_trades)

    @property
    def closed_trades(self) -> list[ClosedTrade]:
        """Copie de l'historique des trades fermes."""
        return list(self._closed_trades)

    def get_trade_by_market(self, market_id: str) -> Optional[OpenTrade]:
        """Retourne le trade ouvert pour un market_id donne, ou None."""
        return self._open_trades.get(market_id)
