"""
Unit Tests for Paper Gate Progress Monitor
Verifica:
1. Contador solo incluye CLOSED trades (OPEN no cuenta).
2. Backtest nunca cuenta como paper.
3. Estrategia desconocida no cuenta.
4. 100 trades cambia estado exactamente a PAPER_GATE_READY.
5. Detección de banderas de anomalía (PF < 0.80, DD > 15%).
6. Cálculo de solapamiento (portfolio overlap).
7. Invariantes de seguridad (APPROVED=false, DEMO_ORDERS=0, REAL_ORDERS=0).
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.execution.paper_gate_monitor import PaperGateMonitor


class TestPaperGateMonitor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        self.reg_file = self.base_path / "registry.json"
        self.bitacora_file = self.base_path / "bitacora.csv"
        self.health_file = self.base_path / "health.json"
        self.out_json = self.base_path / "paper_gate_progress.json"
        self.out_md = self.base_path / "PAPER_GATE_PROGRESS.md"

        # Mock active registry
        mock_registry = {
            "active_paper_strategies": [
                {
                    "id": "Pairs_Stat_Arb_Base",
                    "family": "MEAN_REVERSION_1H",
                    "status": "PAPER_ACTIVE",
                    "promoted_at": "2026-08-16 22:00:00",
                    "metrics": {"val_trades": 313, "val_pf": 1.60}
                },
                {
                    "id": "Pairs_W90_Z2.5_S3.5_H24",
                    "family": "MEAN_REVERSION_1H",
                    "status": "PAPER_ACTIVE",
                    "promoted_at": "2026-08-17 14:32:09",
                    "metrics": {"val_trades": 304, "val_pf": 1.37}
                },
                {
                    "id": "Pairs_W90_Z2.4_S3.5_H24",
                    "family": "MEAN_REVERSION_1H",
                    "status": "PAPER_ACTIVE",
                    "promoted_at": "2026-08-17 14:32:29",
                    "metrics": {"val_trades": 317, "val_pf": 1.34}
                }
            ],
            "human_approved_real_strategies": []
        }
        with open(self.reg_file, "w", encoding="utf-8") as f:
            json.dump(mock_registry, f)

        # Mock runner health
        mock_health = {
            "status": "RUNNING_FORWARD_PAPER",
            "last_signal_by_strategy": {
                "Pairs_Stat_Arb_Base": "Waiting for signal",
                "Pairs_W90_Z2.5_S3.5_H24": "Waiting for signal",
                "Pairs_W90_Z2.4_S3.5_H24": "Waiting for signal"
            }
        }
        with open(self.health_file, "w", encoding="utf-8") as f:
            json.dump(mock_health, f)

        self.monitor = PaperGateMonitor(
            registry_path=self.reg_file,
            bitacora_path=self.bitacora_file,
            runner_health_path=self.health_file,
            output_json_path=self.out_json,
            output_md_path=self.out_md,
            gate_target_trades=100
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_1_closed_trades_only_counted_and_open_ignored(self):
        """1. Verifies that OPEN actions do not increase trade counter, only CLOSE."""
        df_data = pd.DataFrame([
            {"timestamp": "2026-08-18 10:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "pos_1", "holding_bars": 0},
            {"timestamp": "2026-08-18 12:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "pos_2", "holding_bars": 0},
            {"timestamp": "2026-08-18 15:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 15.5, "fees": 0.12, "position_id": "pos_1", "holding_bars": 5}
        ])
        df_data.to_csv(self.bitacora_file, index=False)

        res = self.monitor.run_monitor()
        strat_base = next(s for s in res["strategies_progress"] if s["strategy_id"] == "Pairs_Stat_Arb_Base")
        self.assertEqual(strat_base["closed_paper_trades"], 1)
        self.assertEqual(strat_base["remaining_trades"], 99)
        self.assertEqual(strat_base["progress_pct"], 1.0)
        self.assertEqual(strat_base["paper_PnL"], 15.5)

    def test_2_backtest_trades_never_counted(self):
        """2. Verifies that backtest metrics (e.g. 313 val_trades) are never counted towards paper trades."""
        # Empty bitacora
        pd.DataFrame(columns=["timestamp", "strategy_id", "pair", "action", "pnl", "fees"]).to_csv(self.bitacora_file, index=False)
        res = self.monitor.run_monitor()

        for s in res["strategies_progress"]:
            self.assertEqual(s["closed_paper_trades"], 0)
            self.assertEqual(s["remaining_trades"], 100)
            self.assertEqual(s["progress_pct"], 0.0)

    def test_3_unknown_strategy_ignored(self):
        """3. Verifies that trades from unregistered/unknown strategies are ignored."""
        df_data = pd.DataFrame([
            {"timestamp": "2026-08-18 10:00:00", "strategy_id": "Unknown_Strategy_999", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 100.0, "fees": 0.12, "position_id": "pos_u", "holding_bars": 3},
            {"timestamp": "2026-08-18 11:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 5.0, "fees": 0.12, "position_id": "pos_b", "holding_bars": 2}
        ])
        df_data.to_csv(self.bitacora_file, index=False)

        res = self.monitor.run_monitor()
        strat_ids = [s["strategy_id"] for s in res["strategies_progress"]]
        self.assertNotIn("Unknown_Strategy_999", strat_ids)
        strat_base = next(s for s in res["strategies_progress"] if s["strategy_id"] == "Pairs_Stat_Arb_Base")
        self.assertEqual(strat_base["closed_paper_trades"], 1)

    def test_4_exactly_100_trades_triggers_paper_gate_ready(self):
        """4. Verifies that state transitions to PAPER_GATE_READY strictly at >= 100 closed trades."""
        # 99 trades -> PAPER_ACTIVE
        trades_99 = [
            {"timestamp": f"2026-08-18 10:{i:02d}:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 2.0, "fees": 0.12, "position_id": f"pos_{i}", "holding_bars": 2}
            for i in range(99)
        ]
        pd.DataFrame(trades_99).to_csv(self.bitacora_file, index=False)
        res_99 = self.monitor.run_monitor()
        strat_99 = next(s for s in res_99["strategies_progress"] if s["strategy_id"] == "Pairs_Stat_Arb_Base")
        self.assertEqual(strat_99["closed_paper_trades"], 99)
        self.assertEqual(strat_99["gate_status"], "PAPER_ACTIVE")

        # 100 trades -> PAPER_GATE_READY
        trades_100 = trades_99 + [
            {"timestamp": "2026-08-18 12:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 3.5, "fees": 0.12, "position_id": "pos_100", "holding_bars": 4}
        ]
        pd.DataFrame(trades_100).to_csv(self.bitacora_file, index=False)
        res_100 = self.monitor.run_monitor()
        strat_100 = next(s for s in res_100["strategies_progress"] if s["strategy_id"] == "Pairs_Stat_Arb_Base")
        self.assertEqual(strat_100["closed_paper_trades"], 100)
        self.assertEqual(strat_100["remaining_trades"], 0)
        self.assertEqual(strat_100["progress_pct"], 100.0)
        self.assertEqual(strat_100["gate_status"], "PAPER_GATE_READY")

    def test_5_anomaly_detection_flags(self):
        """5. Verifies that anomaly flags trigger warnings for low PF or excessive DD."""
        # 25 trades with 22 losses and 3 small wins -> PF < 0.80
        bad_trades = []
        for i in range(22):
            bad_trades.append({"timestamp": f"2026-08-18 10:{i:02d}:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": -50.0, "fees": 0.12, "position_id": f"pos_l_{i}", "holding_bars": 2})
        for i in range(3):
            bad_trades.append({"timestamp": f"2026-08-18 11:{i:02d}:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "CLOSE", "pnl": 10.0, "fees": 0.12, "position_id": f"pos_w_{i}", "holding_bars": 2})

        pd.DataFrame(bad_trades).to_csv(self.bitacora_file, index=False)
        res = self.monitor.run_monitor()
        strat = next(s for s in res["strategies_progress"] if s["strategy_id"] == "Pairs_Stat_Arb_Base")
        self.assertLess(strat["paper_PF"], 0.80)
        self.assertTrue(any("PF_DEGRADATION" in a for a in strat["anomaly_flags"]))
        self.assertTrue(any("EXCESSIVE_DRAWDOWN" in a for a in strat["anomaly_flags"]))

    def test_6_portfolio_overlap_calculation(self):
        """6. Verifies calculation of simultaneous trade entries across strategy pairs."""
        df_overlap = pd.DataFrame([
            {"timestamp": "2026-08-18 12:00:00", "strategy_id": "Pairs_Stat_Arb_Base", "pair": "BTCUSDT/ETHUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "p1"},
            {"timestamp": "2026-08-18 12:00:00", "strategy_id": "Pairs_W90_Z2.5_S3.5_H24", "pair": "BTCUSDT/ETHUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "p2"},
            {"timestamp": "2026-08-18 12:00:00", "strategy_id": "Pairs_W90_Z2.4_S3.5_H24", "pair": "BTCUSDT/ETHUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "p3"},
            {"timestamp": "2026-08-18 14:00:00", "strategy_id": "Pairs_W90_Z2.4_S3.5_H24", "pair": "AVAXUSDT/SOLUSDT", "action": "OPEN", "pnl": 0.0, "fees": 0.12, "position_id": "p4"}
        ])
        df_overlap.to_csv(self.bitacora_file, index=False)

        res = self.monitor.run_monitor()
        overlap = res["portfolio_overlap"]
        self.assertEqual(overlap["overlap_Base_vs_Z2.5"]["concurrent_trades"], 1)
        self.assertEqual(overlap["overlap_Base_vs_Z2.4"]["concurrent_trades"], 1)
        self.assertEqual(overlap["overlap_Z2.5_vs_Z2.4"]["concurrent_trades"], 1)

    def test_7_security_invariants_enforced(self):
        """7. Verifies that APPROVED=false, DEMO_ORDERS=0, REAL_ORDERS=0 are strictly enforced in output."""
        res = self.monitor.run_monitor()
        sec = res["security_invariants"]
        self.assertFalse(sec["APPROVED"])
        self.assertEqual(sec["DEMO_ORDERS"], 0)
        self.assertEqual(sec["REAL_ORDERS"], 0)
        self.assertEqual(sec["human_approval"], "PENDING")


if __name__ == "__main__":
    unittest.main()
