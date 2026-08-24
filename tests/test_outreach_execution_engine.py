"""
Unit Test Suite for Outreach Quality Execution Engine (Sprint #24.1)
"""

import unittest
from src.economics.outreach_execution_engine import RealOutreachExecutionEngine


class TestRealOutreachExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RealOutreachExecutionEngine()

    def test_1_relevance_gate_pass(self):
        gate = self.engine.calculate_relevance_gate(
            "Backtest overfitting and lookahead bias verification",
            "How can I test Probability of Backtest Overfitting (PBO) and friction?"
        )
        self.assertTrue(gate["passed_gate"])
        self.assertGreaterEqual(gate["context_score"], 80)
        self.assertGreaterEqual(gate["intent_score"], 70)

    def test_2_relevance_gate_fail_irrelevant(self):
        gate = self.engine.calculate_relevance_gate(
            "GitHub Stars RFC 010 Investment Signal Engine",
            "Looking for suspicious stars on repo"
        )
        self.assertFalse(gate["passed_gate"])
        self.assertGreaterEqual(gate["risk_score"], 20)

    def test_3_generate_contextual_technical_response(self):
        resp = self.engine.generate_contextual_technical_response(
            "Backtest equity curve uses wall-clock timestamps; Sharpe distorted",
            "Sortino ratio distorted"
        )
        self.assertIn("Technical Observation", resp)
        self.assertNotIn("$49", resp)
        self.assertNotIn("buy now", resp.lower())

    def test_4_execute_outreach_cycle(self):
        rep = self.engine.execute_outreach_cycle()
        self.assertEqual(rep["comments_reviewed"], 5)
        self.assertEqual(rep["duplicates_removed"], 2)
        self.assertEqual(rep["irrelevant_comments_removed"], 2)
        self.assertEqual(rep["comments_kept"], 1)
        self.assertEqual(rep["remediation_status"], "REMEDIATION_COMPLETE_HIGH_QUALITY_ENFORCED")


if __name__ == "__main__":
    unittest.main()
