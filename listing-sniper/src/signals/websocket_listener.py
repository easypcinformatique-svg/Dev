"""WebSocket listener — detects new trading pairs appearing on exchange streams."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Optional

import aiohttp

from src.config import AppConfig
from src.models import Exchange, Signal, SignalSource

logger = logging.getLogger(__name__)


class ExchangeWebSocketListener:
    """Monitors exchange WebSocket streams for new symbol appearances."""

    # Public WebSocket endpoints
    _WS_URLS = {
        Exchange.BINANCE: "wss://stream.binance.com:9443/ws/!ticker@arr",
        Exchange.BYBIT: "wss://stream.bybit.com/v5/public/spot",
    }

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._known_symbols: dict[Exchange, set[str]] = {
            ex: set() for ex in Exchange
        }
        self._initialized: dict[Exchange, bool] = {ex: False for ex in Exchange}
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._running = True
        # Pre-populate known symbols from REST
        await self._init_known_symbols()
        logger.info("WebSocketListener started")

    async def stop(self) -> None:
        self._running = False
        if self._session:
            await self._session.close()

    async def _init_known_symbols(self) -> None:
        """Fetch current trading pairs from REST APIs to establish baseline."""
        assert self._session

        # Binance
        try:
            async with self._session.get(
                "https://api.binance.com/api/v3/exchangeInfo",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for sym in data.get("symbols", []):
                        self._known_symbols[Exchange.BINANCE].add(sym["symbol"])
                    self._initialized[Exchange.BINANCE] = True
                    logger.info(
                        "Binance: loaded %d known symbols",
                        len(self._known_symbols[Exchange.BINANCE]),
                    )
        except Exception:
            logger.warning("Failed to init Binance symbols")

        # Bybit
        try:
            async with self._session.get(
                "https://api.bybit.com/v5/market/instruments-info",
                params={"category": "spot", "limit": 1000},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("result", {}).get("list", []):
                        self._known_symbols[Exchange.BYBIT].add(item["symbol"])
                    self._initialized[Exchange.BYBIT] = True
                    logger.info(
                        "Bybit: loaded %d known symbols",
                        len(self._known_symbols[Exchange.BYBIT]),
                    )
        except Exception:
            logger.warning("Failed to init Bybit symbols")

    async def listen(self) -> AsyncIterator[Signal]:
        """Yield signals when new symbols are detected on WebSocket streams."""
        tasks = [
            asyncio.create_task(self._collect_signals(exchange, url))
            for exchange, url in self._WS_URLS.items()
            if self._initialized.get(exchange, False)
        ]
        queue: asyncio.Queue[Signal] = asyncio.Queue()

        async def _feed(exchange: Exchange, url: str) -> None:
            async for sig in self._monitor_exchange(exchange, url):
                await queue.put(sig)

        for exchange, url in self._WS_URLS.items():
            if self._initialized.get(exchange):
                asyncio.create_task(_feed(exchange, url))

        while self._running:
            try:
                sig = await asyncio.wait_for(queue.get(), timeout=5.0)
                yield sig
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _collect_signals(self, exchange: Exchange, url: str) -> list[Signal]:
        """Not used directly — see _monitor_exchange."""
        return []

    async def _monitor_exchange(
        self, exchange: Exchange, url: str
    ) -> AsyncIterator[Signal]:
        """Connect to exchange WS and detect new symbols."""
        assert self._session
        while self._running:
            try:
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    # Bybit requires subscription
                    if exchange == Exchange.BYBIT:
                        await ws.send_json({
                            "op": "subscribe",
                            "args": ["tickers.BTCUSDT"],  # Minimal sub
                        })

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            new_syms = self._extract_new_symbols(exchange, data)
                            for sym in new_syms:
                                ticker = self._symbol_to_ticker(sym)
                                if ticker:
                                    yield Signal(
                                        token_symbol=ticker,
                                        exchange=exchange,
                                        source=SignalSource.WEBSOCKET,
                                        confidence=0.90,
                                        raw_text=f"New symbol detected: {sym}",
                                    )
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("WebSocket error for %s", exchange.value)
                await asyncio.sleep(5)

    def _extract_new_symbols(
        self, exchange: Exchange, data: dict | list
    ) -> list[str]:
        """Check WebSocket data for new trading pairs."""
        new_symbols: list[str] = []
        known = self._known_symbols[exchange]

        if exchange == Exchange.BINANCE and isinstance(data, list):
            for ticker in data:
                sym = ticker.get("s", "")
                if sym and sym not in known:
                    known.add(sym)
                    new_symbols.append(sym)
                    logger.info("New Binance symbol: %s", sym)

        elif exchange == Exchange.BYBIT and isinstance(data, dict):
            topic = data.get("topic", "")
            if "tickers" in topic:
                sym = data.get("data", {}).get("symbol", "")
                if sym and sym not in known:
                    known.add(sym)
                    new_symbols.append(sym)
                    logger.info("New Bybit symbol: %s", sym)

        return new_symbols

    @staticmethod
    def _symbol_to_ticker(symbol: str) -> str:
        """Convert trading pair to base ticker, e.g. SOLUSDT -> SOL."""
        for quote in ("USDT", "USDC", "BUSD", "BTC", "ETH"):
            if symbol.endswith(quote):
                return symbol[: -len(quote)]
        return ""
