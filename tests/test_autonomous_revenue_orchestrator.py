"""
Unit Test Suite for Autonomous Revenue Orchestrator (Sprint #28)
"""

import unittest, uuid
from src.economics.autonomous_revenue_orchestrator import AutonomousRevenueOrchestrator, QuantAuditRevenueEngine, TASK_QUEUE_FILE


class TestAutonomousRevenueOrchestrator(unittest.TestCase):

    def setUp(self):
        # Reset task queue for clean reproducible unit testing
        if TASK_QUEUE_FILE.exists():
            TASK_QUEUE_FILE.unlink()
        self.orchestrator = AutonomousRevenueOrchestrator()

    def test_1_enqueue_task_idempotency(self):
        unique_key = f"KEY_TEST_{uuid.uuid4().hex[:6]}"
        task1 = self.orchestrator.enqueue_task("LEAD_DISCOVERY", {"query": "backtest_sharpe"}, idempotency_key=unique_key)
        self.assertEqual(task1["status"], "PENDING")

        task2 = self.orchestrator.enqueue_task("LEAD_DISCOVERY", {"query": "backtest_sharpe"}, idempotency_key=unique_key)
        self.assertEqual(task2["status"], "SKIPPED_IDEMPOTENT")

    def test_2_update_heartbeat(self):
        hb = self.orchestrator.update_heartbeat(status="HEALTHY", last_job="TEST_JOB")
        self.assertEqual(hb["status"], "HEALTHY")
        self.assertIn("uptime_seconds", hb)

    def test_3_run_scheduled_cycle(self):
        res = self.orchestrator.run_scheduled_cycle()
        self.assertEqual(res["cycle_status"], "PASS")
        self.assertTrue(res["runtime_proof"]["CONTINUOUS_AUTONOMOUS_EXECUTION"])

    def test_4_quant_audit_revenue_engine(self):
        engine = QuantAuditRevenueEngine()
        disc = engine.discover()
        self.assertEqual(len(disc), 1)
        self.assertEqual(disc[0]["task_type"], "LEAD_DISCOVERY")


if __name__ == "__main__":
    unittest.main()
