"""Tests unitaires pour hedge_fund_bot.py — RiskManager, StateStore, data models."""

import json
import tempfile
import shutil
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from hedge_fund_bot import (
    BotConfig, BotState, BotPosition, BotTrade,
    RiskManager, StateStore,
)


class TestBotConfig(unittest.TestCase):
    """Tests pour les valeurs par defaut de BotConfig."""

    def test_defaults(self):
        c = BotConfig()
        self.assertEqual(c.initial_capital, 1000.0)
        self.assertTrue(c.dry_run)
        self.assertEqual(c.max_positions, 8)
        self.assertAlmostEqual(c.max_position_pct, 0.05)
        self.assertAlmostEqual(c.max_total_exposure_pct, 0.30)
        self.assertAlmostEqual(c.daily_loss_limit_pct, 0.05)
        self.assertAlmostEqual(c.max_drawdown_pct, 0.15)

    def test_custom_values(self):
        c = BotConfig(initial_capital=5000, max_positions=15, dry_run=False)
        self.assertEqual(c.initial_capital, 5000)
        self.assertEqual(c.max_positions, 15)
        self.assertFalse(c.dry_run)


class TestBotState(unittest.TestCase):
    """Tests pour BotState."""

    def test_defaults(self):
        s = BotState()
        self.assertEqual(s.capital, 1000.0)
        self.assertIsInstance(s.positions, dict)
        self.assertIsInstance(s.trades, list)
        self.assertEqual(s.total_pnl, 0.0)
        self.assertEqual(s.iteration, 0)


class TestBotDataclasses(unittest.TestCase):
    """Tests pour BotPosition et BotTrade."""

    def test_bot_position(self):
        p = BotPosition(
            market_id="0xabc", question="Q?", side="YES",
            token_id="tok1", entry_price=0.55, size_usd=50.0,
            shares=90.91, entry_time="2025-01-01T00:00:00",
        )
        self.assertEqual(p.market_id, "0xabc")
        self.assertEqual(p.peak_price, 0.0)  # default
        self.assertEqual(p.unrealized_pnl, 0.0)

    def test_bot_trade(self):
        t = BotTrade(
            market_id="0xabc", question="Q?", side="YES",
            entry_price=0.50, exit_price=0.70,
            size_usd=100, pnl=40, pnl_pct=0.40,
            entry_time="2025-01-01T00:00:00",
            exit_time="2025-01-02T00:00:00",
            reason="take_profit",
        )
        self.assertEqual(t.reason, "take_profit")
        self.assertAlmostEqual(t.pnl, 40)


