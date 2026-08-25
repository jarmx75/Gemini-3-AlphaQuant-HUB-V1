"""
Unit Test Suite for Autonomous Customer Acquisition Loop (Sprint #30)
"""

import unittest
from src.economics.autonomous_customer_acquisition_loop import AutonomousCustomerAcquisitionLoopEngine


class TestAutonomousCustomerAcquisitionLoopEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AutonomousCustomerAcquisitionLoopEngine()

    def test_1_lead_quality_gate(self):
        self.assertTrue(self.engine.evaluate_lead_quality_gate(85, 75, 10))
        self.assertFalse(self.engine.evaluate_lead_quality_gate(75, 75, 10))
        self.assertFalse(self.engine.evaluate_lead_quality_gate(85, 65, 10))
        self.assertFalse(self.engine.evaluate_lead_quality_gate(85, 75, 25))

    def test_2_generate_contextual_educational_content(self):
        cnt = self.engine.generate_contextual_educational_content("Backtest Sharpe Distortion")
        self.assertIn("Quantitative Diagnostic", cnt["title"])
        self.assertIn("Strategy Health Diagnostic Quiz", cnt["body"])
        self.assertEqual(cnt["cta_type"], "FREE_DIAGNOSTIC_QUIZ")

    def test_3_run_acquisition_cycle(self):
        dash = self.engine.run_acquisition_cycle()
        self.assertTrue(dash["AUTONOMOUS_ACQUISITION"])
        self.assertIn("best_channel", dash)
        self.assertFalse(dash["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
