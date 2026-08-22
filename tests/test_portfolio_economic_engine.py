"""
Unit & Integration Tests for Phase 2 Economic Redesign Modules
Tests: FactorLibrary, PortfolioCapitalReality, PortfolioSurvivorEvaluator, ResearchRouter.
"""

import json
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

from src.portfolio.capital_reality import PortfolioCapitalReality, ALPHA_SOURCE_MAP_TAXONOMY
from src.portfolio.portfolio_survivor import PortfolioSurvivorEvaluator
from src.portfolio.research_router import ResearchRouter
from src.memory.factor_library import FactorLibrary


class TestPortfolioEconomicEngine(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        self.ret_existing = pd.Series(np.random.normal(0.0005, 0.005, 100), index=dates)
        self.ret_cand = pd.Series(np.random.normal(0.0004, 0.006, 100), index=dates)

    def test_1_factor_library_registration(self):
        lib = FactorLibrary()
        factors = lib.get_all_factors()
        self.assertEqual(len(factors), 16)
        
        validated = lib.get_factors_by_classification("FACTOR_VALIDATED")
        self.assertTrue(len(validated) >= 2)

    def test_2_alpha_source_taxonomy_count(self):
        self.assertEqual(len(ALPHA_SOURCE_MAP_TAXONOMY), 2)
        self.assertIn("ALPHA_SOURCE_01", ALPHA_SOURCE_MAP_TAXONOMY)
        self.assertIn("ALPHA_SOURCE_02", ALPHA_SOURCE_MAP_TAXONOMY)

    def test_3_capital_reality_reproducible_analysis(self):
        engine = PortfolioCapitalReality(usd_mxn_rate=20.0)
        report = engine.run_full_analysis()

        self.assertEqual(report['analysis_metadata']['current_alpha_sources_count'], 2)
        self.assertIn("MODELLED / NOT GUARANTEED", report['analysis_metadata']['disclaimer'])
        
        # Verify 2x2 correlation matrix near zero
        corr_2x2 = report['alpha_source_level_analysis']['correlation_matrix_2x2']
        crypto_eq_corr = corr_2x2['ALPHA_SOURCE_01_CRYPTO']['ALPHA_SOURCE_02_EQUITY']
        self.assertLess(abs(crypto_eq_corr), 0.15)

    def test_4_portfolio_survivor_evaluator(self):
        evaluator = PortfolioSurvivorEvaluator()
        res = evaluator.evaluate_candidate(self.ret_existing, self.ret_cand, "Test_Candidate")
        
        self.assertIn("status", res)
        self.assertIn("sharpe_improvement_delta", res["metrics"])

    def test_5_research_router_hard_gates_and_score(self):
        router = ResearchRouter()
        
        valid_spec = {
            "family": "NOVEL_VOLATILITY_SURFACE",
            "dataset_available": True,
            "hypothesis_novel": True,
            "economic_mechanism_explicit": True,
            "is_family_rejected": False,
            "expected_frequency_value": 5.0,
            "execution_cost_plausible": True,
            "novelty": 8.0,
            "data_availability": 10.0,
            "economic_plausibility": 8.0,
            "diversification_value": 9.0,
            "research_cost": 3.0
        }

        eval_res = router.evaluate_hypothesis(valid_spec)
        self.assertEqual(eval_res["status"], "AUTHORIZED_FOR_RESEARCH")
        self.assertTrue(eval_res["all_gates_passed"])
        self.assertGreater(eval_res["research_score"], 10.0)

    def test_6_security_invariants_enforced(self):
        registry_path = Path("src/factory/registry.json")
        if registry_path.exists():
            with open(registry_path) as f:
                reg_data = json.load(f)
            for strat in reg_data.get("strategies", []):
                self.assertEqual(strat.get("human_approval"), "PENDING (Write 'APPROVED' manually to allow Binance Demo/Real)")
                self.assertFalse(strat.get("live_trading_allowed", False))


if __name__ == "__main__":
    unittest.main()
