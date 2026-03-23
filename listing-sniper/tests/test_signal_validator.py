"""Tests for signal validation and deduplication."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.models import Exchange, Signal, SignalSource
from src.signals.signal_validator import SignalValidator


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.is_signal_seen = AsyncMock(return_value=False)
    redis.mark_signal_seen = AsyncMock()
    return redis


@pytest.fixture
def validator(mock_redis):
    return SignalValidator(mock_redis)


class TestSignalValidator:
    @pytest.mark.asyncio
    async def test_valid_signal_passes(self, validator):
        signal = Signal(
            token_symbol="NEWTOKEN",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Binance Will List NewToken (NEWTOKEN)",
        )
        result = await validator.validate(signal)
        assert result is not None
        assert result.validated is True
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_rejects_delist(self, validator):
        signal = Signal(
            token_symbol="OLD",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Binance Will Delist OldToken (OLD)",
        )
        result = await validator.validate(signal)
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_maintenance(self, validator):
        signal = Signal(
            token_symbol="BTC",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Wallet maintenance for Bitcoin (BTC)",
        )
        result = await validator.validate(signal)
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_known_tokens(self, validator):
        for ticker in ["BTC", "ETH", "SOL", "USDT", "BNB"]:
            signal = Signal(
                token_symbol=ticker,
                exchange=Exchange.BINANCE,
                source=SignalSource.API,
                raw_text=f"New listing {ticker}",
            )
            result = await validator.validate(signal)
            assert result is None, f"{ticker} should be rejected"

    @pytest.mark.asyncio
    async def test_deduplication(self, validator, mock_redis):
        signal = Signal(
            token_symbol="NEW",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Will list NEW",
        )
        # First call
        result1 = await validator.validate(signal)
        assert result1 is not None

        # Second call — redis says already seen
        mock_redis.is_signal_seen.return_value = True
        result2 = await validator.validate(signal)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_short_ticker_rejected(self, validator):
        signal = Signal(
            token_symbol="X",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Will list X",
        )
        result = await validator.validate(signal)
        assert result is None

    @pytest.mark.asyncio
    async def test_api_source_higher_confidence(self, validator):
        api_signal = Signal(
            token_symbol="TOKEN1",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Will list TOKEN1",
        )
        twitter_signal = Signal(
            token_symbol="TOKEN2",
            exchange=Exchange.BINANCE,
            source=SignalSource.TWITTER,
            raw_text="Will list TOKEN2",
        )
        r1 = await validator.validate(api_signal)
        r2 = await validator.validate(twitter_signal)
        assert r1 and r2
        assert r1.confidence > r2.confidence

    @pytest.mark.asyncio
    async def test_corroboration_boosts_confidence(self, validator, mock_redis):
        # First signal from API
        sig1 = Signal(
            token_symbol="CORR",
            exchange=Exchange.BINANCE,
            source=SignalSource.API,
            raw_text="Will list CORR",
        )
        await validator.validate(sig1)

        # Second signal from Twitter (different source, but same symbol)
        # Reset dedup to allow second signal through
        mock_redis.is_signal_seen.return_value = False
        sig2 = Signal(
            token_symbol="CORR",
            exchange=Exchange.BYBIT,  # Different exchange so dedup_key differs
            source=SignalSource.TWITTER,
            raw_text="$CORR listing confirmed",
        )
        r2 = await validator.validate(sig2)
        assert r2 is not None
        # Confidence should be boosted due to corroboration
        assert r2.confidence >= 0.80
