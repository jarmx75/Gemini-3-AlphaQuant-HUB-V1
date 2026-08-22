"""
Unit Tests for Track B Economic Opportunity Engine Modules
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path

from src.economics.opportunity_scorer import OpportunityScorer
from src.economics.validation_gates import ValidationGates
from src.economics.opportunity_engine import OpportunityEngine
from src.economics.experiment_router import AutonomousExperimentRouter
from src.economics.mvp_quant_audit_service import QuantAuditServiceMVP


class TestEconomicOpportunityEngine(unittest.TestCase):

    def test_1_opportunity_scorer(self):
        scorer = OpportunityScorer()
        opp = {
            "economic_value": 8.0,
            "evidence_strength": 8.0,
            "automation_ratio": 0.9,
            "recurrence_score": 8.0,
            "speed_to_mvp": 9.0,
            "capital_efficiency": 10.0,
            "technical_feasibility": 9.0,
            "strategic_fit": 9.0,
            "downside_risk": 2.0,
            "distribution_difficulty": 3.0,
            "regulatory_burden": 1.0,
            "time_to_first_revenue_days": 3.0
        }
        score = scorer.compute_eos(opp)
        self.assertGreater(score, 100.0)

    def test_2_validation_gates(self):
        gates = ValidationGates()
        valid_opp = {
            "family": "MICRO_SAAS",
            "regulatory_burden": 1,
            "technical_feasibility": 9,
            "capital_required_usd": 0,
            "data_available": True,
            "testable_without_real_money": True,
            "is_duplicate": False,
            "problem": "Pairs trading scan"
        }
        passed, rejections = gates.evaluate_opportunity_gates(valid_opp)
        self.assertTrue(passed)
        self.assertEqual(len(rejections), 0)

    def test_3_opportunity_engine_top_3(self):
        engine = OpportunityEngine()
        summary = engine.process_catalog()
        self.assertEqual(len(summary["top_3_selected"]), 3)

    def test_4_experiment_router(self):
        router = AutonomousExperimentRouter()
        res = router.select_next_best_experiment()
        self.assertEqual(res["status"], "EXPERIMENT_SELECTED")

    def test_5_mvp_quant_audit_service(self):
        service = QuantAuditServiceMVP()
        rets = pd.Series(np.random.normal(0.001, 0.005, 100))
        cert = service.audit_strategy_returns("Test_Strategy", rets)
        self.assertIn("certificate_id", cert)
        self.assertIn("audit_verdict", cert)


if __name__ == "__main__":
    unittest.main()
