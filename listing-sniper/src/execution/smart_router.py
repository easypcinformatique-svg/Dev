"""Smart order router — selects the best execution path across DEXes."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.execution.jupiter_executor import SOL_MINT

logger = logging.getLogger(__name__)


@dataclass
class RouteQuote:
    """A quote from a specific DEX route."""

    dex: str
    input_mint: str
    output_mint: str
    input_amount: int        # lamports / smallest unit
    output_amount: int
    price_impact_pct: float
    fees_bps: int
    route_plan: list[dict]
    raw_quote: dict


class SmartRouter:
    """Compares routes across Jupiter, Raydium, and Orca to find best execution."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        logger.info("SmartRouter started")

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def find_best_route(
        self,
        input_mint: str,
        output_mint: str,
        amount_lamports: int,
        slippage_bps: int = 200,
    ) -> Optional[RouteQuote]:
        """
        Query multiple DEX aggregators and return the best route.

        Jupiter usually aggregates across all DEXes, but we also query
        Raydium and Orca directly as fallbacks.
        """
        assert self._session

        results = await asyncio.gather(
            self._jupiter_quote(input_mint, output_mint, amount_lamports, slippage_bps),
            self._raydium_quote(input_mint, output_mint, amount_lamports, slippage_bps),
            return_exceptions=True,
        )

        quotes: list[RouteQuote] = []
        for r in results:
            if isinstance(r, RouteQuote):
                quotes.append(r)

        if not quotes:
            logger.warning("No routes found for %s -> %s", input_mint[:8], output_mint[:8])
            return None

        # Best = highest output amount
        best = max(quotes, key=lambda q: q.output_amount)
        logger.info(
            "Best route: %s, output=%d, impact=%.2f%%",
            best.dex,
            best.output_amount,
            best.price_impact_pct,
        )
        return best

    async def _jupiter_quote(
        self, in_mint: str, out_mint: str, amount: int, slippage: int
    ) -> Optional[RouteQuote]:
        assert self._session
        try:
            params = {
                "inputMint": in_mint,
                "outputMint": out_mint,
                "amount": str(amount),
                "slippageBps": str(slippage),
            }
            async with self._session.get(
                "https://quote-api.jup.ag/v6/quote",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return RouteQuote(
                    dex="jupiter",
                    input_mint=in_mint,
                    output_mint=out_mint,
                    input_amount=int(data.get("inAmount", 0)),
                    output_amount=int(data.get("outAmount", 0)),
                    price_impact_pct=float(data.get("priceImpactPct", "0") or "0"),
                    fees_bps=0,
                    route_plan=data.get("routePlan", []),
                    raw_quote=data,
                )
        except Exception:
            logger.debug("Jupiter quote failed")
            return None

    async def _raydium_quote(
        self, in_mint: str, out_mint: str, amount: int, slippage: int
    ) -> Optional[RouteQuote]:
        assert self._session
        try:
            params = {
                "inputMint": in_mint,
                "outputMint": out_mint,
                "amount": str(amount),
                "slippage": str(slippage / 100),  # Raydium uses %
            }
            async with self._session.get(
                "https://transaction-v1.raydium.io/compute/swap-base-in",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("success"):
                    return None
                swap_data = data.get("data", {})
                return RouteQuote(
                    dex="raydium",
                    input_mint=in_mint,
                    output_mint=out_mint,
                    input_amount=amount,
                    output_amount=int(swap_data.get("outputAmount", 0)),
                    price_impact_pct=float(swap_data.get("priceImpact", "0") or "0"),
                    fees_bps=25,  # Raydium standard fee
                    route_plan=[],
                    raw_quote=data,
                )
        except Exception:
            logger.debug("Raydium quote failed")
            return None
