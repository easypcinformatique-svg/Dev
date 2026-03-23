"""Binance announcement listener — polls the CMS API for new listing announcements."""

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

# Common listing keywords
_LISTING_KW = re.compile(
    r"(will list|new listing|adds?|trading start|spot listing|perpetual listing)",
    re.IGNORECASE,
)
# Extract ticker from text like "Binance Will List TokenName (TICKER)"
_TICKER_RE = re.compile(r"\(([A-Z0-9]{2,10})\)")
# Extract date/time patterns
_DATETIME_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"
)

# Binance CMS API
_BINANCE_CMS = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
_BINANCE_ANNOUNCE = "https://www.binance.com/en/support/announcement/new-cryptocurrency-listing"

# Alternative: Binance announcements API (catalog)
_BINANCE_CATALOG = (
    "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
)


class BinanceListener:
    """Polls Binance announcements for new listing signals."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._interval = config.get("signals", "binance", "poll_interval_sec", default=2)
        self._seen_ids: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0 (compatible; ListingBot/1.0)"}
        )
        self._running = True
        logger.info("BinanceListener started (poll every %ds)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def listen(self) -> AsyncIterator[Signal]:
        """Continuously yield new listing signals."""
        while self._running:
            try:
                signals = await self._poll()
                for sig in signals:
                    yield sig
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("BinanceListener poll error")
            await asyncio.sleep(self._interval)

    async def _poll(self) -> list[Signal]:
        """Fetch latest announcements and extract listing signals."""
        assert self._session
        signals: list[Signal] = []

        # Method 1: CMS article list
        try:
            payload = {
                "type": 1,
                "catalogId": 48,  # New Listings category
                "pageNo": 1,
                "pageSize": 20,
            }
            async with self._session.post(
                _BINANCE_CMS, json=payload, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    articles = (
                        data.get("data", {}).get("articles", [])
                        if isinstance(data.get("data"), dict)
                        else []
                    )
                    for article in articles:
                        sig = self._parse_article(article)
                        if sig:
                            signals.append(sig)
        except Exception:
            logger.debug("Binance CMS poll failed, trying catalog fallback")

        # Method 2: Catalog fallback
        if not signals:
            try:
                async with self._session.get(
                    _BINANCE_CATALOG,
                    params={"catalogId": 48, "pageNo": 1, "pageSize": 10},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = (
                            data.get("data", {}).get("articles", [])
                            if isinstance(data.get("data"), dict)
                            else []
                        )
                        for article in articles:
                            sig = self._parse_article(article)
                            if sig:
                                signals.append(sig)
            except Exception:
                logger.debug("Binance catalog poll also failed")

        return signals

    def _parse_article(self, article: dict) -> Optional[Signal]:
        """Parse a single CMS article into a Signal if it's a listing."""
        article_id = str(article.get("id", article.get("code", "")))
        title = article.get("title", "")

        # Skip if already seen
        if article_id in self._seen_ids:
            return None

        # Check if it's a listing announcement
        if not _LISTING_KW.search(title):
            return None

        self._seen_ids.add(article_id)

        # Extract ticker
        ticker_match = _TICKER_RE.search(title)
        ticker = ticker_match.group(1) if ticker_match else ""
        if not ticker:
            # Try to extract from title words
            words = title.split()
            for i, w in enumerate(words):
                if w.lower() in ("list", "lists", "adds"):
                    if i + 1 < len(words):
                        candidate = words[i + 1].strip("(),.!").upper()
                        if 2 <= len(candidate) <= 10 and candidate.isalpha():
                            ticker = candidate
                            break

        if not ticker:
            logger.debug("Could not extract ticker from: %s", title)
            return None

        # Extract listing time if present
        listing_time = None
        release_date = article.get("releaseDate")
        if release_date:
            try:
                if isinstance(release_date, (int, float)):
                    listing_time = datetime.fromtimestamp(
                        release_date / 1000, tz=timezone.utc
                    )
            except (ValueError, OSError):
                pass

        # Determine token name from title
        token_name = ""
        paren_idx = title.find("(")
        if paren_idx > 0:
            # Everything before the first parenthesis, after "Will List " etc.
            pre = title[:paren_idx].strip()
            for kw in ["Will List", "Lists", "Adds", "New Listing:"]:
                if kw.lower() in pre.lower():
                    token_name = pre.split(kw)[-1].strip() if kw in pre else pre
                    break

        signal = Signal(
            token_symbol=ticker,
            token_name=token_name or ticker,
            exchange=Exchange.BINANCE,
            listing_time=listing_time,
            source=SignalSource.API,
            confidence=0.85,
            raw_text=title,
            url=f"https://www.binance.com/en/support/announcement/{article_id}",
        )
        logger.info("Binance listing signal: %s (%s)", ticker, title[:80])
        return signal


