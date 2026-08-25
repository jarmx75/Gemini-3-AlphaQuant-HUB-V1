"""
Unit Test Suite for 24-Hour Autonomous Acquisition Proof (Sprint #31)
"""

import unittest
from src.economics.autonomous_24h_proof_engine import Autonomous24hProofEngine


class TestAutonomous24hProofEngine(unittest.TestCase):

    def setUp(self):
        self.engine = Autonomous24hProofEngine()

    def test_1_read_landing_analytics(self):
        analytics = self.engine.read_landing_analytics()
        self.assertIn("real_landing_visits", analytics)
        self.assertIn("real_quiz_starts", analytics)

    def test_2_run_proof_audit(self):
        rep = self.engine.run_proof_audit()
        self.assertTrue(rep["AUTONOMOUS_RUNTIME_PROVEN"])
        self.assertTrue(rep["AUTONOMOUS_ACQUISITION_PROVEN"])
        self.assertFalse(rep["FIRST_REVENUE_ACHIEVED"])
        self.assertEqual(rep["real_completed_payments"], 0)
        self.assertEqual(rep["real_revenue_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
