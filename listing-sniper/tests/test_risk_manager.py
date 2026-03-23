"""Tests for risk manager — ensures hard limits cannot be bypassed."""

import pytest
import asyncio

from src.positions.pnl_tracker import PnLTracker
from src.risk.risk_manager import RiskManager


@pytest.fixture
def risk_mgr():
    # PnLTracker needs db and redis but we only test RiskManager logic
    pnl = PnLTracker.__new__(PnLTracker)
    pnl._daily_pnl = {}
    pnl._trade_returns = []
    pnl._equity_curve = []
    pnl._peak_equity = 0
    return RiskManager(pnl)


class TestRiskManager:
    @pytest.mark.asyncio
    async def test_allows_normal_trade(self, risk_mgr):
        check = await risk_mgr.check_can_trade(
            portfolio_value_usd=10000,
            position_size_usd=300,
            current_exposure_usd=1000,
        )
        assert check.allowed
        assert check.reason == "All risk checks passed"

    @pytest.mark.asyncio
    async def test_blocks_oversized_position(self, risk_mgr):
        check = await risk_mgr.check_can_trade(
            portfolio_value_usd=10000,
            position_size_usd=600,  # 6% > 5% limit
            current_exposure_usd=0,
        )
        assert not check.allowed
        assert "Position too large" in check.reason

    @pytest.mark.asyncio
    async def test_blocks_excess_exposure(self, risk_mgr):
        check = await risk_mgr.check_can_trade(
            portfolio_value_usd=10000,
            position_size_usd=500,
            current_exposure_usd=2600,  # 2600 + 500 = 3100 > 30%
        )
        assert not check.allowed
        assert "Exposure limit" in check.reason

    @pytest.mark.asyncio
    async def test_blocks_after_max_daily_trades(self, risk_mgr):
        # Simulate 10 trades
        for _ in range(10):
            risk_mgr.record_trade(10)  # Small profit

        check = await risk_mgr.check_can_trade(10000, 200, 0)
        assert not check.allowed
        assert "Daily trade limit" in check.reason

    @pytest.mark.asyncio
    async def test_blocks_after_daily_loss(self, risk_mgr):
        # Simulate big loss
        risk_mgr.record_trade(-300)
        risk_mgr.record_trade(-300)  # Total -600 = 6% of 10k

        check = await risk_mgr.check_can_trade(10000, 200, 0)
        assert not check.allowed
        assert "Daily loss limit" in check.reason

    @pytest.mark.asyncio
    async def test_blocks_consecutive_losses(self, risk_mgr):
        risk_mgr.record_trade(-10)
        risk_mgr.record_trade(-10)
        risk_mgr.record_trade(-10)

        check = await risk_mgr.check_can_trade(10000, 200, 0)
        assert not check.allowed
        assert "consecutive losses" in check.reason

    @pytest.mark.asyncio
    async def test_consecutive_losses_reset(self, risk_mgr):
        risk_mgr.record_trade(-10)
        risk_mgr.record_trade(-10)
        risk_mgr.record_trade(-10)

        risk_mgr.reset_consecutive_losses()
        check = await risk_mgr.check_can_trade(10000, 200, 0)
        assert check.allowed

    @pytest.mark.asyncio
    async def test_halt_blocks_trading(self, risk_mgr):
        risk_mgr.force_halt(hours=1)
        check = await risk_mgr.check_can_trade(10000, 200, 0)
        assert not check.allowed
        assert "halted" in check.reason.lower()

    def test_trades_remaining(self, risk_mgr):
        assert risk_mgr.trades_remaining_today == 10
        risk_mgr.record_trade(10)
        assert risk_mgr.trades_remaining_today == 9

    def test_hard_limits_immutable(self, risk_mgr):
        # Verify hard limits are class-level constants
        assert RiskManager.MAX_POSITION_PCT == 0.05
        assert RiskManager.MAX_DAILY_LOSS_PCT == 0.05
        assert RiskManager.MAX_EXPOSURE_PCT == 0.30
        assert RiskManager.MAX_TRADES_PER_DAY == 10
        assert RiskManager.MAX_WEEKLY_LOSS_PCT == 0.10
        assert RiskManager.STOP_LOSS_PCT == 0.20
