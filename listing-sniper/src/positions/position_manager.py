"""Position manager — orchestrates entry, monitoring, and exit of positions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from src.config import AppConfig
from src.execution.jupiter_executor import JupiterExecutor
from src.infra.database import Database
from src.infra.redis_cache import RedisCache
from src.infra.telegram_alerts import TelegramAlerter
from src.infra import metrics
from src.models import (
    Position,
    Signal,
    TokenInfo,
    TokenRiskAssessment,
    TradeOrder,
    TradeSide,
    TradeStatus,
)
from src.positions.exit_strategy import ExitStrategy
from src.positions.pnl_tracker import PnLTracker

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages the lifecycle of trading positions."""

    def __init__(
        self,
        config: AppConfig,
        executor: JupiterExecutor,
        exit_strategy: ExitStrategy,
        pnl_tracker: PnLTracker,
        db: Database,
        redis: RedisCache,
        alerter: TelegramAlerter,
    ) -> None:
        self._config = config
        self._executor = executor
        self._exit_strategy = exit_strategy
        self._pnl = pnl_tracker
        self._db = db
        self._redis = redis
        self._alerter = alerter
        self._positions: dict[str, Position] = {}  # id -> Position
        self._monitoring = False

    @property
    def open_positions(self) -> list[Position]:
        return [
            p for p in self._positions.values()
            if p.status in (TradeStatus.OPEN, TradeStatus.PARTIALLY_CLOSED)
        ]

    @property
    def total_exposure_usd(self) -> float:
        return sum(
            p.remaining_tokens * p.current_price_usd for p in self.open_positions
        )

    async def open_position(
        self,
        signal: Signal,
        token: TokenInfo,
        risk: TokenRiskAssessment,
        amount_sol: float,
        amount_usd: float,
        sol_price: float,
    ) -> Optional[Position]:
        """Open a new position by executing a buy order."""
        # Create buy order
        price_usd = 0.0
        if token.pools:
            best_pool = max(token.pools, key=lambda p: p.liquidity_usd)
            price_usd = best_pool.price_usd

        order = TradeOrder(
            signal_id=signal.id,
            token_address=token.contract_address,
            token_symbol=signal.token_symbol,
            side=TradeSide.BUY,
            amount_sol=amount_sol,
            amount_usd=amount_usd,
            price_usd=price_usd,
            slippage_bps=self._config.get("execution", "max_slippage_bps", default=200),
        )

        # Execute
        executed = await self._executor.execute_swap(order)

        # Log trade
        await self._db.insert_trade({
            "id": executed.id,
            "signal_id": signal.id,
            "token_address": token.contract_address,
            "token_symbol": signal.token_symbol,
            "side": executed.side.value,
            "amount_sol": executed.amount_sol,
            "amount_usd": executed.amount_usd,
            "amount_tokens": executed.amount_tokens,
            "price_usd": executed.price_usd,
            "slippage_bps": executed.slippage_bps,
            "status": executed.status.value,
            "tx_signature": executed.tx_signature,
            "created_at": executed.created_at,
            "executed_at": datetime.now(timezone.utc),
            "fees_sol": executed.fees_sol,
            "fees_usd": executed.fees_usd,
            "error": executed.error,
        })

        if executed.status != TradeStatus.OPEN:
            logger.error(
                "Buy order failed for %s: %s",
                signal.token_symbol,
                executed.error,
            )
            metrics.trades_failed.labels(reason=executed.error or "unknown").inc()
            await self._alerter.error_alert(
                "PositionManager",
                f"Buy failed for {signal.token_symbol}: {executed.error}",
            )
            return None

        # Create position
        entry_price = price_usd if price_usd > 0 else (
            amount_usd / executed.amount_tokens if executed.amount_tokens > 0 else 0
        )
        position = Position(
            signal_id=signal.id,
            token_address=token.contract_address,
            token_symbol=signal.token_symbol,
            entry_price_usd=entry_price,
            current_price_usd=entry_price,
            amount_tokens=executed.amount_tokens,
            remaining_tokens=executed.amount_tokens,
            cost_basis_usd=amount_usd,
            status=TradeStatus.OPEN,
            risk_score=risk.risk_score,
            highest_price=entry_price,
        )

        self._positions[position.id] = position
        await self._db.insert_position({
            "id": position.id,
            "signal_id": signal.id,
            "token_address": token.contract_address,
            "token_symbol": signal.token_symbol,
            "entry_price_usd": entry_price,
            "current_price_usd": entry_price,
            "amount_tokens": executed.amount_tokens,
            "remaining_tokens": executed.amount_tokens,
            "cost_basis_usd": amount_usd,
            "status": "OPEN",
            "risk_score": risk.risk_score,
            "highest_price": entry_price,
        })

        metrics.trades_executed.labels(side="BUY", status="success").inc()
        metrics.open_positions_count.set(len(self.open_positions))
        await self._alerter.trade_executed(executed)

        logger.info(
            "Position opened: %s, entry=$%.8f, tokens=%.2f, cost=$%.2f",
            signal.token_symbol,
            entry_price,
            executed.amount_tokens,
            amount_usd,
        )
        return position

    async def monitor_positions(self) -> None:
        """Continuously monitor open positions and execute exits."""
        self._monitoring = True
        logger.info("Position monitoring started")

        while self._monitoring:
            try:
                for pos in list(self.open_positions):
                    await self._check_position(pos)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Position monitoring error")
            await asyncio.sleep(2)  # Check every 2 seconds

    async def stop_monitoring(self) -> None:
        self._monitoring = False

    async def _check_position(self, position: Position) -> None:
        """Check a single position for exit conditions."""
        # Update current price from cache
        price = await self._redis.get_price(position.token_address)
        if price and price > 0:
            position.current_price_usd = price
            if price > position.highest_price:
                position.highest_price = price

            # Update unrealized PnL
            position.unrealized_pnl_usd = position.unrealized_pnl
            if position.entry_price_usd > 0:
                position.unrealized_pnl_pct = (
                    (price - position.entry_price_usd) / position.entry_price_usd
                )

        # Evaluate exit
        decision = self._exit_strategy.evaluate(position)

        if decision.should_exit:
            sell_order = self._exit_strategy.create_sell_order(position, decision)
            executed = await self._executor.execute_swap(sell_order)

            if executed.status == TradeStatus.OPEN:
                # Calculate realized PnL for this tranche
                tokens_sold = position.remaining_tokens * decision.sell_fraction
                sell_value = tokens_sold * position.current_price_usd
                cost = tokens_sold * position.entry_price_usd
                tranche_pnl = sell_value - cost

                position.realized_pnl_usd += tranche_pnl
                position.remaining_tokens -= tokens_sold

                if decision.is_full_exit or position.remaining_tokens <= 0:
                    position.status = TradeStatus.CLOSED
                    position.closed_at = datetime.now(timezone.utc)
                    total_pnl_pct = (
                        position.total_pnl_usd / position.cost_basis_usd
                        if position.cost_basis_usd > 0
                        else 0
                    )
                    await self._pnl.record_trade_result(
                        position, position.total_pnl_usd, total_pnl_pct
                    )
                    await self._alerter.position_closed(position)
                    metrics.trade_pnl_pct.observe(total_pnl_pct * 100)
                else:
                    position.status = TradeStatus.PARTIALLY_CLOSED

                # Update DB
                await self._db.update_position(
                    position.id,
                    status=position.status.value,
                    remaining_tokens=position.remaining_tokens,
                    realized_pnl_usd=position.realized_pnl_usd,
                    current_price_usd=position.current_price_usd,
                    highest_price=position.highest_price,
                    closed_at=position.closed_at,
                )

                # Log trade
                await self._db.insert_trade({
                    "id": executed.id,
                    "signal_id": position.signal_id,
                    "token_address": position.token_address,
                    "token_symbol": position.token_symbol,
                    "side": "SELL",
                    "amount_tokens": tokens_sold,
                    "amount_usd": sell_value,
                    "price_usd": position.current_price_usd,
                    "status": "OPEN",
                    "tx_signature": executed.tx_signature,
                    "executed_at": datetime.now(timezone.utc),
                })

                metrics.trades_executed.labels(side="SELL", status="success").inc()
                metrics.open_positions_count.set(len(self.open_positions))

                logger.info(
                    "Exit %s: %s, sold=%.2f tokens, pnl=$%.2f, reason=%s",
                    position.token_symbol,
                    "FULL" if decision.is_full_exit else "PARTIAL",
                    tokens_sold,
                    tranche_pnl,
                    decision.reason,
                )
