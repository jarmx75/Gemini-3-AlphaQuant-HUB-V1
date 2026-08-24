"""
Unit Test Suite for Customer Conversion Experiment Engine (Sprint #25)
"""

import unittest
from src.economics.customer_conversion_experiment import CustomerConversionExperimentEngine


class TestCustomerConversionExperimentEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CustomerConversionExperimentEngine()

    def test_1_classify_human_intent(self):
        self.assertEqual(self.engine.classify_human_intent("How to audit my backtest?"), "HOT")
        self.assertEqual(self.engine.classify_human_intent("Is there PBO overfitting risk?"), "WARM")
        self.assertEqual(self.engine.classify_human_intent("Thanks for the info!"), "NURTURE")
        self.assertEqual(self.engine.classify_human_intent("Random text"), "NO_ACTION")

    def test_2_run_conversion_experiment(self):
        exp = self.engine.run_conversion_experiment()
        self.assertEqual(exp["experiment_id"], "EXP_GH_GOTIBHAI_18_V1")
        self.assertIn("human_replies", exp)
        self.assertIn("landing_visits", exp)
        self.assertFalse(exp["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
