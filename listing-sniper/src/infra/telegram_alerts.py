"""Telegram notification bot — sends alerts for signals, trades, errors, and PnL."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aiohttp

from src.config import AppConfig
from src.models import Position, Signal, TradeOrder

logger = logging.getLogger(__name__)


class TelegramAlerter:
    """Non-blocking Telegram alert sender."""

    def __init__(self, config: AppConfig) -> None:
        self._token = config.telegram.bot_token
        self._chat_id = config.telegram.chat_id
        self._enabled = bool(self._token and self._chat_id)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base = f"https://api.telegram.org/bot{self._token}"

    async def start(self) -> None:
        if self._enabled:
            self._session = aiohttp.ClientSession()
            logger.info("Telegram alerter started")
        else:
            logger.warning("Telegram alerter disabled — missing token/chat_id")

    async def stop(self) -> None:
        if self._session:
            await self._session.close()

    async def _send(self, text: str, parse_mode: str = "HTML") -> None:
        if not self._enabled or not self._session:
            logger.debug("Telegram alert (disabled): %s", text[:80])
            return
        try:
            await self._session.post(
                f"{self._base}/sendMessage",
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
        except Exception:
            logger.exception("Failed to send Telegram alert")

    def fire_and_forget(self, text: str) -> None:
        """Schedule alert without awaiting."""
        asyncio.create_task(self._send(text))

    # ── High-level alert helpers ─────────────────────────────

    async def signal_detected(self, signal: Signal) -> None:
        await self._send(
            f"🔔 <b>NEW LISTING SIGNAL</b>\n"
            f"Token: <code>{signal.token_symbol}</code> ({signal.token_name})\n"
            f"Exchange: {signal.exchange.value}\n"
            f"Source: {signal.source.value}\n"
            f"Confidence: {signal.confidence:.0%}\n"
            f"Listing time: {signal.listing_time or 'TBD'}\n"
            f"Raw: {signal.raw_text[:200]}"
        )

    async def trade_executed(self, order: TradeOrder) -> None:
        emoji = "🟢" if order.side.value == "BUY" else "🔴"
        await self._send(
            f"{emoji} <b>TRADE {order.side.value}</b>\n"
            f"Token: <code>{order.token_symbol}</code>\n"
            f"Amount: ${order.amount_usd:.2f} ({order.amount_sol:.4f} SOL)\n"
            f"Price: ${order.price_usd:.8f}\n"
            f"Slippage: {order.slippage_bps}bps\n"
            f"Fees: ${order.fees_usd:.4f}\n"
            f"TX: <code>{order.tx_signature or 'dry_run'}</code>"
        )

    async def position_update(self, pos: Position) -> None:
        pnl_emoji = "📈" if pos.total_pnl_usd >= 0 else "📉"
        await self._send(
            f"{pnl_emoji} <b>POSITION UPDATE</b>\n"
            f"Token: <code>{pos.token_symbol}</code>\n"
            f"Entry: ${pos.entry_price_usd:.8f}\n"
            f"Current: ${pos.current_price_usd:.8f}\n"
            f"PnL: ${pos.total_pnl_usd:.2f} ({pos.unrealized_pnl_pct:+.1f}%)\n"
            f"Status: {pos.status.value}\n"
            f"Hold: {pos.hold_duration_hours:.1f}h"
        )

    async def position_closed(self, pos: Position) -> None:
        emoji = "💰" if pos.total_pnl_usd > 0 else "💸"
        await self._send(
            f"{emoji} <b>POSITION CLOSED</b>\n"
            f"Token: <code>{pos.token_symbol}</code>\n"
            f"Realized PnL: ${pos.realized_pnl_usd:.2f}\n"
            f"Total PnL: ${pos.total_pnl_usd:.2f}\n"
            f"Hold time: {pos.hold_duration_hours:.1f}h"
        )

    async def error_alert(self, module: str, error: str) -> None:
        await self._send(
            f"🚨 <b>ERROR in {module}</b>\n<pre>{error[:500]}</pre>"
        )

    async def daily_summary(
        self,
        date: str,
        trades: int,
        wins: int,
        pnl_usd: float,
        portfolio_usd: float,
    ) -> None:
        wr = (wins / trades * 100) if trades else 0
        await self._send(
            f"📊 <b>DAILY SUMMARY — {date}</b>\n"
            f"Trades: {trades} (Win rate: {wr:.0f}%)\n"
            f"PnL: ${pnl_usd:+.2f}\n"
            f"Portfolio: ${portfolio_usd:.2f}"
        )

    async def circuit_breaker(self, reason: str) -> None:
        await self._send(
            f"🛑 <b>CIRCUIT BREAKER TRIGGERED</b>\n{reason}"
        )

    async def risk_alert(self, message: str) -> None:
        await self._send(f"⚠️ <b>RISK ALERT</b>\n{message}")
