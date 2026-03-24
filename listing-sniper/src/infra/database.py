"""PostgreSQL async database layer — trades, signals, positions, PnL."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

from src.config import AppConfig

logger = logging.getLogger(__name__)

# SQL schema executed on first connect
_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id              TEXT PRIMARY KEY,
    token_symbol    TEXT NOT NULL,
    token_name      TEXT DEFAULT '',
    exchange        TEXT NOT NULL,
    listing_time    TIMESTAMPTZ,
    detection_time  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source          TEXT NOT NULL,
    confidence      REAL DEFAULT 0,
    raw_text        TEXT DEFAULT '',
    url             TEXT DEFAULT '',
    validated       BOOLEAN DEFAULT FALSE,
    contract_address TEXT,
    chain           TEXT DEFAULT 'solana'
);

CREATE TABLE IF NOT EXISTS trades (
    id              TEXT PRIMARY KEY,
    signal_id       TEXT REFERENCES signals(id),
    token_address   TEXT NOT NULL,
    token_symbol    TEXT NOT NULL,
    side            TEXT NOT NULL,
    amount_sol      REAL DEFAULT 0,
    amount_usd      REAL DEFAULT 0,
    amount_tokens   REAL DEFAULT 0,
    price_usd       REAL DEFAULT 0,
    slippage_bps    INTEGER DEFAULT 200,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    tx_signature    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at     TIMESTAMPTZ,
    fees_sol        REAL DEFAULT 0,
    fees_usd        REAL DEFAULT 0,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    id                  TEXT PRIMARY KEY,
    signal_id           TEXT REFERENCES signals(id),
    token_address       TEXT NOT NULL,
    token_symbol        TEXT NOT NULL,
    entry_price_usd     REAL DEFAULT 0,
    current_price_usd   REAL DEFAULT 0,
    amount_tokens       REAL DEFAULT 0,
    remaining_tokens    REAL DEFAULT 0,
    cost_basis_usd      REAL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'OPEN',
    opened_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ,
    realized_pnl_usd    REAL DEFAULT 0,
    risk_score          INTEGER DEFAULT 100,
    highest_price       REAL DEFAULT 0,
    trailing_stop_price  REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_pnl (
    date                TEXT PRIMARY KEY,
    trades_count        INTEGER DEFAULT 0,
    wins                INTEGER DEFAULT 0,
    losses              INTEGER DEFAULT 0,
    total_pnl_usd      REAL DEFAULT 0,
    total_pnl_pct       REAL DEFAULT 0,
    max_drawdown_pct    REAL DEFAULT 0,
    portfolio_value_usd REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_signals_detection ON signals(detection_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
"""


