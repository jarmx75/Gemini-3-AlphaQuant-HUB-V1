"""
Unit Test Suite for Outreach Conversion Engine (Sprint #23)
"""

import unittest
from src.economics.outreach_conversion_engine import OutreachConversionEngine


class TestOutreachConversionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = OutreachConversionEngine()

    def test_1_register_lead_state(self):
        res = self.engine.register_lead_state("lead_test_01", "r/algotrading", "Test StatArb Query", "QUALIFIED", {"score": 95})
        self.assertEqual(res["status"], "QUALIFIED")
        self.assertEqual(res["lead_id"], "lead_test_01")

    def test_2_prepare_contextual_contribution(self):
        lead = {"lead_id": "lead_test_02", "source": "GitHub", "title": "Audit tools query"}
        contrib = self.engine.prepare_contextual_contribution(lead)
        self.assertIn("Probability of Backtest Overfitting", contrib["body"])
        self.assertEqual(contrib["status"], "DRAFT")
        self.assertEqual(contrib["price"], "$49 USD")

    def test_3_calculate_expected_revenue(self):
        stats = self.engine.calculate_expected_revenue()
        self.assertIn("expected_revenue_usd", stats)
        self.assertIn("FIRST_REVENUE_ACHIEVED", stats)
        self.assertFalse(stats["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