class TestStateStore(unittest.TestCase):
    """Tests pour la persistence JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.tmpdir, "test_state.json")
        self.store = StateStore(self.state_file)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_load_no_file_returns_default(self):
        state = self.store.load()
        self.assertEqual(state.capital, 1000.0)
        self.assertEqual(state.iteration, 0)

    def test_save_and_load_roundtrip(self):
        state = BotState()
        state.capital = 1234.56
        state.total_pnl = 42.0
        state.iteration = 10
        state.positions = {"m1": {"side": "YES", "size_usd": 50}}
        state.trades = [{"pnl": 10}]
        self.store.save(state)

        loaded = self.store.load()
        self.assertAlmostEqual(loaded.capital, 1234.56)
        self.assertAlmostEqual(loaded.total_pnl, 42.0)
        self.assertEqual(loaded.iteration, 10)
        self.assertIn("m1", loaded.positions)
        self.assertEqual(len(loaded.trades), 1)

    def test_corrupted_json_returns_default(self):
        with open(self.state_file, "w") as f:
            f.write("not valid json{{{")
        state = self.store.load()
        self.assertEqual(state.capital, 1000.0)

    def test_save_limits_trades_to_500(self):
        state = BotState()
        state.trades = [{"pnl": i} for i in range(600)]
        self.store.save(state)

        with open(self.state_file) as f:
            data = json.load(f)
        self.assertEqual(len(data["trades"]), 500)

    def test_save_limits_errors_to_50(self):
        state = BotState()
        state.errors = [{"error": f"e{i}"} for i in range(100)]
        self.store.save(state)

        with open(self.state_file) as f:
            data = json.load(f)
        self.assertEqual(len(data["errors"]), 50)


class TestRiskManager(unittest.TestCase):
    """Tests pour le RiskManager."""

    def setUp(self):
        self.config = BotConfig(initial_capital=1000)
        self.risk = RiskManager(self.config)

    def test_can_open_position_basic(self):
        state = BotState()
        state.capital = 1000
        state.peak_equity = 1000
        can, reason = self.risk.can_open_position(state, 50)
        self.assertTrue(can)
        self.assertEqual(reason, "ok")

    def test_max_positions_reached(self):
        state = BotState()
        state.capital = 1000
        state.positions = {f"m{i}": {"size_usd": 10} for i in range(8)}
        can, reason = self.risk.can_open_position(state, 50)
        self.assertFalse(can)
        self.assertEqual(reason, "max_positions_reached")

    def test_insufficient_capital(self):
        # capital=100 mais exposure deja a 200 => equity=300, max_exposure=90
        # On demande 80$ : passe l'exposure (80 < 90-0? non, 200 deja exposee)
        # Approche : config avec exposure_pct=100% pour ne pas bloquer sur exposure
        config = BotConfig(initial_capital=1000, max_total_exposure_pct=1.0)
        risk = RiskManager(config)
        state = BotState()
        state.capital = 10  # Tres peu de cash restant
        state.peak_equity = 1000
        # equity = 10 + 0 = 10, max_remaining = 10*1.0 - 0 = 10
        # size=9.6 > capital*0.95=9.5 => insufficient_capital
        can, reason = risk.can_open_position(state, 9.6)
        self.assertFalse(can)
        self.assertEqual(reason, "insufficient_capital")

    def test_exposure_limit(self):
        state = BotState()
        state.capital = 500
        state.peak_equity = 1000
        # Positions existantes = 290$ d'exposition (max 30% de equity ~= 237$)
        state.positions = {f"m{i}": {"size_usd": 58} for i in range(5)}
        can, reason = self.risk.can_open_position(state, 50)
        self.assertFalse(can)
        self.assertIn("exposure_limit", reason)

    def test_daily_loss_limit(self):
        state = BotState()
        state.capital = 900
        state.peak_equity = 1000
        state.daily_pnl = -100  # > 5% de equity
        can, reason = self.risk.can_open_position(state, 20)
        self.assertFalse(can)
        self.assertIn("daily_loss_limit", reason)

    def test_max_drawdown_blocks(self):
        state = BotState()
        state.capital = 800
        state.peak_equity = 1000
        # Drawdown = 20% > max 15%
        can, reason = self.risk.can_open_position(state, 20)
        self.assertFalse(can)
        self.assertIn("max_drawdown", reason)

    def test_compute_position_size_scales_with_confidence(self):
        state = BotState()
        state.capital = 1000
        state.peak_equity = 1000
        size_low = self.risk.compute_position_size(state, 0.3)
        size_high = self.risk.compute_position_size(state, 0.9)
        self.assertGreater(size_high, size_low)

    def test_compute_position_size_never_negative(self):
        state = BotState()
        state.capital = 0
        state.peak_equity = 1000
        size = self.risk.compute_position_size(state, 0.5)
        self.assertGreaterEqual(size, 0)

    def test_risk_multiplier_reduces_after_losses(self):
        # 4 pertes consecutives
        for _ in range(4):
            self.risk.record_trade_result(-10)
        mult = self.risk._get_risk_multiplier()
        self.assertLess(mult, 1.0)

    def test_risk_multiplier_resets_after_win(self):
        for _ in range(3):
            self.risk.record_trade_result(-10)
        self.risk.record_trade_result(20)  # Win resets streak
        mult = self.risk._get_risk_multiplier()
        self.assertEqual(mult, 1.0)

    def test_concentration_warning(self):
        state = BotState()
        state.capital = 500
        state.peak_equity = 1000
        # 4 positions YES, 0 NO = 100% concentration
        state.positions = {
            f"m{i}": {"size_usd": 20, "side": "YES"} for i in range(4)
        }
        can, reason = self.risk.can_open_position(state, 20)
        if can:
            self.assertIn("warning", reason)


if __name__ == "__main__":
    unittest.main()