class Database:
    """Async PostgreSQL connection pool wrapper."""

    def __init__(self, config: AppConfig) -> None:
        self._dsn = config.database.url.replace("+asyncpg", "")
        self._pool_size = config.database.pool_size
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=2,
            max_size=self._pool_size,
        )
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA)
        logger.info("Database connected and schema applied")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")

    # ── Signals ──────────────────────────────────────────────

    async def insert_signal(self, s: dict[str, Any]) -> None:
        if not self._pool:
            return
        await self._pool.execute(
            """INSERT INTO signals (id, token_symbol, token_name, exchange,
               listing_time, detection_time, source, confidence, raw_text,
               url, validated, contract_address, chain)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
               ON CONFLICT (id) DO NOTHING""",
            s["id"], s["token_symbol"], s.get("token_name", ""),
            s["exchange"], s.get("listing_time"),
            s.get("detection_time", datetime.now(timezone.utc)),
            s["source"], s.get("confidence", 0), s.get("raw_text", ""),
            s.get("url", ""), s.get("validated", False),
            s.get("contract_address"), s.get("chain", "solana"),
        )

    async def get_recent_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._pool:
            return []
        rows = await self._pool.fetch(
            "SELECT * FROM signals ORDER BY detection_time DESC LIMIT $1", limit
        )
        return [dict(r) for r in rows]

    # ── Trades ───────────────────────────────────────────────

    async def insert_trade(self, t: dict[str, Any]) -> None:
        if not self._pool:
            return
        await self._pool.execute(
            """INSERT INTO trades (id, signal_id, token_address, token_symbol,
               side, amount_sol, amount_usd, amount_tokens, price_usd,
               slippage_bps, status, tx_signature, created_at, executed_at,
               fees_sol, fees_usd, error)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
               ON CONFLICT (id) DO NOTHING""",
            t["id"], t.get("signal_id"), t["token_address"], t["token_symbol"],
            t["side"], t.get("amount_sol", 0), t.get("amount_usd", 0),
            t.get("amount_tokens", 0), t.get("price_usd", 0),
            t.get("slippage_bps", 200), t["status"], t.get("tx_signature"),
            t.get("created_at", datetime.now(timezone.utc)),
            t.get("executed_at"), t.get("fees_sol", 0),
            t.get("fees_usd", 0), t.get("error"),
        )

    async def update_trade_status(self, trade_id: str, status: str, **kwargs: Any) -> None:
        if not self._pool:
            return
        sets = ["status = $2"]
        vals: list[Any] = [trade_id, status]
        idx = 3
        for k, v in kwargs.items():
            sets.append(f"{k} = ${idx}")
            vals.append(v)
            idx += 1
        await self._pool.execute(
            f"UPDATE trades SET {', '.join(sets)} WHERE id = $1", *vals
        )

    # ── Positions ────────────────────────────────────────────

    async def insert_position(self, p: dict[str, Any]) -> None:
        if not self._pool:
            return
        await self._pool.execute(
            """INSERT INTO positions (id, signal_id, token_address, token_symbol,
               entry_price_usd, current_price_usd, amount_tokens,
               remaining_tokens, cost_basis_usd, status, opened_at,
               risk_score, highest_price)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
               ON CONFLICT (id) DO NOTHING""",
            p["id"], p.get("signal_id"), p["token_address"], p["token_symbol"],
            p.get("entry_price_usd", 0), p.get("current_price_usd", 0),
            p.get("amount_tokens", 0), p.get("remaining_tokens", 0),
            p.get("cost_basis_usd", 0), p.get("status", "OPEN"),
            p.get("opened_at", datetime.now(timezone.utc)),
            p.get("risk_score", 100), p.get("highest_price", 0),
        )

    async def get_open_positions(self) -> list[dict[str, Any]]:
        if not self._pool:
            return []
        rows = await self._pool.fetch(
            "SELECT * FROM positions WHERE status IN ('OPEN','PARTIALLY_CLOSED') ORDER BY opened_at"
        )
        return [dict(r) for r in rows]

    async def update_position(self, pos_id: str, **kwargs: Any) -> None:
        if not self._pool:
            return
        if not kwargs:
            return
        sets = []
        vals: list[Any] = [pos_id]
        idx = 2
        for k, v in kwargs.items():
            sets.append(f"{k} = ${idx}")
            vals.append(v)
            idx += 1
        await self._pool.execute(
            f"UPDATE positions SET {', '.join(sets)} WHERE id = $1", *vals
        )

    # ── Daily PnL ────────────────────────────────────────────

    async def upsert_daily_pnl(self, d: dict[str, Any]) -> None:
        if not self._pool:
            return
        await self._pool.execute(
            """INSERT INTO daily_pnl (date, trades_count, wins, losses,
               total_pnl_usd, total_pnl_pct, max_drawdown_pct, portfolio_value_usd)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
               ON CONFLICT (date) DO UPDATE SET
               trades_count=$2, wins=$3, losses=$4, total_pnl_usd=$5,
               total_pnl_pct=$6, max_drawdown_pct=$7, portfolio_value_usd=$8""",
            d["date"], d.get("trades_count", 0), d.get("wins", 0),
            d.get("losses", 0), d.get("total_pnl_usd", 0),
            d.get("total_pnl_pct", 0), d.get("max_drawdown_pct", 0),
            d.get("portfolio_value_usd", 0),
        )

    async def get_daily_pnl(self, days: int = 30) -> list[dict[str, Any]]:
        if not self._pool:
            return []
        rows = await self._pool.fetch(
            "SELECT * FROM daily_pnl ORDER BY date DESC LIMIT $1", days
        )
        return [dict(r) for r in rows]
