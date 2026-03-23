"""Exit strategy — multi-level take profit, stop-loss, trailing stop, and time-based exits."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.config import AppConfig
from src.models import Position, TradeSide, TradeOrder, TradeStatus

logger = logging.getLogger(__name__)


@dataclass
class ExitDecision:
    """An exit decision with order details."""

    should_exit: bool
    reason: str
    sell_fraction: float  # 0.0 to 1.0
    is_full_exit: bool

    @staticmethod
    def hold() -> ExitDecision:
        return ExitDecision(False, "hold", 0.0, False)


class ExitStrategy:
    """
    Multi-level exit strategy:
    - Take profit tranches at +25%, +50%, +100%
    - Stop-loss at -20%
    - Trailing stop 20% on remaining position
    - Time-based exits (1h no +10%, 4h unconditional, 24h max hold)
    """

    def __init__(self, config: AppConfig) -> None:
        self._tp_levels: list[dict] = config.get(
            "positions", "take_profit", default=[
                {"pct": 0.25, "sell_fraction": 0.30},
                {"pct": 0.50, "sell_fraction": 0.30},
                {"pct": 1.00, "sell_fraction": 0.20},
            ]
        )
        self._trailing_stop_pct = config.get(
            "positions", "trailing_stop_pct", default=0.20
        )
        self._trailing_fraction = config.get(
            "positions", "trailing_fraction", default=0.20
        )
        self._stop_loss_pct = config.get("positions", "stop_loss_pct", default=0.20)
        self._time_exits = config.get(
            "positions", "time_exits", default=[
                {"hours": 1, "min_gain_pct": 0.10},
                {"hours": 4, "min_gain_pct": 0.0},
            ]
        )
        self._max_hold_hours = config.get("positions", "max_hold_hours", default=24)

    def evaluate(self, position: Position) -> ExitDecision:
        """Evaluate whether to exit (partially or fully) a position."""
        if position.remaining_tokens <= 0:
            return ExitDecision.hold()

        current = position.current_price_usd
        entry = position.entry_price_usd
        if entry <= 0 or current <= 0:
            return ExitDecision.hold()

        gain_pct = (current - entry) / entry
        hold_hours = position.hold_duration_hours

        # === STOP-LOSS (highest priority) ===
        if gain_pct <= -self._stop_loss_pct:
            logger.warning(
                "STOP-LOSS triggered for %s: %.1f%%",
                position.token_symbol,
                gain_pct * 100,
            )
            return ExitDecision(
                should_exit=True,
                reason=f"stop_loss ({gain_pct:+.1%})",
                sell_fraction=1.0,
                is_full_exit=True,
            )

        # === MAX HOLD TIME ===
        if hold_hours >= self._max_hold_hours:
            logger.info(
                "MAX HOLD triggered for %s: %.1fh",
                position.token_symbol,
                hold_hours,
            )
            return ExitDecision(
                should_exit=True,
                reason=f"max_hold ({hold_hours:.1f}h)",
                sell_fraction=1.0,
                is_full_exit=True,
            )

        # === TIME-BASED EXITS ===
        for te in self._time_exits:
            hours = te["hours"]
            min_gain = te["min_gain_pct"]
            if hold_hours >= hours and gain_pct < min_gain:
                logger.info(
                    "TIME EXIT for %s: %.1fh held, gain=%.1f%% < required %.1f%%",
                    position.token_symbol,
                    hold_hours,
                    gain_pct * 100,
                    min_gain * 100,
                )
                return ExitDecision(
                    should_exit=True,
                    reason=f"time_exit ({hours}h, gain={gain_pct:+.1%})",
                    sell_fraction=1.0,
                    is_full_exit=True,
                )

        # === TRAILING STOP ===
        if position.trailing_stop_activated:
            trailing_price = position.trailing_stop_price
            if current <= trailing_price:
                logger.info(
                    "TRAILING STOP for %s: price=$%.6f <= trail=$%.6f",
                    position.token_symbol,
                    current,
                    trailing_price,
                )
                return ExitDecision(
                    should_exit=True,
                    reason=f"trailing_stop (trail=${trailing_price:.6f})",
                    sell_fraction=1.0,
                    is_full_exit=True,
                )
            # Update trailing stop price if price went higher
            if current > position.highest_price:
                position.highest_price = current
                position.trailing_stop_price = current * (1 - self._trailing_stop_pct)

        # === TAKE PROFIT LEVELS ===
        for i, tp in enumerate(self._tp_levels):
            tp_pct = tp["pct"]
            sell_frac = tp["sell_fraction"]

            if gain_pct >= tp_pct and i not in position.take_profit_levels_hit:
                position.take_profit_levels_hit.append(i)
                logger.info(
                    "TAKE PROFIT L%d for %s: gain=%.1f%% >= %.1f%%, sell %.0f%%",
                    i + 1,
                    position.token_symbol,
                    gain_pct * 100,
                    tp_pct * 100,
                    sell_frac * 100,
                )

                # After all TP levels hit, activate trailing stop on remainder
                if len(position.take_profit_levels_hit) >= len(self._tp_levels):
                    position.trailing_stop_activated = True
                    position.highest_price = current
                    position.trailing_stop_price = current * (1 - self._trailing_stop_pct)

                return ExitDecision(
                    should_exit=True,
                    reason=f"take_profit_L{i + 1} ({tp_pct:+.0%})",
                    sell_fraction=sell_frac,
                    is_full_exit=False,
                )

        return ExitDecision.hold()

    def create_sell_order(
        self, position: Position, decision: ExitDecision
    ) -> TradeOrder:
        """Create a sell order based on the exit decision."""
        tokens_to_sell = position.remaining_tokens * decision.sell_fraction

        return TradeOrder(
            signal_id=position.signal_id,
            token_address=position.token_address,
            token_symbol=position.token_symbol,
            side=TradeSide.SELL,
            amount_tokens=tokens_to_sell,
            amount_usd=tokens_to_sell * position.current_price_usd,
            price_usd=position.current_price_usd,
            status=TradeStatus.PENDING,
        )
