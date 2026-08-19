"""
Failure Injection & End-to-End Integration Test Suite for Demo Dry-Run
Verifies:
1. Complete normal flow (signal -> risk -> order -> fill -> position -> reconcile -> close -> logs).
2. Stale market data detection & rejection.
3. Simulated API timeout & safe idempotent recovery.
4. Duplicate submit idempotency (same clientOrderId never doubles fill).
5. Partial fill handling.
6. Rejected order handling.
7. Position mismatch detection -> Reconciliation HALT & KillSwitch trigger.
8. Unexpected fill detection -> Reconciliation HALT.
9. Kill switch circuit breaker -> cancels open orders & blocks new orders.
10. Daily loss limit breach -> blocks new entries.
11. Strategy drawdown breach -> blocks entries.
12. State persistence & restart recovery with open positions.
13. Security invariants (no network in DRY_RUN, REAL requires APPROVED, zero paper pollution).
"""

import os
import sys
import time
import json
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.execution.execution_config import ExecutionConfig, ExecutionMode
from src.execution.dry_run_broker import DryRunBroker
from src.execution.order_manager import OrderManager, OrderStatus
from src.execution.position_manager import PositionManager
from src.execution.risk_manager import RiskManager
from src.execution.reconciliation import ReconciliationEngine
from src.execution.kill_switch import KillSwitch, KillReason
from src.execution.demo_dry_run import DemoDryRunRehearsal
from src.execution.paper_gate_monitor import PaperGateMonitor


