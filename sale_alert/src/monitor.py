"""Ticketmaster Discovery API monitor.

Polls the public Discovery API for events matching watched artists,
detects when an event goes on-sale, and fires a callback.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable

import aiohttp

from sale_alert.src.config import AppConfig, EventConfig

logger = logging.getLogger(__name__)

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
MIN_REQUEST_INTERVAL = 2  # seconds between requests (rate-limit safety)


@dataclass
class DetectedEvent:
    """An event that was detected as on-sale."""

    artist: str
    event_id: str
    event_name: str
    url: str
    start_date: str
    min_price: float | None
    max_price: float | None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


OnSaleCallback = Callable[[DetectedEvent], Awaitable[None]]


class TicketmasterMonitor:
    """Polls Ticketmaster Discovery API and detects new on-sale events."""

    def __init__(
        self,
        config: AppConfig,
        on_sale_callback: OnSaleCallback,
    ) -> None:
        self._config = config
        self._callback = on_sale_callback
        self._seen_event_ids: set[str] = set()
        self._consecutive_errors = 0
        self._max_errors = 3  # circuit breaker threshold
        self._running = False

    async def start(self) -> None:
        """Start monitoring all configured artists concurrently."""
        if not self._config.tm_api_key:
            logger.error("TM_API_KEY is not set — cannot start monitor")
            return

        self._running = True
        logger.info(
            "Starting Ticketmaster monitor for %d artist(s)",
            len(self._config.events),
        )

        tasks = [
            asyncio.create_task(self._watch_artist(ev))
            for ev in self._config.events
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self) -> None:
        self._running = False

    async def _watch_artist(self, event_cfg: EventConfig) -> None:
        """Poll loop for a single artist."""
        logger.info("Watching artist: %s", event_cfg.artist)

        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    await self._poll_once(session, event_cfg)
                    self._consecutive_errors = 0
                except Exception:
                    self._consecutive_errors += 1
                    logger.exception(
                        "Error polling for %s (consecutive: %d)",
                        event_cfg.artist,
                        self._consecutive_errors,
                    )
                    if self._consecutive_errors >= self._max_errors:
                        logger.error(
                            "Circuit breaker triggered after %d errors for %s",
                            self._max_errors,
                            event_cfg.artist,
                        )
                        # Back off longer before retrying
                        await asyncio.sleep(60)
                        self._consecutive_errors = 0

                await asyncio.sleep(self._config.poll_interval_seconds)

    async def _poll_once(
        self,
        session: aiohttp.ClientSession,
        event_cfg: EventConfig,
    ) -> None:
        params = {
            "apikey": self._config.tm_api_key,
            "keyword": event_cfg.artist,
            "countryCode": "FR",
            "size": "50",
        }

        async with session.get(DISCOVERY_URL, params=params) as resp:
            if resp.status == 429:
                logger.warning("Rate-limited by Ticketmaster, backing off")
                await asyncio.sleep(10)
                return
            resp.raise_for_status()
            data = await resp.json()

        events = (
            data.get("_embedded", {}).get("events", []) if data else []
        )

        for event in events:
            event_id = event.get("id", "")
            if event_id in self._seen_event_ids:
                continue

            sales = event.get("sales", {}).get("public", {})
            if not sales.get("startDateTime"):
                continue

            # Check if currently on-sale
            start_public = sales.get("startDateTime", "")
            end_public = sales.get("endDateTime", "")
            now_iso = datetime.now(timezone.utc).isoformat()

            if start_public <= now_iso and (
                not end_public or now_iso <= end_public
            ):
                self._seen_event_ids.add(event_id)

                # Extract price range
                price_ranges = event.get("priceRanges", [])
                min_price = price_ranges[0].get("min") if price_ranges else None
                max_price = price_ranges[0].get("max") if price_ranges else None

                detected = DetectedEvent(
                    artist=event_cfg.artist,
                    event_id=event_id,
                    event_name=event.get("name", ""),
                    url=event.get("url", ""),
                    start_date=event.get("dates", {})
                    .get("start", {})
                    .get("localDate", ""),
                    min_price=min_price,
                    max_price=max_price,
                )

                logger.info(
                    "ON-SALE detected: %s — %s",
                    detected.event_name,
                    detected.url,
                )
                await self._callback(detected)

            else:
                # Not yet on-sale — track it so we detect the transition
                # We do NOT add it to _seen yet; we'll check again next poll
                logger.debug(
                    "Event %s (%s) not yet on-sale (starts %s)",
                    event_id,
                    event.get("name"),
                    start_public,
                )

        await asyncio.sleep(MIN_REQUEST_INTERVAL)
