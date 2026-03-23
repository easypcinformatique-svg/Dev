"""Token discovery — resolve token addresses and find liquidity pools on Solana DEXes."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.infra.redis_cache import RedisCache
from src.models import PoolInfo, Signal, TokenInfo

logger = logging.getLogger(__name__)


class TokenDiscovery:
    """Discovers token contract addresses and DEX pools for newly listed tokens."""

    def __init__(self, config: AppConfig, redis: RedisCache) -> None:
        self._config = config
        self._redis = redis
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(
            total=config.get("analysis", "token_discovery", "timeout_sec", default=5)
        )

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        logger.info("TokenDiscovery started")

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def discover(self, signal: Signal) -> Optional[TokenInfo]:
        """
        Find the Solana token address and pools for a signal.
        Queries multiple providers in parallel for speed.
        """
        assert self._session

        # Check cache first
        cached = await self._redis.get_json(f"token:{signal.token_symbol}")
        if cached:
            return TokenInfo(**cached)

        # Query all providers in parallel
        results = await asyncio.gather(
            self._dexscreener_search(signal.token_symbol),
            self._jupiter_search(signal.token_symbol),
            self._birdeye_search(signal.token_symbol),
            return_exceptions=True,
        )

        token_info: Optional[TokenInfo] = None
        for result in results:
            if isinstance(result, TokenInfo) and result.contract_address:
                token_info = result
                break

        if not token_info:
            logger.warning("Could not discover token: %s", signal.token_symbol)
            return None

        # Enrich with pool data
        if token_info.contract_address and not token_info.pools:
            pools = await self._find_pools(token_info.contract_address)
            token_info.pools = pools

        # Cache for 5 minutes
        await self._redis.set_json(
            f"token:{signal.token_symbol}",
            {
                "symbol": token_info.symbol,
                "name": token_info.name,
                "contract_address": token_info.contract_address,
                "chain": token_info.chain,
                "decimals": token_info.decimals,
                "coingecko_id": token_info.coingecko_id,
                "dexscreener_url": token_info.dexscreener_url,
            },
            ttl=300,
        )

        logger.info(
            "Discovered %s: address=%s, pools=%d",
            signal.token_symbol,
            token_info.contract_address[:12],
            len(token_info.pools),
        )
        return token_info

    async def _dexscreener_search(self, symbol: str) -> Optional[TokenInfo]:
        """Search DexScreener for token info (fastest provider)."""
        assert self._session
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            async with self._session.get(url, timeout=self._timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                pairs = data.get("pairs", [])

                # Filter for Solana pairs
                sol_pairs = [
                    p for p in pairs
                    if p.get("chainId") == "solana"
                    and p.get("baseToken", {}).get("symbol", "").upper() == symbol.upper()
                ]

                if not sol_pairs:
                    return None

                # Pick the pair with the most liquidity
                sol_pairs.sort(
                    key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
                    reverse=True,
                )
                best = sol_pairs[0]
                base = best.get("baseToken", {})

                pools = []
                for pair in sol_pairs[:5]:
                    pool_created = pair.get("pairCreatedAt")
                    created_dt = None
                    if pool_created:
                        try:
                            created_dt = datetime.fromtimestamp(
                                pool_created / 1000, tz=timezone.utc
                            )
                        except (ValueError, OSError):
                            pass

                    pools.append(
                        PoolInfo(
                            pool_address=pair.get("pairAddress", ""),
                            dex=pair.get("dexId", "unknown"),
                            base_token=base.get("address", ""),
                            quote_token=pair.get("quoteToken", {}).get("address", ""),
                            liquidity_usd=float(
                                pair.get("liquidity", {}).get("usd", 0) or 0
                            ),
                            volume_24h_usd=float(
                                pair.get("volume", {}).get("h24", 0) or 0
                            ),
                            price_usd=float(pair.get("priceUsd", 0) or 0),
                            created_at=created_dt,
                        )
                    )

                return TokenInfo(
                    symbol=base.get("symbol", symbol),
                    name=base.get("name", symbol),
                    contract_address=base.get("address", ""),
                    chain="solana",
                    pools=pools,
                    dexscreener_url=best.get("url"),
                )
        except Exception:
            logger.debug("DexScreener search failed for %s", symbol)
            return None

    async def _jupiter_search(self, symbol: str) -> Optional[TokenInfo]:
        """Search Jupiter token list for address."""
        assert self._session
        try:
            url = "https://token.jup.ag/strict"
            async with self._session.get(url, timeout=self._timeout) as resp:
                if resp.status != 200:
                    return None
                tokens = await resp.json()
                for token in tokens:
                    if token.get("symbol", "").upper() == symbol.upper():
                        return TokenInfo(
                            symbol=token["symbol"],
                            name=token.get("name", symbol),
                            contract_address=token["address"],
                            chain="solana",
                            decimals=token.get("decimals", 9),
                        )
        except Exception:
            logger.debug("Jupiter search failed for %s", symbol)
        return None

    async def _birdeye_search(self, symbol: str) -> Optional[TokenInfo]:
        """Search Birdeye for token info."""
        assert self._session
        import os
        api_key = os.getenv("BIRDEYE_API_KEY", "")
        if not api_key:
            return None
        try:
            url = "https://public-api.birdeye.so/defi/v3/search"
            headers = {"X-API-KEY": api_key}
            params = {"keyword": symbol, "chain": "solana", "sort_by": "liquidity", "sort_type": "desc"}
            async with self._session.get(
                url, headers=headers, params=params, timeout=self._timeout
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                items = data.get("data", {}).get("items", [])
                for item in items:
                    if item.get("symbol", "").upper() == symbol.upper():
                        return TokenInfo(
                            symbol=item["symbol"],
                            name=item.get("name", symbol),
                            contract_address=item["address"],
                            chain="solana",
                            decimals=item.get("decimals", 9),
                        )
        except Exception:
            logger.debug("Birdeye search failed for %s", symbol)
        return None

    async def _find_pools(self, token_address: str) -> list[PoolInfo]:
        """Find all DEX pools for a token on Solana."""
        assert self._session
        pools: list[PoolInfo] = []

        # Jupiter quote check
        try:
            url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                "outputMint": token_address,
                "amount": "100000000",  # 0.1 SOL in lamports
                "slippageBps": "300",
            }
            async with self._session.get(url, params=params, timeout=self._timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for route in data.get("routePlan", []):
                        swap = route.get("swapInfo", {})
                        pools.append(
                            PoolInfo(
                                pool_address=swap.get("ammKey", ""),
                                dex=swap.get("label", "jupiter"),
                                base_token=token_address,
                                quote_token="So11111111111111111111111111111111111111112",
                                price_usd=0,  # Will be enriched later
                            )
                        )
        except Exception:
            logger.debug("Jupiter pool search failed for %s", token_address[:12])

        return pools
