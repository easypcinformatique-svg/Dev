"""Prometheus metrics for monitoring and Grafana dashboards."""

from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# ── Counters ─────────────────────────────────────────────────
signals_detected = Counter(
    "sniper_signals_detected_total",
    "Total listing signals detected",
    ["exchange", "source"],
)
signals_validated = Counter(
    "sniper_signals_validated_total",
    "Total validated signals",
    ["exchange"],
)
trades_executed = Counter(
    "sniper_trades_executed_total",
    "Total trades executed",
    ["side", "status"],
)
trades_failed = Counter(
    "sniper_trades_failed_total",
    "Total failed trades",
    ["reason"],
)
circuit_breaker_trips = Counter(
    "sniper_circuit_breaker_trips_total",
    "Circuit breaker activations",
    ["reason"],
)

# ── Gauges ───────────────────────────────────────────────────
portfolio_value = Gauge(
    "sniper_portfolio_value_usd",
    "Current portfolio value in USD",
)
open_positions_count = Gauge(
    "sniper_open_positions",
    "Number of open positions",
)
unrealized_pnl = Gauge(
    "sniper_unrealized_pnl_usd",
    "Total unrealized PnL in USD",
)
daily_pnl_gauge = Gauge(
    "sniper_daily_pnl_usd",
    "Today's realized PnL in USD",
)
sol_balance = Gauge(
    "sniper_sol_balance",
    "SOL balance of the trading wallet",
)
daily_trades_remaining = Gauge(
    "sniper_daily_trades_remaining",
    "Remaining trades allowed today",
)

# ── Histograms ───────────────────────────────────────────────
signal_to_trade_latency = Histogram(
    "sniper_signal_to_trade_seconds",
    "Latency from signal detection to trade execution",
    buckets=[0.5, 1, 2, 3, 5, 10, 30, 60, 120],
)
trade_slippage = Histogram(
    "sniper_trade_slippage_bps",
    "Actual slippage in basis points",
    buckets=[10, 25, 50, 100, 200, 300, 500, 1000],
)
trade_pnl_pct = Histogram(
    "sniper_trade_pnl_pct",
    "Trade PnL percentage",
    buckets=[-50, -20, -10, -5, 0, 5, 10, 25, 50, 100, 200],
)


def start_metrics_server(port: int = 9090) -> None:
    """Start Prometheus HTTP exporter."""
    try:
        start_http_server(port)
        logger.info("Prometheus metrics server started on :%d", port)
    except OSError as e:
        logger.warning("Metrics server failed to start: %s", e)
