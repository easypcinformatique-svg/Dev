"""Signal validation, deduplication, and confidence scoring."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.infra.redis_cache import RedisCache
from src.models import Signal, SignalSource

logger = logging.getLogger(__name__)

# Words that indicate this is NOT a new listing
_NEGATIVE_KW = re.compile(
    r"(delist|maintenance|suspend|removal|removed|will remove|margin|futures only)",
    re.IGNORECASE,
)

# Known stablecoins and very established tokens (not interesting for sniping)
_SKIP_TOKENS = frozenset({
    "BTC", "ETH", "USDT", "USDC", "BUSD", "DAI", "TUSD", "SOL",
    "BNB", "XRP", "ADA", "DOGE", "DOT", "MATIC", "AVAX", "LINK",
    "UNI", "ATOM", "LTC", "BCH", "NEAR", "APT", "ARB", "OP",
})

# Source confidence weights
_SOURCE_CONFIDENCE: dict[SignalSource, float] = {
    SignalSource.API: 0.85,
    SignalSource.TWITTER: 0.70,
    SignalSource.WEBSOCKET: 0.90,
    SignalSource.TELEGRAM: 0.50,
    SignalSource.ONCHAIN: 0.40,
}


class SignalValidator:
    """Validates, deduplicates, and scores listing signals."""

    def __init__(self, redis: RedisCache) -> None:
        self._redis = redis
        self._recent_signals: dict[str, list[Signal]] = {}  # symbol -> signals
        self._correlated_symbols: set[str] = set()

    async def validate(self, signal: Signal) -> Optional[Signal]:
        """
        Validate a signal. Returns the enriched signal or None if rejected.

        Steps:
        1. Reject false positives (delistings, maintenance, known tokens)
        2. Deduplicate
        3. Score confidence based on source + corroboration
        """
        # Step 1: Reject obvious false positives
        if _NEGATIVE_KW.search(signal.raw_text):
            logger.debug("Rejected (negative keyword): %s", signal.raw_text[:60])
            return None

        if signal.token_symbol.upper() in _SKIP_TOKENS:
            logger.debug("Rejected (known token): %s", signal.token_symbol)
            return None

        if not signal.token_symbol or len(signal.token_symbol) < 2:
            logger.debug("Rejected (invalid ticker): %s", signal.token_symbol)
            return None

        # Step 2: Deduplication via Redis
        dedup_key = f"{signal.token_symbol}:{signal.exchange.value}"
        if await self._redis.is_signal_seen(dedup_key):
            logger.debug("Deduplicated: %s on %s", signal.token_symbol, signal.exchange.value)
            # Even though deduplicated, track for corroboration
            await self._track_corroboration(signal)
            return None

        await self._redis.mark_signal_seen(dedup_key, ttl=86400)

        # Step 3: Score confidence
        signal.confidence = self._calculate_confidence(signal)

        # Step 4: Track for cross-source corroboration
        await self._track_corroboration(signal)

        # Step 5: Boost confidence if corroborated
        symbol = signal.token_symbol.upper()
        if symbol in self._recent_signals:
            sources = {s.source for s in self._recent_signals[symbol]}
            if len(sources) >= 2:
                signal.confidence = min(0.98, signal.confidence + 0.15)
                logger.info(
                    "Signal corroborated from %d sources: %s (confidence=%.2f)",
                    len(sources),
                    symbol,
                    signal.confidence,
                )

        signal.validated = True
        logger.info(
            "Signal validated: %s on %s (confidence=%.2f, source=%s)",
            signal.token_symbol,
            signal.exchange.value,
            signal.confidence,
            signal.source.value,
        )
        return signal

    def _calculate_confidence(self, signal: Signal) -> float:
        """Calculate confidence score based on source and signal quality."""
        base = _SOURCE_CONFIDENCE.get(signal.source, 0.50)

        # Boost if listing time is specified
        if signal.listing_time:
            base += 0.05

        # Boost if token name is present (not just ticker)
        if signal.token_name and signal.token_name != signal.token_symbol:
            base += 0.03

        # Boost if URL is present (verifiable)
        if signal.url:
            base += 0.02

        return min(0.95, base)

    async def _track_corroboration(self, signal: Signal) -> None:
        """Track signals for cross-source corroboration."""
        symbol = signal.token_symbol.upper()
        if symbol not in self._recent_signals:
            self._recent_signals[symbol] = []

        self._recent_signals[symbol].append(signal)

        # Prune old signals (older than 1 hour)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self._recent_signals[symbol] = [
            s for s in self._recent_signals[symbol] if s.detection_time > cutoff
        ]

        # Clean up symbols with no recent signals
        empty_symbols = [
            s for s, sigs in self._recent_signals.items() if not sigs
        ]
        for s in empty_symbols:
            del self._recent_signals[s]

    async def get_corroboration_count(self, symbol: str) -> int:
        """Get number of independent sources for a symbol."""
        sigs = self._recent_signals.get(symbol.upper(), [])
        return len({s.source for s in sigs})