class BybitListener:
    """Polls Bybit announcements for new listing signals."""

    _URL = "https://api.bybit.com/v5/announcements/index"

    def __init__(self, config: AppConfig) -> None:
        self._interval = config.get("signals", "bybit", "poll_interval_sec", default=3)
        self._seen_ids: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._running = True
        logger.info("BybitListener started")

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def listen(self) -> AsyncIterator[Signal]:
        while self._running:
            try:
                async with self._session.get(  # type: ignore[union-attr]
                    self._URL,
                    params={"locale": "en-US", "type": "new_crypto", "limit": 10},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("result", {}).get("list", []):
                            aid = str(item.get("id", ""))
                            if aid in self._seen_ids:
                                continue
                            title = item.get("title", "")
                            if not _LISTING_KW.search(title):
                                continue
                            self._seen_ids.add(aid)
                            tm = _TICKER_RE.search(title)
                            if tm:
                                yield Signal(
                                    token_symbol=tm.group(1),
                                    exchange=Exchange.BYBIT,
                                    source=SignalSource.API,
                                    confidence=0.80,
                                    raw_text=title,
                                )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("BybitListener error")
            await asyncio.sleep(self._interval)


class OKXListener:
    """Polls OKX announcements for new listing signals."""

    _URL = "https://www.okx.com/api/v5/support/announcements"

    def __init__(self, config: AppConfig) -> None:
        self._interval = config.get("signals", "okx", "poll_interval_sec", default=3)
        self._seen_ids: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._running = True
        logger.info("OKXListener started")

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def listen(self) -> AsyncIterator[Signal]:
        while self._running:
            try:
                async with self._session.get(  # type: ignore[union-attr]
                    self._URL,
                    params={"annType": "listings", "page": "1", "limit": "10"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("data", []):
                            aid = str(item.get("id", ""))
                            if aid in self._seen_ids:
                                continue
                            title = item.get("title", "")
                            if not _LISTING_KW.search(title):
                                continue
                            self._seen_ids.add(aid)
                            tm = _TICKER_RE.search(title)
                            if tm:
                                yield Signal(
                                    token_symbol=tm.group(1),
                                    exchange=Exchange.OKX,
                                    source=SignalSource.API,
                                    confidence=0.80,
                                    raw_text=title,
                                )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("OKXListener error")
            await asyncio.sleep(self._interval)


class KuCoinListener:
    """Polls KuCoin announcements for new listing signals."""

    _URL = "https://www.kucoin.com/_api/cms/articles"

    def __init__(self, config: AppConfig) -> None:
        self._interval = config.get("signals", "kucoin", "poll_interval_sec", default=5)
        self._seen_ids: set[str] = set()
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._running = True
        logger.info("KuCoinListener started")

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def listen(self) -> AsyncIterator[Signal]:
        while self._running:
            try:
                async with self._session.get(  # type: ignore[union-attr]
                    self._URL,
                    params={"category": "listing", "lang": "en_US", "page": 1, "pageSize": 10},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("items", []):
                            aid = str(item.get("id", ""))
                            if aid in self._seen_ids:
                                continue
                            title = item.get("title", "")
                            if not _LISTING_KW.search(title):
                                continue
                            self._seen_ids.add(aid)
                            tm = _TICKER_RE.search(title)
                            if tm:
                                yield Signal(
                                    token_symbol=tm.group(1),
                                    exchange=Exchange.KUCOIN,
                                    source=SignalSource.API,
                                    confidence=0.75,
                                    raw_text=title,
                                )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("KuCoinListener error")
            await asyncio.sleep(self._interval)
