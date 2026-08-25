"""
Unit Test Suite for Forensic Audit of Real Autonomous Acquisition (Sprint #32)
"""

import unittest, json
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.autonomous_customer_acquisition_loop import AutonomousCustomerAcquisitionLoopEngine, CYCLE_HISTORY_JSONL


class TestAcquisitionForensicAudit(unittest.TestCase):

    def setUp(self):
        self.audit_engine = AcquisitionForensicAuditEngine()
        self.loop_engine = AutonomousCustomerAcquisitionLoopEngine()

    def test_1_no_hardcoded_metrics_in_loop(self):
        dash = self.loop_engine.run_acquisition_cycle()
        # All revenue must equal 0.0 unless live COMPLETED payment exists
        self.assertEqual(dash["revenue_usd"], 0.0)
        self.assertFalse(dash["FIRST_REVENUE_ACHIEVED"])

    def test_2_zero_synthetic_events_in_real_funnel(self):
        rep = self.audit_engine.run_forensic_audit()
        dq = rep["data_quality"]
        self.assertEqual(dq["hardcoded_metrics"], 0)
        self.assertEqual(dq["synthetic_metrics"], 0)

    def test_3_cycle_history_auditable(self):
        self.loop_engine.run_acquisition_cycle()
        self.assertTrue(CYCLE_HISTORY_JSONL.exists())
        with open(CYCLE_HISTORY_JSONL, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)
            last_entry = json.loads(lines[-1])
            self.assertIn("cycle_id", last_entry)
            self.assertIn("timestamp", last_entry)
            self.assertIn("action_status", last_entry)

    def test_4_mock_payments_excluded_from_real_revenue(self):
        rep = self.audit_engine.run_forensic_audit()
        rev = rep["revenue"]
        self.assertEqual(rev["completed_payments"], 0)
        self.assertEqual(rev["revenue_usd"], 0.0)

    def test_5_final_verdict_validity(self):
        rep = self.audit_engine.run_forensic_audit()
        self.assertIn(rep["final_verdict"], [
            "REAL_AUTONOMOUS_ACQUISITION_VERIFIED",
            "REAL_AUTONOMOUS_ACQUISITION_NOT_VERIFIED",
            "CRON_OPERATIONAL_BUT_ACQUISITION_INACTIVE",
            "ACQUISITION_TELEMETRY_INVALID"
        ])


if __name__ == "__main__":
    unittest.main()
