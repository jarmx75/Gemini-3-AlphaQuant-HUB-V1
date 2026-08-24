"""
Unit Test Suite for Customer Acquisition Engine (Sprint #22)
"""

import unittest
from src.economics.customer_acquisition_engine import CustomerAcquisitionEngine


class TestCustomerAcquisitionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CustomerAcquisitionEngine()

    def test_1_lead_scoring_hot(self):
        lead = {
            "lead_id": "hot_01",
            "problem_intent_score": 25,
            "quant_relevance_score": 20,
            "backtest_present_score": 20,
            "risk_overfitting_score": 15,
            "purchase_intent_score": 10,
            "channel_permission_score": 10
        }
        res = self.engine.score_lead(lead)
        self.assertEqual(res["total_score"], 100)
        self.assertEqual(res["classification"], "HOT")
        self.assertTrue(res["is_qualified"])

    def test_2_lead_scoring_ignore(self):
        lead = {
            "lead_id": "spam_01",
            "problem_intent_score": 5,
            "quant_relevance_score": 0,
            "backtest_present_score": 0,
            "risk_overfitting_score": 0,
            "purchase_intent_score": 0,
            "channel_permission_score": 0
        }
        res = self.engine.score_lead(lead)
        self.assertEqual(res["total_score"], 5)
        self.assertEqual(res["classification"], "IGNORE")
        self.assertFalse(res["is_qualified"])

    def test_3_generate_educational_content(self):
        content = self.engine.generate_educational_content("pbo_overfitting")
        self.assertIn("Probability of Backtest Overfitting", content["title"])
        self.assertIn("$49 USD", content["price"])
        self.assertIn("https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/", content["cta_link"])

    def test_4_acquisition_cycle_execution(self):
        report = self.engine.run_discovery_and_acquisition_cycle()
        self.assertGreater(report["raw_leads_discovered"], 0)
        self.assertGreater(report["qualified_leads_count"], 0)
        self.assertIn("generated_content", report)


if __name__ == "__main__":
    unittest.main()
