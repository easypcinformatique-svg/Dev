"""Alert channels: Telegram and SMS (Twilio).

Each channel is optional — if credentials are missing it logs a warning
and skips silently.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from sale_alert.src.config import AppConfig
from sale_alert.src.monitor import DetectedEvent

logger = logging.getLogger(__name__)


def _format_message(event: DetectedEvent) -> str:
    price = ""
    if event.min_price is not None:
        price = f" — Prix: {event.min_price}€"
        if event.max_price and event.max_price != event.min_price:
            price = f" — Prix: {event.min_price}–{event.max_price}€"
    return (
        f"🎫 ALERTE {event.artist}\n"
        f"Vente ouverte sur Ticketmaster\n"
        f"{event.event_name} — {event.start_date}{price}\n"
        f"{event.url}"
    )


class AlertEngine:
    """Dispatches alerts over multiple channels concurrently."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    async def send(self, event: DetectedEvent) -> None:
        results = await asyncio.gather(
            self._send_telegram(event),
            self._send_sms(event),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                channel = ["Telegram", "SMS"][i]
                logger.error("Alert failed on %s: %s", channel, result)

    # ── Telegram ─────────────────────────────────────────────────────

    async def _send_telegram(self, event: DetectedEvent) -> None:
        token = self._config.telegram_bot_token
        chat_id = self._config.telegram_chat_id
        if not token or not chat_id:
            logger.debug("Telegram not configured — skipping")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": _format_message(event),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Voir les billets", "url": event.url}]
                ]
            }
            if event.url
            else {},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Telegram API error %d: %s", resp.status, body)
                else:
                    logger.info("Telegram alert sent for %s", event.event_name)

    # ── SMS via Twilio ───────────────────────────────────────────────

    async def _send_sms(self, event: DetectedEvent) -> None:
        sid = self._config.twilio_account_sid
        auth = self._config.twilio_auth_token
        from_num = self._config.twilio_from_number
        to_num = self._config.alert_phone_number
        if not all([sid, auth, from_num, to_num]):
            logger.debug("Twilio not configured — skipping")
            return

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {
            "From": from_num,
            "To": to_num,
            "Body": _format_message(event),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=data,
                auth=aiohttp.BasicAuth(sid, auth),
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    logger.error("Twilio API error %d: %s", resp.status, body)
                else:
                    logger.info("SMS alert sent for %s", event.event_name)