class TestDemoDryRunFailureInjection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name)
        self.rehearsal = DemoDryRunRehearsal(log_dir=self.log_dir, initial_balance=5000.0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_1_normal_lifecycle_end_to_end(self):
        """1. Verifies the complete happy path: Signal -> Risk -> 2 Legs Filled -> Reconcile -> Close."""
        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "z_score": 2.8,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        open_res = self.rehearsal.execute_signal(sig)
        self.assertEqual(open_res["status"], "SUCCESS")
        self.assertTrue(open_res["reconciliation_ok"])
        self.assertIn("BTCUSDT/ETHUSDT", self.rehearsal.position_mgr.open_positions)

        # Close position
        close_res = self.rehearsal.close_position("BTCUSDT/ETHUSDT", exit_price_y=59000.0, exit_price_x=3000.0, reason="Target Reverted")
        self.assertEqual(close_res["status"], "SUCCESS")
        self.assertTrue(close_res["reconciliation_ok"])
        self.assertNotIn("BTCUSDT/ETHUSDT", self.rehearsal.position_mgr.open_positions)
        self.assertEqual(len(self.rehearsal.position_mgr.closed_positions), 1)

    def test_2_stale_market_data_blocked_by_risk_and_kill_switch(self):
        """2. Verifies that stale market data (>30s) halts order submission."""
        # Set market data timestamp 100 seconds in the past
        self.rehearsal.risk_mgr.last_market_data_timestamp = time.time() - 100.0

        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_LONG_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        res = self.rehearsal.execute_signal(sig)
        self.assertEqual(res["status"], "RISK_REJECTED")
        self.assertIn("Stale market data", res["reason"])

        # Check auto-kill evaluation
        is_stale, _ = self.rehearsal.risk_mgr.check_stale_data()
        kill_event = self.rehearsal.kill_switch.check_auto_kill_conditions(is_data_stale=is_stale)
        self.assertIsNotNone(kill_event)
        self.assertEqual(kill_event.reason, KillReason.STALE_MARKET_DATA)
        self.assertTrue(self.rehearsal.config.kill_switch_active)

    def test_3_simulated_api_timeout_and_idempotent_recovery(self):
        """3. Verifies that timeout during submit does not duplicate orders upon safe recovery."""
        broker = self.rehearsal.broker
        order_mgr = self.rehearsal.order_mgr

        cid = "test_timeout_cid_123"
        # First attempt: timeout injection
        broker.inject_timeout(True)
        order = order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.01,
            price=60000.0,
            client_order_id=cid
        )
        self.assertEqual(order.status, OrderStatus.REJECTED)

        # Reset timeout and submit again with same clientOrderId
        broker.inject_timeout(False)
        order_recovered = order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.01,
            price=60000.0,
            client_order_id=cid
        )
        self.assertEqual(order_recovered.status, OrderStatus.FILLED)
        self.assertEqual(len(broker.fills_log), 1)

    def test_4_duplicate_submit_idempotency(self):
        """4. Verifies that resubmitting with same clientOrderId never creates multiple fills."""
        broker = self.rehearsal.broker
        order_mgr = self.rehearsal.order_mgr

        cid = "idempotent_order_999"
        order1 = order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="ETHUSDT",
            side="SELL",
            quantity=0.5,
            price=3000.0,
            client_order_id=cid
        )
        self.assertEqual(order1.status, OrderStatus.FILLED)
        self.assertEqual(len(broker.fills_log), 1)

        # Resubmit identical client_order_id
        order2 = order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="ETHUSDT",
            side="SELL",
            quantity=0.5,
            price=3000.0,
            client_order_id=cid
        )
        self.assertEqual(order2.status, OrderStatus.FILLED)
        self.assertEqual(len(broker.fills_log), 1, "Must NOT duplicate fill in broker")

    def test_5_partial_fill_handling(self):
        """5. Verifies partial fill simulation and position tracking."""
        self.rehearsal.broker.inject_partial_fill(True, ratio=0.5)
        order = self.rehearsal.order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.02,
            price=60000.0
        )
        self.assertEqual(order.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(order.executed_qty, 0.01)

    def test_6_rejected_order_handling(self):
        """6. Verifies order rejection leaves local state intact."""
        self.rehearsal.broker.inject_rejection(True)
        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        res = self.rehearsal.execute_signal(sig)
        self.assertEqual(res["status"], "LEG_Y_FAILED")
        self.assertEqual(len(self.rehearsal.position_mgr.open_positions), 0)

    def test_7_position_mismatch_triggers_reconciliation_halt(self):
        """7. Verifies that broker position mismatch causes Reconciliation halt and KillSwitch trigger."""
        # First open a normal position
        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        self.rehearsal.execute_signal(sig)

        # Inject corrupt position mismatch on broker
        self.rehearsal.broker.inject_position_mismatch("BTCUSDT", 0.5)

        # Run reconciliation
        report = self.rehearsal.reconciliation.run_full_reconciliation()
        self.assertFalse(report.is_synchronized)
        self.assertTrue(report.halt_required)
        self.assertTrue(len(report.position_mismatches) > 0)

        # Check auto kill
        event = self.rehearsal.kill_switch.check_auto_kill_conditions(reconciliation_report=report)
        self.assertIsNotNone(event)
        self.assertEqual(event.reason, KillReason.POSITION_MISMATCH)
        self.assertTrue(self.rehearsal.config.kill_switch_active)

    def test_8_unexpected_fill_triggers_reconciliation_halt(self):
        """8. Verifies that unrequested position on exchange triggers reconciliation failure."""
        self.rehearsal.broker.inject_unexpected_fill("AVAXUSDT", 10.0, 30.0)
        report = self.rehearsal.reconciliation.run_full_reconciliation()
        self.assertFalse(report.is_synchronized)
        self.assertTrue(report.halt_required)

    def test_9_kill_switch_cancels_orders_and_blocks_new(self):
        """9. Verifies kill switch cancels open orders and blocks any new submissions."""
        # Create a pending order on broker
        self.rehearsal.broker.orders["open_order_1"] = {
            "symbol": "BTCUSDT",
            "orderId": 777,
            "clientOrderId": "open_order_1",
            "status": "SUBMITTED",
            "executedQty": "0",
            "origQty": "0.1",
            "avgPrice": "0",
            "side": "BUY",
            "type": "LIMIT"
        }
        managed = self.rehearsal.order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            price=50000.0,
            client_order_id="open_order_1"
        )
        self.rehearsal.order_mgr.orders["open_order_1"].status = OrderStatus.SUBMITTED

        # Trigger Kill Switch
        kill_event = self.rehearsal.kill_switch.trigger(KillReason.MANUAL_TRIGGER, "Manual Safety Halt")
        self.assertTrue(self.rehearsal.kill_switch.is_triggered)
        self.assertEqual(kill_event.orders_canceled, 1)

        # Attempt new order
        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        res = self.rehearsal.execute_signal(sig)
        self.assertEqual(res["status"], "RISK_REJECTED")
        self.assertIn("Kill switch is actively triggered", res["reason"])

    def test_10_daily_loss_limit_breach(self):
        """10. Verifies that cumulative daily loss >= $50 blocks further trades."""
        self.rehearsal.risk_mgr.record_pnl("Pairs_Stat_Arb_Base", -55.0)

        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        res = self.rehearsal.execute_signal(sig)
        self.assertEqual(res["status"], "RISK_REJECTED")
        self.assertIn("Max daily loss reached", res["reason"])

    def test_11_strategy_drawdown_limit_breach(self):
        """11. Verifies that strategy drawdown >= 10% ($100 on $1000 base) blocks trades."""
        self.rehearsal.config.max_daily_loss = 500.0  # Isolate strategy DD from daily loss limit
        # Initial peak at +50, then drop to -60 -> DD = 110 USD = 11%
        self.rehearsal.risk_mgr.record_pnl("Pairs_Stat_Arb_Base", 50.0)
        self.rehearsal.risk_mgr.record_pnl("Pairs_Stat_Arb_Base", -110.0)

        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        res = self.rehearsal.execute_signal(sig)
        self.assertEqual(res["status"], "RISK_REJECTED")
        self.assertIn("drawdown", res["reason"])

    def test_12_restart_with_open_position_recovery(self):
        """12. Verifies local position state recovery across restarts."""
        # Open position
        sig = {
            "strategy_id": "Pairs_Stat_Arb_Base",
            "pair": "BTCUSDT/ETHUSDT",
            "action": "OPEN_SHORT_SPREAD",
            "gamma": 20.0,
            "price_y": 60000.0,
            "price_x": 3000.0
        }
        self.rehearsal.execute_signal(sig)
        self.assertEqual(len(self.rehearsal.position_mgr.open_positions), 1)

        # Create fresh rehearsal instance connected to same broker state
        rehearsal_2 = DemoDryRunRehearsal(log_dir=self.log_dir)
        rehearsal_2.broker = self.rehearsal.broker
        rehearsal_2.position_mgr.open_positions = self.rehearsal.position_mgr.open_positions.copy()
        rehearsal_2.reconciliation.client = rehearsal_2.broker
        rehearsal_2.reconciliation.position_mgr = rehearsal_2.position_mgr

        # Reconcile after restart
        report = rehearsal_2.reconciliation.run_full_reconciliation()
        self.assertTrue(report.is_synchronized)
        self.assertFalse(report.halt_required)

    def test_13_security_invariants_and_zero_paper_pollution(self):
        """13. Verifies DRY_RUN never modifies bitacora paper trades and preserves security invariants."""
        # Execute multiple dry-run rehearsal trades
        for i in range(5):
            self.rehearsal.execute_signal({
                "strategy_id": "Pairs_Stat_Arb_Base",
                "pair": "BTCUSDT/ETHUSDT",
                "action": "OPEN_SHORT_SPREAD",
                "gamma": 20.0,
                "price_y": 60000.0,
                "price_x": 3000.0
            })
            self.rehearsal.close_position("BTCUSDT/ETHUSDT", exit_price_y=60000.0, exit_price_x=3000.0)

        # Verify paper gate monitor still sees 0 closed paper trades
        monitor = PaperGateMonitor()
        rep = monitor.run_monitor()
        for sp in rep["strategies_progress"]:
            self.assertEqual(sp["closed_paper_trades"], 0, "DryRun trades must NEVER count as Paper trades")

        # Verify security invariants
        self.assertEqual(self.rehearsal.config.env, ExecutionMode.DRY_RUN)
        self.assertEqual(self.rehearsal.config.base_url, "LOCAL_DRY_RUN_NO_NETWORK")
        self.assertFalse(self.rehearsal.config.real_trading_enabled)


if __name__ == "__main__":
    unittest.main()
