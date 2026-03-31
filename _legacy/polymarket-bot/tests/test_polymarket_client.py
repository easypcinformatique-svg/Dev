"""Tests unitaires pour polymarket_client.py."""

import unittest
from unittest.mock import patch, MagicMock

from polymarket_client import PolymarketClient, _with_retry, MAX_RETRIES


class TestWithRetry(unittest.TestCase):
    """Tests pour la fonction _with_retry."""

    def test_success_first_try(self):
        func = MagicMock(return_value="ok")
        result = _with_retry(func, "arg1", key="val")
        self.assertEqual(result, "ok")
        func.assert_called_once_with("arg1", key="val")

    @patch("polymarket_client.time.sleep")
    def test_retries_on_failure(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("err1"), Exception("err2"), "ok"])
        result = _with_retry(func, "arg1")
        self.assertEqual(result, "ok")
        self.assertEqual(func.call_count, 3)

    @patch("polymarket_client.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        func = MagicMock(side_effect=Exception("always fails"))
        with self.assertRaises(Exception) as ctx:
            _with_retry(func)
        self.assertIn("always fails", str(ctx.exception))
        self.assertEqual(func.call_count, MAX_RETRIES)

    @patch("polymarket_client.time.sleep")
    def test_backoff_sleep_called(self, mock_sleep):
        func = MagicMock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        _with_retry(func)
        # Devrait avoir dormi 2 fois (avant retry 2 et 3)
        self.assertEqual(mock_sleep.call_count, 2)


class TestPolymarketClientDryRun(unittest.TestCase):
    """Tests pour le mode DRY_RUN."""

    @patch("polymarket_client.BaseReadClient")
    def setUp(self, mock_read_client):
        self.mock_read = mock_read_client.return_value
        self.client = PolymarketClient(private_key="", dry_run=True)

    def test_dry_run_is_default(self):
        self.assertTrue(self.client.dry_run)

    def test_trading_client_none_in_dry_run(self):
        self.assertIsNone(self.client.trading_client)

    def test_place_order_dry_returns_dict(self):
        result = self.client.place_order(
            token_id="tok123",
            side="BUY",
            size_usd=50.0,
            price=0.60,
        )
        self.assertIn("orderID", result)
        self.assertTrue(result["orderID"].startswith("DRY-"))
        self.assertTrue(result["dry_run"])

    def test_close_position_dry_returns_dict(self):
        result = self.client.close_position(token_id="tok123", shares=100.0)
        self.assertIn("orderID", result)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["side"], "SELL")

    def test_dry_order_counter_increments(self):
        self.client.place_order("t1", "BUY", 50, 0.5)
        self.client.place_order("t2", "BUY", 50, 0.5)
        self.client.close_position("t3", 100)
        self.assertEqual(self.client._dry_order_counter, 3)

    def test_get_markets_calls_read_client(self):
        self.mock_read.get_all_active_markets.return_value = ["market1", "market2"]
        result = self.client.get_markets(limit=50)
        self.assertEqual(result, ["market1", "market2"])

    def test_get_midpoint_calls_read_client(self):
        self.mock_read.get_midpoint.return_value = 0.55
        result = self.client.get_midpoint("tok123")
        self.assertEqual(result, 0.55)

    def test_get_spread_calls_read_client(self):
        self.mock_read.get_spread.return_value = {"spread": 0.03}
        result = self.client.get_spread("tok123")
        self.assertEqual(result["spread"], 0.03)

    def test_get_position_without_trading_client(self):
        result = self.client.get_position("market_abc")
        self.assertEqual(result, {"trades": []})


class TestPolymarketClientLive(unittest.TestCase):
    """Tests pour le mode LIVE (mock du trading client)."""

    @patch("polymarket_client.BaseTradingClient")
    @patch("polymarket_client.BaseReadClient")
    def test_live_mode_init(self, mock_read, mock_trading):
        client = PolymarketClient(private_key="0xfake_key", dry_run=False)
        self.assertFalse(client.dry_run)
        self.assertIsNotNone(client.trading_client)

    @patch("polymarket_client.BaseTradingClient")
    @patch("polymarket_client.BaseReadClient")
    def test_live_fallback_to_dry_on_error(self, mock_read, mock_trading):
        mock_trading.side_effect = Exception("auth failed")
        client = PolymarketClient(private_key="0xbad", dry_run=False)
        self.assertTrue(client.dry_run)  # Fallback to dry run


if __name__ == "__main__":
    unittest.main()
