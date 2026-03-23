"""Tests for exit strategy logic."""

import pytest
from datetime import datetime, timedelta, timezone

from src.config import AppConfig
from src.models import Position, TradeStatus
from src.positions.exit_strategy import ExitStrategy


@pytest.fixture
def strategy():
    config = AppConfig()
    config.yaml_data = {
        "positions": {
            "take_profit": [
                {"pct": 0.25, "sell_fraction": 0.30},
                {"pct": 0.50, "sell_fraction": 0.30},
                {"pct": 1.00, "sell_fraction": 0.20},
            ],
            "trailing_stop_pct": 0.20,
            "trailing_fraction": 0.20,
            "stop_loss_pct": 0.20,
            "time_exits": [
                {"hours": 1, "min_gain_pct": 0.10},
                {"hours": 4, "min_gain_pct": 0.0},
            ],
            "max_hold_hours": 24,
        }
    }
    return ExitStrategy(config)


class TestExitStrategy:
    def test_hold_when_price_flat(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.05,
            remaining_tokens=100,
        )
        decision = strategy.evaluate(pos)
        assert not decision.should_exit

    def test_stop_loss_triggers(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=0.75,  # -25%
            remaining_tokens=100,
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert decision.is_full_exit
        assert decision.sell_fraction == 1.0
        assert "stop_loss" in decision.reason

    def test_take_profit_l1(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.30,  # +30% > 25% TP1
            remaining_tokens=100,
            take_profit_levels_hit=[],
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert not decision.is_full_exit
        assert decision.sell_fraction == 0.30
        assert "take_profit_L1" in decision.reason

    def test_take_profit_l2(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.55,  # +55% > 50% TP2
            remaining_tokens=100,
            take_profit_levels_hit=[0],  # L1 already hit
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert decision.sell_fraction == 0.30
        assert "take_profit_L2" in decision.reason

    def test_time_exit_1h(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.05,  # Only +5% < required 10%
            remaining_tokens=100,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=1.5),
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert decision.is_full_exit
        assert "time_exit" in decision.reason

    def test_max_hold_time(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.15,  # +15% but held too long
            remaining_tokens=100,
            opened_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert decision.is_full_exit
        assert "max_hold" in decision.reason

    def test_no_exit_when_no_tokens(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=0.5,  # Would trigger stop loss
            remaining_tokens=0,
        )
        decision = strategy.evaluate(pos)
        assert not decision.should_exit

    def test_trailing_stop(self, strategy):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.80,  # Was high, now dropped
            remaining_tokens=100,
            take_profit_levels_hit=[0, 1, 2],  # All TPs hit
            trailing_stop_activated=True,
            highest_price=2.5,
            trailing_stop_price=2.0,  # 20% below peak
        )
        decision = strategy.evaluate(pos)
        assert decision.should_exit
        assert "trailing_stop" in decision.reason
