"""Tests for core domain models."""

import pytest
from src.models import (
    Position,
    RiskTier,
    Signal,
    TokenRiskAssessment,
    TradeOrder,
    TradeSide,
    TradeStatus,
    Exchange,
    SignalSource,
)


class TestTokenRiskAssessment:
    def test_safe_token(self):
        risk = TokenRiskAssessment(
            token_address="test",
            liquidity_usd=200000,
            pool_age_hours=48,
            holder_count=5000,
            top10_concentration=0.20,
            is_renounced=True,
            is_honeypot=False,
            has_mint_authority=False,
        )
        score = risk.calculate_risk_score()
        assert score <= 30
        assert risk.risk_tier == RiskTier.SAFE

    def test_medium_risk_token(self):
        risk = TokenRiskAssessment(
            token_address="test",
            liquidity_usd=15000,
            pool_age_hours=3,
            holder_count=300,
            top10_concentration=0.55,
            is_renounced=False,
            is_honeypot=False,
            has_mint_authority=True,
        )
        score = risk.calculate_risk_score()
        assert 31 <= score <= 60
        assert risk.risk_tier == RiskTier.MEDIUM

    def test_danger_token(self):
        risk = TokenRiskAssessment(
            token_address="test",
            liquidity_usd=500,
            pool_age_hours=0.1,
            holder_count=10,
            top10_concentration=0.95,
            is_renounced=False,
            is_honeypot=True,
            has_mint_authority=True,
        )
        score = risk.calculate_risk_score()
        assert score > 80
        assert risk.risk_tier == RiskTier.DANGER

    def test_honeypot_adds_20_points(self):
        r1 = TokenRiskAssessment(
            token_address="t1", is_honeypot=False,
            liquidity_usd=100000, pool_age_hours=100,
            holder_count=10000, top10_concentration=0.1,
            is_renounced=True, has_mint_authority=False,
        )
        r2 = TokenRiskAssessment(
            token_address="t2", is_honeypot=True,
            liquidity_usd=100000, pool_age_hours=100,
            holder_count=10000, top10_concentration=0.1,
            is_renounced=True, has_mint_authority=False,
        )
        s1 = r1.calculate_risk_score()
        s2 = r2.calculate_risk_score()
        assert s2 - s1 == 20


class TestPosition:
    def test_unrealized_pnl_profit(self):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.5,
            remaining_tokens=100,
        )
        assert pos.unrealized_pnl == pytest.approx(50.0)

    def test_unrealized_pnl_loss(self):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=0.8,
            remaining_tokens=100,
        )
        assert pos.unrealized_pnl == pytest.approx(-20.0)

    def test_total_pnl(self):
        pos = Position(
            entry_price_usd=1.0,
            current_price_usd=1.5,
            remaining_tokens=50,
            realized_pnl_usd=25.0,
        )
        # Unrealized: 50 * (1.5 - 1.0) = 25, total = 25 + 25 = 50
        assert pos.total_pnl_usd == pytest.approx(50.0)

    def test_zero_entry_price(self):
        pos = Position(entry_price_usd=0, current_price_usd=1.0, remaining_tokens=100)
        assert pos.unrealized_pnl == 0.0


class TestSignal:
    def test_signal_defaults(self):
        sig = Signal(token_symbol="TEST", exchange=Exchange.BINANCE)
        assert sig.confidence == 0.0
        assert sig.validated is False
        assert sig.chain == "solana"
        assert len(sig.id) == 12

    def test_trade_order_defaults(self):
        order = TradeOrder(token_address="abc", token_symbol="TEST", side=TradeSide.BUY)
        assert order.status == TradeStatus.PENDING
        assert order.slippage_bps == 200
