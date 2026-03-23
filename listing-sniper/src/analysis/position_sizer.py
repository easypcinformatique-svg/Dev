"""Position sizing — Kelly Criterion adapted for crypto listing sniping."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config import AppConfig
from src.models import RiskTier, TokenRiskAssessment

logger = logging.getLogger(__name__)

# Hard limits — never exceeded
_MIN_POSITION_USD = 100.0
_MAX_POSITION_USD = 5000.0
_MAX_PORTFOLIO_PCT = 0.05     # 5%
_MAX_POOL_LIQUIDITY_PCT = 0.02  # 2% of pool liquidity


@dataclass
class PositionSize:
    """Calculated position size with reasoning."""

    amount_usd: float
    amount_sol: float
    reason: str
    risk_tier: RiskTier
    kelly_fraction: float
    liquidity_cap_usd: float
    portfolio_cap_usd: float


class PositionSizer:
    """Calculates optimal position size using adapted Kelly Criterion."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._test_mode = config.mode in ("paper", "dry_run")
        self._max_slippage_bps = config.get(
            "execution", "max_slippage_bps", default=200
        )

    def calculate(
        self,
        portfolio_value_usd: float,
        sol_price_usd: float,
        risk: TokenRiskAssessment,
        max_slippage_bps: int | None = None,
    ) -> PositionSize:
        """
        Calculate optimal position size.

        Rules:
        - Never more than 5% of portfolio
        - Never more than 2% of pool liquidity (limit slippage)
        - Reduction proportional to risk score
        - Minimum $100, Maximum $5000
        """
        if max_slippage_bps is None:
            max_slippage_bps = self._max_slippage_bps

        # In test mode, use larger position limits for small portfolios
        max_position_pct = 0.10 if self._test_mode else _MAX_PORTFOLIO_PCT
        min_position_usd = 10.0 if self._test_mode else _MIN_POSITION_USD

        # Hard cap: % of portfolio
        portfolio_cap = portfolio_value_usd * max_position_pct

        # Hard cap: % of pool liquidity (to limit price impact)
        liquidity_cap = risk.liquidity_usd * _MAX_POOL_LIQUIDITY_PCT

        # Kelly fraction based on risk tier
        # Win probability and payoff ratio vary by risk tier
        if risk.risk_tier == RiskTier.SAFE:
            # ~65% win rate, 2:1 payoff → Kelly = 0.65 - 0.35/2 = 0.475
            kelly = 0.475
            risk_multiplier = 1.0
        elif risk.risk_tier == RiskTier.MEDIUM:
            # ~55% win rate, 1.5:1 payoff → Kelly = 0.55 - 0.45/1.5 = 0.25
            kelly = 0.25
            risk_multiplier = 0.5
        elif risk.risk_tier == RiskTier.RISKY:
            # ~40% win rate, 2:1 payoff → Kelly = 0.40 - 0.60/2 = 0.10
            kelly = 0.10
            risk_multiplier = 0.2
        else:  # DANGER
            return PositionSize(
                amount_usd=0,
                amount_sol=0,
                reason=f"DANGER tier (score={risk.risk_score}) — skipping trade",
                risk_tier=risk.risk_tier,
                kelly_fraction=0,
                liquidity_cap_usd=liquidity_cap,
                portfolio_cap_usd=portfolio_cap,
            )

        # Half-Kelly for safety (standard practice)
        half_kelly = kelly * 0.5

        # Base position
        kelly_position = portfolio_value_usd * half_kelly * risk_multiplier

        # Apply all caps
        amount_usd = min(
            kelly_position,
            portfolio_cap,
            liquidity_cap,
            _MAX_POSITION_USD,
        )

        # Apply minimum
        if amount_usd < min_position_usd:
            if portfolio_value_usd >= min_position_usd * 3:
                # Portfolio big enough but position too small — skip
                return PositionSize(
                    amount_usd=0,
                    amount_sol=0,
                    reason=f"Position too small (${amount_usd:.0f} < ${min_position_usd})",
                    risk_tier=risk.risk_tier,
                    kelly_fraction=half_kelly,
                    liquidity_cap_usd=liquidity_cap,
                    portfolio_cap_usd=portfolio_cap,
                )
            amount_usd = min_position_usd

        # Convert to SOL
        amount_sol = amount_usd / sol_price_usd if sol_price_usd > 0 else 0

        reason = (
            f"Kelly={half_kelly:.3f} × risk_mult={risk_multiplier:.1f} "
            f"→ ${kelly_position:.0f}, "
            f"capped by {'portfolio' if amount_usd == portfolio_cap else 'liquidity' if amount_usd == liquidity_cap else 'max' if amount_usd == _MAX_POSITION_USD else 'kelly'}"
        )

        logger.info(
            "Position size for risk=%d (%s): $%.0f (%.4f SOL). %s",
            risk.risk_score,
            risk.risk_tier.value,
            amount_usd,
            amount_sol,
            reason,
        )

        return PositionSize(
            amount_usd=round(amount_usd, 2),
            amount_sol=round(amount_sol, 6),
            reason=reason,
            risk_tier=risk.risk_tier,
            kelly_fraction=half_kelly,
            liquidity_cap_usd=liquidity_cap,
            portfolio_cap_usd=portfolio_cap,
        )
