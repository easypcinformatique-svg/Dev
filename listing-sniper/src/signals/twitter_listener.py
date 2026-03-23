"""Twitter/X listener — monitors exchange accounts for listing announcements."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import aiohttp

from src.config import AppConfig
from src.models import Exchange, Signal, SignalSource

logger = logging.getLogger(__name__)

_LISTING_KW = re.compile(
    r"(will list|new listing|listing|trading (starts?|opens?|available)|spot listing)",
    re.IGNORECASE,
)
_TICKER_RE = re.compile(r"\$([A-Z]{2,10})\b|\(([A-Z]{2,10})\)")

_ACCOUNT_EXCHANGE_MAP: dict[str, Exchange] = {
    "binance": Exchange.BINANCE,
    "caborance": Exchange.BINANCE,
    "bybit_official": Exchange.BYBIT,
    "okx": Exchange.OKX,
    "kaborncoin": Exchange.KUCOIN,
}


class TwitterListener:
    """Polls Twitter API v2 for recent tweets from exchange accounts."""

    _BASE = "https://api.twitter.com/2"

    def __init__(self, config: AppConfig) -> None:
        self._bearer = config.yaml_data.get("twitter", {}).get("bearer_token", "") or ""
        if not self._bearer:
            import os
            self._bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
        self._accounts: list[str] = config.get(
            "signals", "twitter", "accounts", default=[]
        )
        self._interval = config.get("signals", "twitter", "poll_interval_sec", default=5)
        self._seen_ids: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._user_ids: dict[str, str] = {}

    async def start(self) -> None:
        if not self._bearer:
            logger.warning("TwitterListener disabled — no bearer token")
            return
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self._bearer}"}
        )
        self._running = True
        # Resolve usernames to IDs
        await self._resolve_users()
        logger.info(
            "TwitterListener started — monitoring %d accounts", len(self._user_ids)
        )

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def _resolve_users(self) -> None:
        """Resolve Twitter usernames to user IDs."""
        if not self._session or not self._accounts:
            return
        try:
            usernames = ",".join(self._accounts)
            async with self._session.get(
                f"{self._BASE}/users/by",
                params={"usernames": usernames},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for user in data.get("data", []):
                        self._user_ids[user["username"].lower()] = user["id"]
        except Exception:
            logger.exception("Failed to resolve Twitter user IDs")

    async def listen(self) -> AsyncIterator[Signal]:
        """Poll for new tweets from monitored accounts."""
        if not self._running:
            return

        while self._running:
            try:
                for username, user_id in self._user_ids.items():
                    signals = await self._check_user(username, user_id)
                    for sig in signals:
                        yield sig
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("TwitterListener poll error")
            await asyncio.sleep(self._interval)

    async def _check_user(self, username: str, user_id: str) -> list[Signal]:
        """Fetch recent tweets for a user and extract listing signals."""
        assert self._session
        signals: list[Signal] = []
        try:
            async with self._session.get(
                f"{self._BASE}/users/{user_id}/tweets",
                params={
                    "max_results": 5,
                    "tweet.fields": "created_at,text",
                },
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return signals
                data = await resp.json()
                for tweet in data.get("data", []):
                    tweet_id = tweet["id"]
                    if tweet_id in self._seen_ids:
                        continue
                    text = tweet.get("text", "")
                    if not _LISTING_KW.search(text):
                        continue
                    self._seen_ids.add(tweet_id)

                    # Extract ticker
                    match = _TICKER_RE.search(text)
                    ticker = (match.group(1) or match.group(2)) if match else ""
                    if not ticker:
                        continue

                    exchange = _ACCOUNT_EXCHANGE_MAP.get(
                        username.lower(), Exchange.BINANCE
                    )

                    created_at = tweet.get("created_at")
                    detection = datetime.now(timezone.utc)
                    if created_at:
                        try:
                            detection = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    signals.append(
                        Signal(
                            token_symbol=ticker,
                            exchange=exchange,
                            source=SignalSource.TWITTER,
                            confidence=0.70,
                            raw_text=text[:500],
                            url=f"https://twitter.com/{username}/status/{tweet_id}",
                            detection_time=detection,
                        )
                    )
                    logger.info(
                        "Twitter signal from @%s: %s — %s",
                        username,
                        ticker,
                        text[:80],
                    )
        except Exception:
            logger.debug("Twitter check failed for @%s", username)

        return signals
