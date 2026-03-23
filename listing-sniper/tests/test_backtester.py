"""Tests for the backtester."""

import pytest
from src.backtest.backtester import Backtester, BacktestConfig
from src.backtest.data_collector import HistoricalListing


@pytest.fixture
def config():
    return BacktestConfig(initial_capital=10000)


@pytest.fixture
def backtester(config):
    return Backtester(config)


def _make_listing(symbol: str, price: float, price_1h: float, liq: float = 50000) -> HistoricalListing:
    return HistoricalListing(
        token_symbol=symbol,
        token_name=symbol,
        exchange="BINANCE",
        announcement_time="2024-01-01T00:00:00",
        listing_time="2024-01-01T01:00:00",
        price_at_listing=price,
        price_1h_after=price_1h,
        price_4h_after=price_1h * 0.95,
        price_24h_after=price_1h * 0.9,
        liquidity_at_listing=liq,
    )


class TestBacktester:
    def test_profitable_trades(self, backtester):
        listings = [
            _make_listing("WIN1", 1.0, 1.5),  # +50%
            _make_listing("WIN2", 2.0, 3.0),  # +50%
        ]
        result = backtester.run(listings)
        assert result.final_capital > result.initial_capital
        assert result.total_trades == 2
        assert result.wins > 0

    def test_losing_trades(self, backtester):
        listings = [
            _make_listing("LOSS1", 1.0, 0.5),  # -50%
            _make_listing("LOSS2", 2.0, 1.0),  # -50%
        ]
        result = backtester.run(listings)
        assert result.final_capital < result.initial_capital

    def test_skips_low_liquidity(self, backtester):
        listings = [
            _make_listing("LOW", 1.0, 2.0, liq=100),  # Too low
        ]
        result = backtester.run(listings)
        assert result.total_trades == 0

    def test_skips_zero_price(self, backtester):
        listings = [
            _make_listing("ZERO", 0, 0),
        ]
        result = backtester.run(listings)
        assert result.total_trades == 0

    def test_metrics_calculated(self, backtester):
        listings = [
            _make_listing("A", 1.0, 1.3),
            _make_listing("B", 1.0, 0.8),
            _make_listing("C", 1.0, 1.5),
            _make_listing("D", 1.0, 1.2),
        ]
        result = backtester.run(listings)
        assert result.total_trades > 0
        assert 0 <= result.win_rate <= 1
        assert result.max_drawdown_pct >= 0
        # Sharpe ratio should be a real number
        assert isinstance(result.sharpe_ratio, float)

    def test_empty_listings(self, backtester):
        result = backtester.run([])
        assert result.total_trades == 0
        assert result.final_capital == result.initial_capital

    def test_report_generation(self, backtester):
        listings = [_make_listing("REP", 1.0, 1.5)]
        result = backtester.run(listings)
        report = backtester.print_report(result)
        assert "BACKTEST REPORT" in report
        assert "Win Rate" in report
