"""
Listing Sniper — Main Orchestrator

Wires all modules together and runs the full sniping pipeline:
  Signal Detection → Token Analysis → Risk Assessment → Execution → Position Management
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timezone

from src.config import AppConfig
from src.models import RiskTier, Signal, TradeStatus
from src.infra.database import Database
from src.infra.redis_cache import RedisCache
from src.infra.telegram_alerts import TelegramAlerter
from src.infra import metrics

from src.signals.binance_listener import (
    BinanceListener,
    BybitListener,
    KuCoinListener,
    OKXListener,
)
from src.signals.twitter_listener import TwitterListener
from src.signals.websocket_listener import ExchangeWebSocketListener
from src.signals.onchain_listener import OnchainListener
from src.signals.signal_validator import SignalValidator

from src.analysis.token_discovery import TokenDiscovery
from src.analysis.risk_assessment import RiskAssessor
from src.analysis.position_sizer import PositionSizer

from src.execution.jupiter_executor import JupiterExecutor
from src.execution.mev_protection import MevProtection

from src.positions.exit_strategy import ExitStrategy
from src.positions.pnl_tracker import PnLTracker
from src.positions.position_manager import PositionManager

from src.risk.risk_manager import RiskManager
from src.risk.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ListingSniper:
    """Main application — coordinates all subsystems."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._running = False

        # Infrastructure
        self._db = Database(config)
        self._redis = RedisCache(config)
        self._alerter = TelegramAlerter(config)

        # Signals
        self._binance = BinanceListener(config)
        self._bybit = BybitListener(config)
        self._okx = OKXListener(config)
        self._kucoin = KuCoinListener(config)
        self._twitter = TwitterListener(config)
        self._ws_listener = ExchangeWebSocketListener(config)
        self._onchain = OnchainListener(config)
        self._validator = SignalValidator(self._redis)

        # Analysis
        self._discovery = TokenDiscovery(config, self._redis)
        self._risk_assessor = RiskAssessor(config)
        self._sizer = PositionSizer(config)

        # Execution
        self._executor = JupiterExecutor(config)
        self._mev = MevProtection(config)

        # Positions
        self._exit_strategy = ExitStrategy(config)
        self._pnl = PnLTracker(self._db, self._redis)
        self._position_mgr = PositionManager(
            config, self._executor, self._exit_strategy,
            self._pnl, self._db, self._redis, self._alerter,
        )

        # Risk
        self._risk_mgr = RiskManager(self._pnl)
        self._circuit_breaker = CircuitBreaker(config, self._alerter)

        # State
        self._portfolio_value_usd: float = float(
            config.get("portfolio", "initial_capital_usd", default=500)
        )
        self._sol_price_usd: float = 150.0  # Updated at runtime
        self._start_time = datetime.now(timezone.utc)
        self._recent_signals: list[dict] = []
        self._recent_trades: list[dict] = []
        self._errors: list[dict] = []

    async def start(self) -> None:
        """Initialize all subsystems."""
        logger.info("=" * 60)
        logger.info("LISTING SNIPER — Starting up")
        logger.info("Mode: %s", self._config.mode)
        logger.info("Dry run: %s", self._config.dry_run)
        logger.info("=" * 60)

        # Start metrics server
        prom_port = self._config.get("monitoring", "prometheus", "port", default=9090)
        if self._config.get("monitoring", "prometheus", "enabled", default=True):
            metrics.start_metrics_server(prom_port)

        # Connect infrastructure
        try:
            await self._db.connect()
        except Exception:
            logger.warning("Database connection failed — running without persistence")

        try:
            await self._redis.connect()
        except Exception:
            logger.warning("Redis connection failed — running without cache")

        await self._alerter.start()

        # Start modules
        await self._binance.start()
        await self._bybit.start()
        await self._okx.start()
        await self._kucoin.start()
        await self._twitter.start()
        await self._ws_listener.start()
        await self._onchain.start()
        await self._discovery.start()
        await self._risk_assessor.start()
        await self._executor.start()
        await self._mev.start()
        await self._circuit_breaker.start()

        self._running = True
        logger.info("All subsystems started")

        # Send startup alert
        await self._alerter._send(
            f"🚀 <b>Listing Sniper Started</b>\n"
            f"Mode: {self._config.mode}\n"
            f"Portfolio: ${self._portfolio_value_usd:.2f}"
        )

    async def stop(self) -> None:
        """Gracefully shut down all subsystems."""
        logger.info("Shutting down...")
        self._running = False

        await self._position_mgr.stop_monitoring()
        await self._circuit_breaker.stop()
        await self._binance.stop()
        await self._bybit.stop()
        await self._okx.stop()
        await self._kucoin.stop()
        await self._twitter.stop()
        await self._ws_listener.stop()
        await self._onchain.stop()
        await self._discovery.stop()
        await self._risk_assessor.stop()
        await self._executor.stop()
        await self._mev.stop()
        await self._alerter.stop()
        await self._redis.close()
        await self._db.close()

        logger.info("Shutdown complete")

    async def run(self) -> None:
        """Main event loop — run all listeners and process signals."""
        await self.start()

        try:
            # Launch concurrent tasks
            tasks = [
                asyncio.create_task(self._run_listeners(), name="listeners"),
                asyncio.create_task(
                    self._position_mgr.monitor_positions(), name="position_monitor"
                ),
                asyncio.create_task(
                    self._circuit_breaker.monitor(), name="circuit_breaker"
                ),
                asyncio.create_task(self._update_sol_price(), name="sol_price"),
                asyncio.create_task(self._update_metrics(), name="metrics"),
                asyncio.create_task(self._save_state_loop(), name="state_saver"),
            ]

            # Wait for any task to complete (or fail)
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_EXCEPTION
            )
            for task in done:
                if task.exception():
                    logger.error(
                        "Task %s failed: %s", task.get_name(), task.exception()
                    )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def _run_listeners(self) -> None:
        """Run all signal listeners and process incoming signals."""
        signal_queue: asyncio.Queue[Signal] = asyncio.Queue()

        async def _feed_binance() -> None:
            async for sig in self._binance.listen():
                await signal_queue.put(sig)

        async def _feed_bybit() -> None:
            async for sig in self._bybit.listen():
                await signal_queue.put(sig)

        async def _feed_okx() -> None:
            async for sig in self._okx.listen():
                await signal_queue.put(sig)

        async def _feed_kucoin() -> None:
            async for sig in self._kucoin.listen():
                await signal_queue.put(sig)

        async def _feed_twitter() -> None:
            async for sig in self._twitter.listen():
                await signal_queue.put(sig)

        async def _feed_ws() -> None:
            async for sig in self._ws_listener.listen():
                await signal_queue.put(sig)

        async def _feed_onchain() -> None:
            async for sig in self._onchain.listen():
                await signal_queue.put(sig)

        # Start all feeders
        feeders = []
        if self._config.get("signals", "binance", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_binance()))
        if self._config.get("signals", "bybit", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_bybit()))
        if self._config.get("signals", "okx", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_okx()))
        if self._config.get("signals", "kucoin", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_kucoin()))
        if self._config.get("signals", "twitter", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_twitter()))
        if self._config.get("signals", "websocket", "enabled", default=True):
            feeders.append(asyncio.create_task(_feed_ws()))
        if self._config.get("signals", "onchain", "enabled", default=False):
            feeders.append(asyncio.create_task(_feed_onchain()))

        logger.info("Signal listeners active: %d", len(feeders))

        # Process signals from queue
        while self._running:
            try:
                sig = await asyncio.wait_for(signal_queue.get(), timeout=5.0)
                await self._process_signal(sig)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Signal processing error")

        for f in feeders:
            f.cancel()

    async def _process_signal(self, raw_signal: Signal) -> None:
        """Full signal processing pipeline."""
        start = time.monotonic()
        metrics.signals_detected.labels(
            exchange=raw_signal.exchange.value, source=raw_signal.source.value
        ).inc()

        # Step 1: Validate
        signal = await self._validator.validate(raw_signal)
        if not signal:
            return

        metrics.signals_validated.labels(exchange=signal.exchange.value).inc()
        logger.info(
            "Signal validated: %s on %s (%.2f confidence)",
            signal.token_symbol,
            signal.exchange.value,
            signal.confidence,
        )

        # Track for dashboard
        self._recent_signals.append({
            "token_symbol": signal.token_symbol,
            "token_name": signal.token_name,
            "exchange": signal.exchange.value,
            "source": signal.source.value,
            "confidence": signal.confidence,
            "detection_time": signal.detection_time.isoformat() if signal.detection_time else "",
            "raw_text": signal.raw_text[:200],
        })
        if len(self._recent_signals) > 100:
            self._recent_signals = self._recent_signals[-50:]

        # Alert
        await self._alerter.signal_detected(signal)

        # Step 2: Check circuit breakers
        if self._circuit_breaker.is_tripped:
            logger.warning("Circuit breaker tripped — skipping %s", signal.token_symbol)
            return

        # Step 3: Discover token
        token = await self._discovery.discover(signal)
        if not token:
            logger.warning("Token discovery failed for %s", signal.token_symbol)
            return

        # Step 4: Risk assessment
        risk = await self._risk_assessor.assess(token)

        # Step 5: Position sizing
        size = self._sizer.calculate(
            self._portfolio_value_usd,
            self._sol_price_usd,
            risk,
        )

        if size.amount_usd <= 0:
            logger.info(
                "Skipping %s: %s", signal.token_symbol, size.reason
            )
            return

        # Step 6: Risk manager check
        check = await self._risk_mgr.check_can_trade(
            self._portfolio_value_usd,
            size.amount_usd,
            self._position_mgr.total_exposure_usd,
        )
        if not check.allowed:
            logger.warning(
                "Risk check failed for %s: %s", signal.token_symbol, check.reason
            )
            await self._alerter.risk_alert(
                f"Trade blocked for {signal.token_symbol}: {check.reason}"
            )
            return

        # Step 7: Persist signal
        try:
            await self._db.insert_signal({
                "id": signal.id,
                "token_symbol": signal.token_symbol,
                "token_name": signal.token_name,
                "exchange": signal.exchange.value,
                "listing_time": signal.listing_time,
                "detection_time": signal.detection_time,
                "source": signal.source.value,
                "confidence": signal.confidence,
                "raw_text": signal.raw_text,
                "url": signal.url,
                "validated": True,
                "contract_address": token.contract_address,
                "chain": signal.chain,
            })
        except Exception:
            logger.debug("Signal persistence failed")

        # Step 8: Execute trade
        elapsed = time.monotonic() - start
        logger.info(
            "Executing trade for %s: $%.2f (%.4f SOL) — pipeline took %.2fs",
            signal.token_symbol,
            size.amount_usd,
            size.amount_sol,
            elapsed,
        )

        position = await self._position_mgr.open_position(
            signal, token, risk, size.amount_sol, size.amount_usd, self._sol_price_usd
        )

        if position:
            metrics.signal_to_trade_latency.observe(time.monotonic() - start)
            self._risk_mgr.record_trade(0)  # PnL recorded on close
            logger.info(
                "Position opened for %s — total pipeline: %.2fs",
                signal.token_symbol,
                time.monotonic() - start,
            )

    def get_dashboard_data(self) -> dict:
        """Return current state for the web dashboard."""
        now = datetime.now(timezone.utc)
        uptime = now - self._start_time
        uptime_str = f"{int(uptime.total_seconds() // 3600)}h{int((uptime.total_seconds() % 3600) // 60)}m"

        open_pos = []
        for p in self._position_mgr.open_positions:
            open_pos.append({
                "token_symbol": p.token_symbol,
                "token_address": p.token_address,
                "entry_price_usd": p.entry_price_usd,
                "current_price_usd": p.current_price_usd,
                "remaining_tokens": p.remaining_tokens,
                "cost_basis_usd": p.cost_basis_usd,
                "realized_pnl_usd": p.realized_pnl_usd,
                "unrealized_pnl_usd": p.unrealized_pnl,
                "hold_hours": p.hold_duration_hours,
                "risk_score": p.risk_score,
                "status": p.status.value,
            })

        perf = self._pnl.get_performance_stats()
        cb_status = {
            "is_tripped": self._circuit_breaker.is_tripped,
            "rpc_error_rate": self._circuit_breaker.get_rpc_error_rate(),
        }
        risk_status = {
            "trades_remaining": self._risk_mgr.trades_remaining_today,
            "is_halted": self._risk_mgr.is_halted,
            "exposure_pct": (
                self._position_mgr.total_exposure_usd / self._portfolio_value_usd
                if self._portfolio_value_usd > 0 else 0
            ),
            "daily_loss_pct": 0,
        }

        total_unrealized = sum(p.unrealized_pnl for p in self._position_mgr.open_positions)

        return {
            "status": "halted" if self._risk_mgr.is_halted else ("running" if self._running else "stopped"),
            "mode": self._config.mode,
            "portfolio_value_usd": self._portfolio_value_usd,
            "sol_balance": 0,  # Updated by circuit breaker
            "daily_pnl_usd": 0,
            "total_pnl_usd": total_unrealized,
            "sol_price_usd": self._sol_price_usd,
            "open_positions": open_pos,
            "recent_signals": self._recent_signals[-50:],
            "recent_trades": self._recent_trades[-50:],
            "performance": {
                "total_trades": perf.total_trades,
                "wins": perf.wins,
                "losses": perf.losses,
                "win_rate": perf.win_rate,
                "profit_factor": perf.profit_factor,
                "sharpe_ratio": perf.sharpe_ratio,
                "sortino_ratio": perf.sortino_ratio,
                "max_drawdown_pct": perf.max_drawdown_pct,
            },
            "risk_status": risk_status,
            "circuit_breaker": cb_status,
            "errors": self._errors[-20:],
            "uptime": uptime_str,
            "last_update": now.isoformat(),
        }

    async def _save_state_loop(self) -> None:
        """Periodically save state to JSON for the dashboard."""
        from src.web_dashboard import save_state
        while self._running:
            try:
                save_state(self.get_dashboard_data())
            except Exception:
                pass
            await asyncio.sleep(10)

    async def _update_sol_price(self) -> None:
        """Periodically update SOL/USD price."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    async with session.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": "solana", "vs_currencies": "usd"},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            price = data.get("solana", {}).get("usd", 0)
                            if price > 0:
                                self._sol_price_usd = price
                                await self._redis.set_price("SOL", price)
                except Exception:
                    pass
                await asyncio.sleep(30)

    async def _update_metrics(self) -> None:
        """Periodically update Prometheus metrics."""
        while self._running:
            try:
                metrics.portfolio_value.set(self._portfolio_value_usd)
                metrics.open_positions_count.set(
                    len(self._position_mgr.open_positions)
                )
                exposure = self._position_mgr.total_exposure_usd
                metrics.unrealized_pnl.set(
                    sum(
                        p.unrealized_pnl
                        for p in self._position_mgr.open_positions
                    )
                )
                metrics.daily_trades_remaining.set(
                    self._risk_mgr.trades_remaining_today
                )
            except Exception:
                pass
            await asyncio.sleep(5)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    import json as json_mod

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "module": record.module,
                "msg": record.getMessage(),
            }
            if record.exc_info and record.exc_info[1]:
                log["error"] = str(record.exc_info[1])
            return json_mod.dumps(log)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))


def main() -> None:
    """Entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Listing Sniper")
    parser.add_argument("--dashboard", action="store_true", help="Launch with web dashboard")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5050)))
    args = parser.parse_args()

    config = AppConfig.load()
    setup_logging(config.log_level)

    sniper = ListingSniper(config)

    if args.dashboard:
        # Launch Flask dashboard in a separate thread
        import threading
        from src.web_dashboard import create_dashboard_app, _start_keep_alive

        flask_app = create_dashboard_app(sniper=sniper)

        def _run_flask() -> None:
            flask_app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)

        flask_thread = threading.Thread(target=_run_flask, daemon=True)
        flask_thread.start()

        # Start keep-alive to prevent free tier sleep
        app_url = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{args.port}")
        _start_keep_alive(app_url, interval=600)

        logger.info("Dashboard started on port %d", args.port)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _signal_handler() -> None:
        logger.info("Received shutdown signal")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        loop.run_until_complete(sniper.run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Exited cleanly")


if __name__ == "__main__":
    main()
