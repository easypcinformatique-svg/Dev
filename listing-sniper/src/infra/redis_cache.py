"""Redis cache for real-time prices, signal deduplication, and rate limiting."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from src.config import AppConfig

logger = logging.getLogger(__name__)

# Key prefixes
_PRICE = "price:"
_SIGNAL = "signal:"
_RATE = "rate:"
_LOCK = "lock:"


class RedisCache:
    """Async Redis wrapper for the sniper system."""

    def __init__(self, config: AppConfig) -> None:
        self._url = config.redis.url
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._url, decode_responses=True, max_connections=20
        )
        await self._client.ping()
        logger.info("Redis connected")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("Redis closed")

    @property
    def client(self) -> aioredis.Redis:
        assert self._client is not None, "Redis not connected"
        return self._client

    # ── Price Cache ──────────────────────────────────────────

    async def set_price(self, token: str, price: float, ttl: int = 30) -> None:
        await self.client.set(f"{_PRICE}{token}", str(price), ex=ttl)

    async def get_price(self, token: str) -> Optional[float]:
        val = await self.client.get(f"{_PRICE}{token}")
        return float(val) if val else None

    # ── Signal Deduplication ─────────────────────────────────

    async def is_signal_seen(self, key: str) -> bool:
        """Check if we already processed this signal (by composite key)."""
        return bool(await self.client.exists(f"{_SIGNAL}{key}"))

    async def mark_signal_seen(self, key: str, ttl: int = 86400) -> None:
        """Mark signal as seen for 24h by default."""
        await self.client.set(f"{_SIGNAL}{key}", "1", ex=ttl)

    # ── Rate Limiting ────────────────────────────────────────

    async def check_rate_limit(self, key: str, max_count: int, window_sec: int) -> bool:
        """Return True if under the rate limit."""
        rk = f"{_RATE}{key}"
        pipe = self._client.pipeline()  # type: ignore[union-attr]
        pipe.incr(rk)
        pipe.expire(rk, window_sec)
        results = await pipe.execute()
        return int(results[0]) <= max_count

    # ── Distributed Lock ─────────────────────────────────────

    async def acquire_lock(self, name: str, ttl: int = 30) -> bool:
        return bool(
            await self.client.set(f"{_LOCK}{name}", "1", nx=True, ex=ttl)
        )

    async def release_lock(self, name: str) -> None:
        await self.client.delete(f"{_LOCK}{name}")

    # ── Generic helpers ──────────────────────────────────────

    async def set_json(self, key: str, data: Any, ttl: int = 300) -> None:
        await self.client.set(key, json.dumps(data), ex=ttl)

    async def get_json(self, key: str) -> Optional[Any]:
        val = await self.client.get(key)
        return json.loads(val) if val else None
