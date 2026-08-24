"""
Unit Test Suite for Autonomous Revenue Discovery Engine (Sprint #27)
"""

import unittest
from src.economics.autonomous_revenue_discovery import AutonomousRevenueDiscoveryEngine


class TestAutonomousRevenueDiscoveryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AutonomousRevenueDiscoveryEngine()

    def test_1_score_lead_intent(self):
        lead = {
            "lead_id": "lead_test_01",
            "problem_relevance": 30,
            "purchase_intent": 25,
            "technical_fit": 20,
            "recency": 15,
            "audience_quality": 10
        }
        res = self.engine.score_lead_intent(lead)
        self.assertEqual(res["total_score"], 100)
        self.assertEqual(res["classification"], "HOT")
        self.assertTrue(res["is_hot"])

    def test_2_score_revenue_opportunity(self):
        opp = {
            "opp_id": "opp_test_01",
            "category": "Data Products",
            "demand_score": 20,
            "capital_efficiency": 15,
            "automation_potential": 20,
            "speed_to_market": 15,
            "recurring_potential": 15,
            "regulatory_safety": 15
        }
        res = self.engine.score_revenue_opportunity(opp)
        self.assertEqual(res["opportunity_score"], 100)
        self.assertTrue(res["recurring_potential"])

    def test_3_generate_dashboard(self):
        dash = self.engine.generate_dashboard()
        self.assertIn("timestamp", dash)
        self.assertIn("best_revenue_opportunity", dash)
        self.assertFalse(dash["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
