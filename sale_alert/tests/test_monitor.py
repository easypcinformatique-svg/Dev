"""Tests for the Ticketmaster monitor.

Simulates API responses to verify on-sale detection and alert dispatch.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

import aiohttp
import pytest
from aioresponses import aioresponses

from sale_alert.src.config import AppConfig, EventConfig
from sale_alert.src.monitor import TicketmasterMonitor, DetectedEvent, DISCOVERY_URL
from sale_alert.src.alerts import _format_message

TM_URL_PATTERN = re.compile(r"^https://app\.ticketmaster\.com/discovery/v2/events\.json")


# ── Helpers ──────────────────────────────────────────────────────────

def _make_config(events: list[EventConfig] | None = None) -> AppConfig:
    return AppConfig(
        tm_api_key="TEST_KEY",
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_from_number="",
        alert_phone_number="",
        telegram_bot_token="",
        telegram_chat_id="",
        events=events or [EventConfig(artist="TestArtist")],
        poll_interval_seconds=1,
    )


def _onsale_event(event_id: str = "EVT1", name: str = "Test Concert") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": event_id,
        "name": name,
        "url": "https://www.ticketmaster.fr/event/test",
        "dates": {"start": {"localDate": "2026-06-15"}},
        "sales": {
            "public": {
                "startDateTime": (now - timedelta(hours=1)).isoformat(),
                "endDateTime": (now + timedelta(days=30)).isoformat(),
            }
        },
        "priceRanges": [{"min": 45.0, "max": 90.0, "currency": "EUR"}],
    }


def _future_event(event_id: str = "EVT2") -> dict:
    future = datetime.now(timezone.utc) + timedelta(days=7)
    return {
        "id": event_id,
        "name": "Future Concert",
        "url": "https://www.ticketmaster.fr/event/future",
        "dates": {"start": {"localDate": "2026-09-01"}},
        "sales": {
            "public": {
                "startDateTime": future.isoformat(),
                "endDateTime": (future + timedelta(days=30)).isoformat(),
            }
        },
        "priceRanges": [{"min": 50.0, "max": 100.0, "currency": "EUR"}],
    }


# ── Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detects_onsale_event():
    """Monitor should detect an event that is currently on-sale."""
    detected: list[DetectedEvent] = []

    async def callback(event: DetectedEvent) -> None:
        detected.append(event)

    config = _make_config()
    monitor = TicketmasterMonitor(config, on_sale_callback=callback)

    with aioresponses() as mocked:
        mocked.get(
            TM_URL_PATTERN,
            payload={"_embedded": {"events": [_onsale_event()]}},
        )

        async with aiohttp.ClientSession() as session:
            await monitor._poll_once(session, config.events[0])

    assert len(detected) == 1
    assert detected[0].artist == "TestArtist"
    assert detected[0].event_id == "EVT1"
    assert detected[0].min_price == 45.0


@pytest.mark.asyncio
async def test_ignores_future_event():
    """Monitor should not alert for events not yet on-sale."""
    detected: list[DetectedEvent] = []

    async def callback(event: DetectedEvent) -> None:
        detected.append(event)

    config = _make_config()
    monitor = TicketmasterMonitor(config, on_sale_callback=callback)

    with aioresponses() as mocked:
        mocked.get(
            TM_URL_PATTERN,
            payload={"_embedded": {"events": [_future_event()]}},
        )

        async with aiohttp.ClientSession() as session:
            await monitor._poll_once(session, config.events[0])

    assert len(detected) == 0


@pytest.mark.asyncio
async def test_deduplicates_events():
    """Same event_id should only trigger one alert."""
    detected: list[DetectedEvent] = []

    async def callback(event: DetectedEvent) -> None:
        detected.append(event)

    config = _make_config()
    monitor = TicketmasterMonitor(config, on_sale_callback=callback)

    with aioresponses() as mocked:
        mocked.get(
            TM_URL_PATTERN,
            payload={"_embedded": {"events": [_onsale_event()]}},
        )
        mocked.get(
            TM_URL_PATTERN,
            payload={"_embedded": {"events": [_onsale_event()]}},
        )

        async with aiohttp.ClientSession() as session:
            await monitor._poll_once(session, config.events[0])
            await monitor._poll_once(session, config.events[0])

    assert len(detected) == 1


def test_format_message():
    event = DetectedEvent(
        artist="Orelsan",
        event_id="E1",
        event_name="Orelsan — Civilisation Tour",
        url="https://www.ticketmaster.fr/event/orelsan",
        start_date="2026-06-15",
        min_price=45.0,
        max_price=90.0,
    )
    msg = _format_message(event)
    assert "Orelsan" in msg
    assert "45" in msg
    assert "90" in msg
    assert "ticketmaster.fr" in msg


def test_config_loading():
    """Verify EventConfig.from_dict handles all field types."""
    cfg = EventConfig.from_dict({
        "artist": "Stromae",
        "expected_onsale": "2026-05-15T10:00:00",
        "min_price_eur": 40,
        "max_price_eur": 150,
    })
    assert cfg.artist == "Stromae"
    assert cfg.expected_onsale == datetime(2026, 5, 15, 10, 0, 0)
    assert cfg.min_price_eur == 40
