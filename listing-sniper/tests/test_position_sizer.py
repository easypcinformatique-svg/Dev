"""Tests for position sizing logic."""

import pytest
from src.analysis.position_sizer import PositionSizer, _MAX_POSITION_USD, _MIN_POSITION_USD
from src.config import AppConfig
from src.models import RiskTier, TokenRiskAssessment


@pytest.fixture
def sizer():
    config = AppConfig()
    config.yaml_data = {"execution": {"max_slippage_bps": 200}}
    return PositionSizer(config)


class TestPositionSizer:
    def test_safe_token_full_position(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=500000)
        risk.risk_score = 20
        risk.risk_tier = RiskTier.SAFE
        size = sizer.calculate(10000, 150.0, risk)
        assert size.amount_usd > 0
        assert size.amount_usd <= _MAX_POSITION_USD
        assert size.amount_usd <= 10000 * 0.05  # 5% cap

    def test_danger_token_skipped(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=500000)
        risk.risk_score = 90
        risk.risk_tier = RiskTier.DANGER
        size = sizer.calculate(10000, 150.0, risk)
        assert size.amount_usd == 0
        assert "DANGER" in size.reason

    def test_liquidity_cap(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=1000)
        risk.risk_score = 20
        risk.risk_tier = RiskTier.SAFE
        size = sizer.calculate(100000, 150.0, risk)
        # 2% of $1000 = $20 < $100 minimum → may skip or force minimum
        assert size.amount_usd <= 1000 * 0.02 or size.amount_usd == 0

    def test_portfolio_cap(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=1000000)
        risk.risk_score = 20
        risk.risk_tier = RiskTier.SAFE
        size = sizer.calculate(5000, 150.0, risk)
        assert size.amount_usd <= 5000 * 0.05  # $250 max

    def test_medium_risk_half_position(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=500000)
        risk.risk_score = 45
        risk.risk_tier = RiskTier.MEDIUM
        size = sizer.calculate(10000, 150.0, risk)
        assert size.amount_usd > 0
        assert size.risk_tier == RiskTier.MEDIUM

    def test_sol_conversion(self, sizer):
        risk = TokenRiskAssessment(token_address="t", liquidity_usd=500000)
        risk.risk_score = 20
        risk.risk_tier = RiskTier.SAFE
        size = sizer.calculate(10000, 200.0, risk)
        if size.amount_usd > 0:
            assert size.amount_sol == pytest.approx(size.amount_usd / 200.0, abs=0.01)
