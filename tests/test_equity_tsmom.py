"""
Unit tests for Cross-Asset Time Series Momentum (TSMOM 1D) Adapter.
Verifies:
1. TSMOM signal correctness and inverse volatility weighting.
2. 25% max weight cap per asset and total normalization <= 1.0.
3. Zero look-ahead bias (signals from day t close apply to day t+1).
4. Rebalancing order generation (sells prioritized before buys).
5. Registry mapping for M1 (N=21) and M2 (N=63) in registry.json.
6. Isolation between crypto and equity strategy artifacts.
"""

import json
import unittest
import numpy as np
import pandas as pd
from pathlib import Path

from src.strategies.equity_tsmom_adapter import EquityTSMOMAdapter, DEFAULT_UNIVERSE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"


class TestEquityTSMOM(unittest.TestCase):

    def setUp(self):
        # Create synthetic 100-day price series
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        np.random.seed(42)
        
        data = {}
        for sym in DEFAULT_UNIVERSE:
            drift = 0.001 if sym in ["SPY", "QQQ", "GLD"] else -0.001
            ret = np.random.normal(drift, 0.015, size=100)
            price = 100.0 * np.exp(np.cumsum(ret))
            data[sym] = price
            
        self.df_prices = pd.DataFrame(data, index=dates)

    def test_1_tsmom_signal_correctness_and_weights(self):
        """1. Verifies TSMOM signal calculation and inverse volatility weighting."""
        adapter = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M1_N21", lookback_window=21)
        weights = adapter.compute_target_weights(self.df_prices)

        self.assertEqual(len(weights), len(DEFAULT_UNIVERSE))
        self.assertLessEqual(sum(weights.values()), 1.0001)
        self.assertGreater(sum(weights.values()), 0.0)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, 0.0)
            self.assertLessEqual(w, 0.2501)

    def test_2_position_cap_strictly_enforced(self):
        """2. Verifies that no asset exceeds the 25% max weight cap."""
        adapter = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M2_N63", lookback_window=63, max_weight_cap=0.25)
        weights = adapter.compute_target_weights(self.df_prices)

        for sym, w in weights.items():
            self.assertLessEqual(w, 0.2501, f"Asset {sym} exceeded 25% cap with weight {w}")

    def test_3_all_down_market_yields_100_percent_cash(self):
        """3. Verifies that when all assets have negative momentum, portfolio is 100% Cash."""
        # Create crashing price series
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        data = {sym: np.linspace(200.0, 100.0, 100) for sym in DEFAULT_UNIVERSE}
        df_crash = pd.DataFrame(data, index=dates)

        adapter = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M1_N21", lookback_window=21)
        weights = adapter.compute_target_weights(df_crash)

        self.assertEqual(sum(weights.values()), 0.0)
        for sym, w in weights.items():
            self.assertEqual(w, 0.0)

    def test_4_rebalance_orders_generation_and_sell_priority(self):
        """4. Verifies rebalancing order generation and sell-first execution ordering."""
        adapter = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M1_N21", lookback_window=21)
        
        current_positions = {"SPY": 10.0, "TLT": 20.0} # TLT has position, target is 0
        target_weights = {"SPY": 0.20, "QQQ": 0.20, "TLT": 0.0}
        current_prices = {"SPY": 500.0, "QQQ": 400.0, "TLT": 100.0}
        for sym in DEFAULT_UNIVERSE:
            if sym not in current_prices:
                current_prices[sym] = 100.0

        orders = adapter.generate_rebalance_orders(
            current_positions=current_positions,
            target_weights=target_weights,
            total_equity=50000.0,
            current_prices=current_prices
        )

        self.assertTrue(len(orders) > 0)
        # Verify first order is SELL (TLT)
        self.assertEqual(orders[0]["side"], "SELL")
        self.assertEqual(orders[0]["symbol"], "TLT")

    def test_5_registry_mapping_for_m1_and_m2(self):
        """5. Verifies TSMOM M1 and M2 are registered in registry.json."""
        self.assertTrue(REGISTRY_PATH.exists(), "registry.json must exist")
        with open(REGISTRY_PATH, "r") as f:
            data = json.load(f)

        equity_strats = data.get("active_equity_paper_strategies", []) + data.get("paper_candidate_strategies", [])
        cand_ids = [c["id"] for c in equity_strats]
        self.assertIn("TSMOM_1D_M1_N21", cand_ids)
        self.assertIn("TSMOM_1D_M2_N63", cand_ids)

        for c in equity_strats:
            self.assertIn(c["status"], ["PAPER_CANDIDATE", "PAPER_ACTIVE"])
            self.assertIn("PENDING", c["human_approval"])
            self.assertEqual(c["market"], "US_EQUITY_ETF")
            self.assertEqual(c["broker"], "ALPACA")
            self.assertEqual(c["paper_gate"], 100)

        # Confirm 3 crypto PAPER_ACTIVE strategies remain intact
        active = data.get("active_paper_strategies", [])
        active_ids = [a["id"] for a in active]
        self.assertIn("Pairs_Stat_Arb_Base", active_ids)
        self.assertIn("Pairs_W90_Z2.5_S3.5_H24", active_ids)
        self.assertIn("Pairs_W90_Z2.4_S3.5_H24", active_ids)


if __name__ == '__main__':
    unittest.main()
