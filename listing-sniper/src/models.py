"""Core domain models used throughout the listing sniper system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Exchange(str, Enum):
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"
    KUCOIN = "KUCOIN"


class SignalSource(str, Enum):
    API = "API"
    TWITTER = "TWITTER"
    WEBSOCKET = "WEBSOCKET"
    TELEGRAM = "TELEGRAM"
    ONCHAIN = "ONCHAIN"


class RiskTier(str, Enum):
    SAFE = "SAFE"          # 0-30
    MEDIUM = "MEDIUM"      # 31-60
    RISKY = "RISKY"        # 61-80
    DANGER = "DANGER"      # 81-100


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Signal:
    """Represents a detected listing signal."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    token_symbol: str = ""
    token_name: str = ""
    exchange: Exchange = Exchange.BINANCE
    listing_time: Optional[datetime] = None
    detection_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: SignalSource = SignalSource.API
    confidence: float = 0.0
    raw_text: str = ""
    url: str = ""
    validated: bool = False
    contract_address: Optional[str] = None
    chain: str = "solana"


@dataclass
class TokenInfo:
    """Discovered token information."""

    symbol: str
    name: str
    contract_address: str
    chain: str = "solana"
    decimals: int = 9
    coingecko_id: Optional[str] = None
    dexscreener_url: Optional[str] = None
    pools: list[PoolInfo] = field(default_factory=list)


@dataclass
class PoolInfo:
    """DEX pool information."""

    pool_address: str
    dex: str  # jupiter, raydium, orca
    base_token: str
    quote_token: str
    liquidity_usd: float = 0.0
    volume_24h_usd: float = 0.0
    price_usd: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class TokenRiskAssessment:
    """Risk assessment for a token."""

    token_address: str
    liquidity_usd: float = 0.0
    pool_age_hours: float = 0.0
    holder_count: int = 0
    top10_concentration: float = 1.0
    is_renounced: bool = False
    is_honeypot: bool = False
    has_mint_authority: bool = True
    rug_pull_score: float = 100.0
    risk_score: int = 100
    risk_tier: RiskTier = RiskTier.DANGER
    assessed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def calculate_risk_score(self) -> int:
        """Calculate composite risk score 0-100 (lower = safer)."""
        score = 0.0

        # Liquidity (0-25 points)
        if self.liquidity_usd < 1000:
            score += 25
        elif self.liquidity_usd < 5000:
            score += 20
        elif self.liquidity_usd < 20000:
            score += 10
        elif self.liquidity_usd < 100000:
            score += 5

        # Pool age (0-15 points)
        if self.pool_age_hours < 0.5:
            score += 15
        elif self.pool_age_hours < 2:
            score += 10
        elif self.pool_age_hours < 24:
            score += 5

        # Holder concentration (0-20 points)
        if self.top10_concentration > 0.90:
            score += 20
        elif self.top10_concentration > 0.70:
            score += 15
        elif self.top10_concentration > 0.50:
            score += 10
        elif self.top10_concentration > 0.30:
            score += 5

        # Holder count (0-10 points)
        if self.holder_count < 50:
            score += 10
        elif self.holder_count < 200:
            score += 5

        # Honeypot (0 or 20)
        if self.is_honeypot:
            score += 20

        # Mint authority (0 or 10)
        if self.has_mint_authority:
            score += 10

        # Not renounced (0 or 5)
        if not self.is_renounced:
            score += 5

        self.risk_score = min(100, int(score))

        if self.risk_score <= 30:
            self.risk_tier = RiskTier.SAFE
        elif self.risk_score <= 60:
            self.risk_tier = RiskTier.MEDIUM
        elif self.risk_score <= 80:
            self.risk_tier = RiskTier.RISKY
        else:
            self.risk_tier = RiskTier.DANGER

        return self.risk_score


@dataclass
class TradeOrder:
    """A trade order (buy or sell)."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    signal_id: str = ""
    token_address: str = ""
    token_symbol: str = ""
    side: TradeSide = TradeSide.BUY
    amount_sol: float = 0.0
    amount_usd: float = 0.0
    amount_tokens: float = 0.0
    price_usd: float = 0.0
    slippage_bps: int = 200
    status: TradeStatus = TradeStatus.PENDING
    tx_signature: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    executed_at: Optional[datetime] = None
    fees_sol: float = 0.0
    fees_usd: float = 0.0
    error: Optional[str] = None


@dataclass
class Position:
    """An open trading position."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    signal_id: str = ""
    token_address: str = ""
    token_symbol: str = ""
    entry_price_usd: float = 0.0
    current_price_usd: float = 0.0
    amount_tokens: float = 0.0
    remaining_tokens: float = 0.0
    cost_basis_usd: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    opened_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    closed_at: Optional[datetime] = None
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    exit_orders: list[TradeOrder] = field(default_factory=list)
    risk_score: int = 100
    take_profit_levels_hit: list[int] = field(default_factory=list)
    stop_loss_triggered: bool = False
    trailing_stop_activated: bool = False
    trailing_stop_price: float = 0.0
    highest_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if self.entry_price_usd == 0:
            return 0.0
        value = self.remaining_tokens * self.current_price_usd
        cost = self.remaining_tokens * self.entry_price_usd
        return value - cost

    @property
    def total_pnl_usd(self) -> float:
        return self.realized_pnl_usd + self.unrealized_pnl

    @property
    def hold_duration_hours(self) -> float:
        now = self.closed_at or datetime.now(timezone.utc)
        return (now - self.opened_at).total_seconds() / 3600


@dataclass
class DailyPnL:
    """Daily performance metrics."""

    date: str  # YYYY-MM-DD
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    portfolio_value_usd: float = 0.0
