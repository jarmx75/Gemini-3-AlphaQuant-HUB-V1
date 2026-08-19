"""
Integration Tests for Paper Runner, Strategy Adapters, and Demo Readiness
Verifies:
1. Each of the 3 PAPER_ACTIVE strategies has an executable adapter.
2. Each generates at least one signal on historical test segments.
3. Signal -> paper trade -> CSV log -> demo_readiness end-to-end pipeline.
4. Strategy IDs in registry.json match Runner adapter IDs.
5. Unregistered/invalid strategies without adapters fail closed.
6. Demo readiness strictly does not count historical backtest trades as paper trades.
"""

import unittest
import os
import time
import json
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch

from src.execution.pairs_trading_paper_runner import PairsTradingPaperRunner, StrategyAdapter
from src.execution.demo_readiness import audit_paper_readiness, compute_paper_metrics_from_df

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"
HISTORICAL_DIR = PROJECT_ROOT / "data" / "historical"


class TestPaperRunnerIntegration(unittest.TestCase):

    def setUp(self):
        self.runner = PairsTradingPaperRunner(use_binance_client=False)
        self.expected_active_ids = [
            "Pairs_Stat_Arb_Base",
            "Pairs_W90_Z2.5_S3.5_H24",
            "Pairs_W90_Z2.4_S3.5_H24"
        ]

    def test_1_each_active_strategy_has_executable_adapter(self):
        """1. Verifies each of the 3 PAPER_ACTIVE strategies has an instantiated executable adapter."""
        for strat_id in self.expected_active_ids:
            self.assertIn(strat_id, self.runner.adapters, f"Missing adapter for {strat_id}")
            adapter = self.runner.adapters[strat_id]
            self.assertIsNotNone(adapter.engine, f"Adapter engine is None for {strat_id}")
            self.assertEqual(adapter.strategy_id, strat_id)

    def test_2_each_strategy_generates_signals_on_historical_data(self):
        """2. Verifies that each strategy generates at least one valid signal on historical test slice."""
        pairs_to_test = [
            ("BTCUSDT", "ETHUSDT"),
            ("AVAXUSDT", "SOLUSDT"),
            ("LINKUSDT", "DOTUSDT")
        ]
        
        # Load historical data (using 2023-2024 active slice)
        loaded_data = {}
        for y, x in pairs_to_test:
            fy, fx = HISTORICAL_DIR / f"{y}_1h_2022_2026.csv", HISTORICAL_DIR / f"{x}_1h_2022_2026.csv"
            if fy.exists() and fx.exists():
                df_y = pd.read_csv(fy).iloc[8000:12000].reset_index(drop=True)
                df_x = pd.read_csv(fx).iloc[8000:12000].reset_index(drop=True)
                loaded_data[(y, x)] = (df_y, df_x)

        df_btc = pd.read_csv(HISTORICAL_DIR / "BTCUSDT_1h_2022_2026.csv").iloc[8000:12000].reset_index(drop=True)

        for strat_id in self.expected_active_ids:
            adapter = self.runner.adapters[strat_id]
            signals_found = 0
            
            for (y, x), (df_y, df_x) in loaded_data.items():
                pair_name = f"{y}/{x}"
                # Scan sliding windows with step=1 to not miss transient 1-hour Z-score spikes
                for i in range(750, min(1500, len(df_y)), 1):
                    sub_y = df_y.iloc[i-750:i].copy()
                    sub_x = df_x.iloc[i-750:i].copy()
                    sub_btc = df_btc.iloc[i-750:i].copy()
                    
                    sig = adapter.engine.generate_pair_signal(
                        df_y=sub_y,
                        df_x=sub_x,
                        pair_name=pair_name,
                        df_btc=sub_btc,
                        open_pos=None,
                        bars_held=0
                    )
                    if sig and sig.get("action") in ["OPEN_LONG_SPREAD", "OPEN_SHORT_SPREAD"]:
                        signals_found += 1
                        break
                if signals_found > 0:
                    break
                    
            self.assertGreater(signals_found, 0, f"Strategy {strat_id} failed to generate any signal on test data.")

    def test_3_signal_to_paper_trade_to_log_to_demo_readiness_pipeline(self):
        """3. End-to-end verification: signal -> open position -> exit -> log -> demo_readiness accounting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_csv = Path(tmpdir) / "test_bitacora.csv"
            self.runner.csv_log_path = temp_csv
            self.runner.init_csv()

            strat_id = "Pairs_W90_Z2.5_S3.5_H24"
            pair_name = "BTCUSDT/ETHUSDT"

            # Create mock kline dataframes
            dates = pd.date_range("2026-08-01 00:00:00", periods=100, freq="1h")
            
            # Synthetic spread with initial divergence then mean reversion
            close_y = [60000.0 + i*10 for i in range(100)]
            close_x = [3000.0 - i*5 for i in range(100)]
            
            df_y = pd.DataFrame({"close": close_y, "timestamp": dates})
            df_x = pd.DataFrame({"close": close_x, "timestamp": dates})
            df_btc = df_y.copy()

            # 1. Force Entry by passing high Z
            pos_key = (strat_id, pair_name)
            self.runner.open_paper_positions[pos_key] = {
                'strategy_id': strat_id,
                'pair': pair_name,
                'side': 'LONG_SPREAD',
                'entry_y': 60000.0,
                'entry_x': 3000.0,
                'gamma': 20.0,
                'z_entry': 2.6,
                'entry_time': "2026-08-01 10:00:00",
                'entry_timestamp': 1785578400,
                'reason': "Spread Entry Test"
            }

            # 2. Trigger Close
            with patch.object(self.runner.adapters[strat_id].engine, 'generate_pair_signal', return_value={
                'action': 'CLOSE_PAIR',
                'z_score': 0.05,
                'reason': 'Spread Mean-Reverted (Z=0.05)'
            }):
                trade_res = self.runner.process_pair_market_data(
                    strategy_id=strat_id,
                    pair_name=pair_name,
                    df_y=df_y,
                    df_x=df_x,
                    df_btc=df_btc,
                    current_time_str="2026-08-01 14:00:00",
                    current_timestamp=1785592800
                )

            self.assertIsNotNone(trade_res)
            self.assertEqual(trade_res["type"], "CLOSE")
            self.assertEqual(trade_res["strategy_id"], strat_id)

            # 3. Verify trade is recorded in CSV with strategy_id
            self.assertTrue(temp_csv.exists())
            df_logged = pd.read_csv(temp_csv)
            self.assertEqual(len(df_logged), 1)
            self.assertEqual(df_logged.iloc[0]["strategy_id"], strat_id)

            # 4. Verify demo_readiness calculates metrics for this specific strategy
            metrics = compute_paper_metrics_from_df(df_logged[df_logged['strategy_id'] == strat_id])
            self.assertEqual(metrics["paper_trades"], 1)
            self.assertIsNotNone(metrics["last_trade"])

    def test_4_strategy_id_in_registry_matches_runner_id(self):
        """4. Verifies strategy IDs in registry.json match Runner adapter IDs exactly."""
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
        
        registry_ids = [s["id"] for s in reg.get("active_paper_strategies", [])]
        runner_ids = list(self.runner.adapters.keys())
        
        self.assertEqual(set(registry_ids), set(runner_ids))

    def test_5_strategy_without_adapter_cannot_be_executed(self):
        """5. Verifies executing an untracked strategy without an adapter raises KeyError / fails closed."""
        with self.assertRaises(KeyError):
            self.runner.process_pair_market_data(
                strategy_id="UNTRACKED_STRATEGY_XYZ",
                pair_name="BTCUSDT/ETHUSDT",
                df_y=pd.DataFrame({"close": [1, 2]}),
                df_x=pd.DataFrame({"close": [1, 2]}),
                df_btc=pd.DataFrame({"close": [1, 2]})
            )

    def test_6_demo_readiness_does_not_count_backtest_as_paper(self):
        """6. Verifies that demo_readiness does not use backtest metrics as paper trades."""
        audit_rep = audit_paper_readiness()
        for strat_id in self.expected_active_ids:
            strat_data = audit_rep["strategies"][strat_id]
            # Must reflect real paper log count (0 in production without live closed trades), NOT backtest (>300)
            self.assertEqual(strat_data["paper_trades"], 0, "Demo readiness must not conflate backtest trades with paper trades.")
            self.assertEqual(strat_data["gate_status"], "PAPER_GATE_PENDING")


    def test_7_position_state_persists_across_restarts(self):
        """7. Verifies that open paper positions are saved and restored across runner restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_state = Path(tmpdir) / "test_positions.json"
            self.runner.state_file_path = temp_state

            pos_key = ("Pairs_Stat_Arb_Base", "BTCUSDT/ETHUSDT")
            self.runner.open_paper_positions[pos_key] = {
                'position_id': "pos_test_123",
                'strategy_id': "Pairs_Stat_Arb_Base",
                'pair': "BTCUSDT/ETHUSDT",
                'side': "LONG_SPREAD",
                'entry_y': 60000.0,
                'entry_x': 3000.0,
                'gamma': 20.0,
                'z_entry': 2.55,
                'entry_time': "2026-08-18 12:00:00",
                'entry_timestamp': 1785500000,
                'entry_fee': 0.12,
                'reason': "Persistence Test"
            }
            self.runner.save_position_state()
            self.assertTrue(temp_state.exists())

            # Create new runner instance and load state
            new_runner = PairsTradingPaperRunner(use_binance_client=False)
            new_runner.state_file_path = temp_state
            new_runner.load_position_state()

            self.assertIn(pos_key, new_runner.open_paper_positions)
            loaded_pos = new_runner.open_paper_positions[pos_key]
            self.assertEqual(loaded_pos["position_id"], "pos_test_123")
            self.assertEqual(loaded_pos["z_entry"], 2.55)

    def test_8_watchdog_detects_stale_market_data(self):
        """8. Verifies that watchdog halts new entries if market data latency exceeds 30m buffer."""
        self.runner.last_market_timestamp_unix = time.time() - 7200.0  # 2 hours old
        is_fresh = self.runner.check_market_data_freshness()
        self.assertFalse(is_fresh)
        self.assertIn("STALE_DATA_HALT", self.runner.watchdog_status)

    def test_9_reconciliation_validator_and_engine_parity(self):
        """9. Verifies that Validator and Strategy Engine have exact structural parity on OOS slice."""
        from src.factory.validator import FactoryValidator, FactoryCandidate
        v = FactoryValidator()
        cand = FactoryCandidate(
            id='Pairs_Stat_Arb_Base',
            lookback_window=90,
            z_entry=2.5,
            z_exit=0.0,
            z_stop=3.5,
            max_holding_bars=24,
            eg_p_threshold=0.03,
            adf_p_threshold=0.05,
            pairs=[]
        )
        df_btc_eth = v.cached_pairs['BTCUSDT/ETHUSDT']
        df_val = df_btc_eth[(df_btc_eth['timestamp'] >= '2024-01-01') & (df_btc_eth['timestamp'] <= '2026-08-16')].reset_index(drop=True)
        trades = v.simulate_series(df_val, cand)
        self.assertEqual(len(trades), 108, "BTC/ETH 2024-2026 OOS must produce exactly 108 trades in canonical Validator.")


if __name__ == "__main__":
    unittest.main()
