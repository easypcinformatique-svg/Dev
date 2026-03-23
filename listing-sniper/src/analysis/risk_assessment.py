"""Risk assessment — evaluates token safety before execution."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.models import TokenInfo, TokenRiskAssessment

logger = logging.getLogger(__name__)


class RiskAssessor:
    """Evaluates token risk using on-chain data and heuristics."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._max_top10 = config.get("analysis", "risk", "max_top10_concentration", default=0.90)
        self._min_liquidity = config.get("analysis", "risk", "min_liquidity_usd", default=5000)
        self._min_pool_age = config.get("analysis", "risk", "min_pool_age_hours", default=0.5)
        self._honeypot_check = config.get("analysis", "risk", "honeypot_check", default=True)
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        logger.info("RiskAssessor started")

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def assess(self, token: TokenInfo) -> TokenRiskAssessment:
        """Run full risk assessment on a token."""
        assessment = TokenRiskAssessment(token_address=token.contract_address)

        # Gather data in parallel
        import asyncio
        await asyncio.gather(
            self._check_liquidity(token, assessment),
            self._check_holders(token, assessment),
            self._check_mint_authority(token, assessment),
            self._check_honeypot(token, assessment),
            return_exceptions=True,
        )

        # Calculate pool age from best pool
        if token.pools:
            best_pool = max(token.pools, key=lambda p: p.liquidity_usd)
            assessment.liquidity_usd = best_pool.liquidity_usd
            if best_pool.created_at:
                age = (datetime.now(timezone.utc) - best_pool.created_at).total_seconds()
                assessment.pool_age_hours = age / 3600

        # Calculate final risk score
        assessment.calculate_risk_score()

        logger.info(
            "Risk assessment for %s: score=%d tier=%s liq=$%.0f holders=%d",
            token.symbol,
            assessment.risk_score,
            assessment.risk_tier.value,
            assessment.liquidity_usd,
            assessment.holder_count,
        )
        return assessment

    async def _check_liquidity(
        self, token: TokenInfo, assessment: TokenRiskAssessment
    ) -> None:
        """Check total liquidity across pools."""
        total_liq = sum(p.liquidity_usd for p in token.pools)
        assessment.liquidity_usd = total_liq

    async def _check_holders(
        self, token: TokenInfo, assessment: TokenRiskAssessment
    ) -> None:
        """Check holder count and concentration via Helius or Solscan."""
        assert self._session
        try:
            # Use DexScreener or Birdeye for holder data
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token.contract_address}"
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        # Approximate from pair data
                        assessment.holder_count = max(
                            int(p.get("txns", {}).get("h24", {}).get("buys", 0))
                            for p in pairs
                        ) if pairs else 0
        except Exception:
            logger.debug("Holder check failed for %s", token.symbol)

        # Fallback: use Solana RPC to check largest accounts
        try:
            rpc_url = self._config.solana.rpc_primary
            if rpc_url:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenLargestAccounts",
                    "params": [token.contract_address],
                }
                async with self._session.post(
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        accounts = data.get("result", {}).get("value", [])
                        if accounts:
                            total_supply = sum(
                                float(a.get("uiAmount", 0) or 0) for a in accounts
                            )
                            if total_supply > 0:
                                top10_sum = sum(
                                    float(a.get("uiAmount", 0) or 0)
                                    for a in accounts[:10]
                                )
                                assessment.top10_concentration = top10_sum / total_supply
        except Exception:
            logger.debug("Top10 concentration check failed for %s", token.symbol)

    async def _check_mint_authority(
        self, token: TokenInfo, assessment: TokenRiskAssessment
    ) -> None:
        """Check if the token's mint authority is revoked."""
        assert self._session
        try:
            rpc_url = self._config.solana.rpc_primary
            if not rpc_url:
                return
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token.contract_address,
                    {"encoding": "jsonParsed"},
                ],
            }
            async with self._session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    info = (
                        data.get("result", {})
                        .get("value", {})
                        .get("data", {})
                        .get("parsed", {})
                        .get("info", {})
                    )
                    mint_auth = info.get("mintAuthority")
                    freeze_auth = info.get("freezeAuthority")
                    assessment.has_mint_authority = mint_auth is not None
                    assessment.is_renounced = mint_auth is None and freeze_auth is None
        except Exception:
            logger.debug("Mint authority check failed for %s", token.symbol)

    async def _check_honeypot(
        self, token: TokenInfo, assessment: TokenRiskAssessment
    ) -> None:
        """
        Check if the token might be a honeypot (can buy but not sell).
        Uses a simulated swap quote to test sellability.
        """
        if not self._honeypot_check:
            return
        assert self._session
        try:
            # Try to get a sell quote — if it fails, it might be a honeypot
            url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": token.contract_address,
                "outputMint": "So11111111111111111111111111111111111111112",  # SOL
                "amount": "1000000",  # Small amount
                "slippageBps": "1000",
            }
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("outAmount"):
                        assessment.is_honeypot = False
                    else:
                        assessment.is_honeypot = True
                else:
                    # If quote fails, might be honeypot
                    assessment.is_honeypot = True
        except Exception:
            logger.debug("Honeypot check inconclusive for %s", token.symbol)
            assessment.is_honeypot = False  # Assume not honeypot if check fails
