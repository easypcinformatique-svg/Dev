"""Tests unitaires pour trade_logger.py."""

import os
import json
import csv
import tempfile
import shutil
import unittest

from trade_logger import TradeLogger, ClosedTrade, OpenTrade, POLYMARKET_FEE_PCT


class TestTradeLogger(unittest.TestCase):
    """Tests pour la classe TradeLogger."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logger = TradeLogger(
            output_dir=self.tmpdir,
            csv_file="test_trades.csv",
            json_file="test_trades.json",
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    # ------------------------------------------------------------------
    #  LOG ENTRY
    # ------------------------------------------------------------------

    def test_log_entry_returns_trade_id(self):
        tid = self.logger.log_entry(
            market_id="0xabc123",
            token_id="tok_yes",
            question="Will X happen?",
            side="YES",
            entry_price=0.60,
            size_usd=100.0,
            shares=166.67,
            order_id="ORD-001",
        )
        self.assertTrue(tid.startswith("T-"))
        self.assertEqual(tid, "T-000001")

    def test_log_entry_stores_open_trade(self):
        self.logger.log_entry(
            market_id="0xabc123",
            token_id="tok_yes",
            question="Will X happen?",
            side="YES",
            entry_price=0.60,
            size_usd=100.0,
            shares=166.67,
        )
        self.assertIn("0xabc123", self.logger.open_trades)
        t = self.logger.open_trades["0xabc123"]
        self.assertEqual(t.side, "YES")
        self.assertAlmostEqual(t.entry_price, 0.60)

    def test_log_entry_increments_counter(self):
        self.logger.log_entry("m1", "t1", "Q1", "YES", 0.5, 50, 100)
        self.logger.log_entry("m2", "t2", "Q2", "NO", 0.4, 40, 100)
        self.assertEqual(self.logger._trade_counter, 2)

    def test_log_entry_with_custom_time(self):
        self.logger.log_entry(
            market_id="m1", token_id="t1", question="Q",
            side="YES", entry_price=0.5, size_usd=50, shares=100,
            entry_time="2025-06-15T10:30:00",
        )
        t = self.logger.open_trades["m1"]
        self.assertEqual(t.entry_time, "2025-06-15T10:30:00")

    # ------------------------------------------------------------------
    #  LOG EXIT
    # ------------------------------------------------------------------

    def test_log_exit_returns_closed_trade(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        closed = self.logger.log_exit("m1", 0.70, "take_profit")
        self.assertIsInstance(closed, ClosedTrade)
        self.assertEqual(closed.exit_reason, "take_profit")

    def test_log_exit_unknown_market_returns_none(self):
        result = self.logger.log_exit("unknown_market", 0.5, "manual")
        self.assertIsNone(result)

    def test_log_exit_pnl_calculation_yes(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        closed = self.logger.log_exit("m1", 0.70, "take_profit")

        # PnL brut = (0.70 - 0.50) * 200 = 40
        self.assertAlmostEqual(closed.pnl_gross, 40.0, places=2)

        # Frais entree = 100 * 0.02 = 2
        self.assertAlmostEqual(closed.fees_entry, 2.0, places=2)

        # Frais sortie = 200 * 0.70 * 0.02 = 2.8
        self.assertAlmostEqual(closed.fees_exit, 2.8, places=2)

        # PnL net = 40 - 2 - 2.8 = 35.2
        self.assertAlmostEqual(closed.pnl_net, 35.2, places=2)

    def test_log_exit_pnl_calculation_no(self):
        self.logger.log_entry("m1", "t1", "Q", "NO", 0.60, 100, 166.67)
        closed = self.logger.log_exit("m1", 0.40, "take_profit")

        # PnL brut = (0.60 - 0.40) * 166.67 = 33.334
        self.assertAlmostEqual(closed.pnl_gross, 33.334, places=2)

    def test_log_exit_removes_from_open(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        self.logger.log_exit("m1", 0.70, "take_profit")
        self.assertNotIn("m1", self.logger.open_trades)

    def test_log_exit_adds_to_closed(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        self.logger.log_exit("m1", 0.70, "take_profit")
        self.assertEqual(len(self.logger.closed_trades), 1)

    def test_log_exit_custom_time(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        closed = self.logger.log_exit("m1", 0.70, "tp", exit_time="2025-07-01T12:00:00")
        self.assertEqual(closed.exit_time, "2025-07-01T12:00:00")

    # ------------------------------------------------------------------
    #  PERSISTENCE CSV
    # ------------------------------------------------------------------

    def test_csv_created_on_exit(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        self.logger.log_exit("m1", 0.70, "take_profit")
        csv_path = os.path.join(self.tmpdir, "test_trades.csv")
        self.assertTrue(os.path.exists(csv_path))

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["side"], "YES")

    def test_csv_appends_multiple_trades(self):
        for i in range(3):
            self.logger.log_entry(f"m{i}", f"t{i}", "Q", "YES", 0.50, 100, 200)
            self.logger.log_exit(f"m{i}", 0.70, "tp")

        csv_path = os.path.join(self.tmpdir, "test_trades.csv")
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 3)

    # ------------------------------------------------------------------
    #  PERSISTENCE JSON
    # ------------------------------------------------------------------

    def test_json_created_on_entry(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        json_path = os.path.join(self.tmpdir, "test_trades.json")
        self.assertTrue(os.path.exists(json_path))

        with open(json_path) as f:
            data = json.load(f)
        self.assertEqual(len(data["open_trades"]), 1)

    def test_json_reload_preserves_state(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        self.logger.log_exit("m1", 0.70, "tp")
        self.logger.log_entry("m2", "t2", "Q2", "NO", 0.40, 50, 125)

        # Recharger depuis le JSON
        logger2 = TradeLogger(
            output_dir=self.tmpdir,
            csv_file="test_trades.csv",
            json_file="test_trades.json",
        )
        self.assertEqual(len(logger2.closed_trades), 1)
        self.assertIn("m2", logger2.open_trades)

    # ------------------------------------------------------------------
    #  GET STATS
    # ------------------------------------------------------------------

    def test_get_stats_empty(self):
        stats = self.logger.get_stats()
        self.assertEqual(stats["total_trades"], 0)
        self.assertEqual(stats["win_rate"], 0.0)

    def test_get_stats_with_trades(self):
        # Trade gagnant
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        self.logger.log_exit("m1", 0.70, "tp")

        # Trade perdant
        self.logger.log_entry("m2", "t2", "Q", "YES", 0.60, 100, 166.67)
        self.logger.log_exit("m2", 0.40, "sl")

        stats = self.logger.get_stats()
        self.assertEqual(stats["total_trades"], 2)
        self.assertGreater(stats["win_rate"], 0)
        self.assertIn("sharpe_ratio", stats)
        self.assertIn("max_drawdown", stats)
        self.assertIn("profit_factor", stats)
        self.assertIn("total_fees", stats)

    def test_get_stats_profit_factor(self):
        # 2 trades gagnants, 1 perdant
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.40, 100, 250)
        self.logger.log_exit("m1", 0.80, "tp")

        self.logger.log_entry("m2", "t2", "Q", "YES", 0.30, 100, 333.33)
        self.logger.log_exit("m2", 0.60, "tp")

        self.logger.log_entry("m3", "t3", "Q", "YES", 0.70, 100, 142.86)
        self.logger.log_exit("m3", 0.30, "sl")

        stats = self.logger.get_stats()
        self.assertEqual(stats["total_trades"], 3)
        self.assertGreater(stats["profit_factor"], 0)

    # ------------------------------------------------------------------
    #  FEES
    # ------------------------------------------------------------------

    def test_fee_percentage_is_two_percent(self):
        self.assertEqual(POLYMARKET_FEE_PCT, 0.02)

    def test_fees_always_positive(self):
        self.logger.log_entry("m1", "t1", "Q", "YES", 0.50, 100, 200)
        closed = self.logger.log_exit("m1", 0.30, "sl")  # Trade perdant
        self.assertGreater(closed.fees_entry, 0)
        self.assertGreater(closed.fees_exit, 0)
        self.assertGreater(closed.fees_total, 0)


if __name__ == "__main__":
    unittest.main()
