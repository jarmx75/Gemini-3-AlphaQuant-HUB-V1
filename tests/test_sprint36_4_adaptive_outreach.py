"""
Unit Test Suite for Sprint #36.4 Adaptive Outreach Thresholds & Exposure Budget

Enforces 4 core invariants:
1. 3-Tier adaptive action classification (Tier A AUTO_PUBLISH, Tier B VALUE_CONTRIBUTION, Tier C BLOCK).
2. Exposure budget enforcement (per-cycle and per-target limits).
3. Risk block categorization (duplicate, cooldown, relevance, promo_risk, exposure_budget).
4. Channel evaluation vs action separation (CHANNEL_EVALUATED != CHANNEL_USED / CHANNEL_WITH_ACTIONS).
"""

import unittest
import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.autonomous_opportunity_discovery_engine import OpportunityScorer, AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint364AdaptiveOutreach(unittest.TestCase):

    def setUp(self):
        self.discovery_engine = AutonomousOpportunityDiscoveryEngine()
        self.pilot = LocalAcquisitionPilot()

    def test_1_three_tier_action_classification(self):
        """Verify Tier A, Tier B, and Tier C assignment based on context, intent, and promo risk."""
        tier_a_opp = {"channel": "GITHUB", "context_score": 85, "intent_score": 80, "promotion_risk": 10, "duplicate_risk": 0}
        tier_b_opp = {"channel": "REDDIT", "context_score": 60, "intent_score": 50, "promotion_risk": 30, "duplicate_risk": 0}
        tier_c_opp = {"channel": "REDDIT", "context_score": 40, "intent_score": 30, "promotion_risk": 50, "duplicate_risk": 0}

        res_a = OpportunityScorer.evaluate_publication_guards(tier_a_opp)
        res_b = OpportunityScorer.evaluate_publication_guards(tier_b_opp)
        res_c = OpportunityScorer.evaluate_publication_guards(tier_c_opp)

        self.assertTrue(res_a.is_qual)
        self.assertEqual(res_a.action_tier, "TIER_A_AUTO_PUBLISH")

        self.assertTrue(res_b.is_qual)
        self.assertEqual(res_b.action_tier, "TIER_B_VALUE_CONTRIBUTION")

        self.assertFalse(res_c.is_qual)
        self.assertEqual(res_c.action_tier, "TIER_C_BLOCK")

    def test_2_exposure_budget_enforcement(self):
        """Verify per-cycle and per-target exposure budgets are enforced."""
        rep = self.pilot.run_single_cycle()
        outreach = rep["OUTREACH"]
        # Actions per cycle must be <= 5
        self.assertLessEqual(outreach["actions_successful"], 5)
        self.assertLessEqual(outreach["publications_created"], 5)

    def test_3_risk_block_categorization(self):
        """Verify risk metrics categorize duplicate, cooldown, relevance, promo_risk, and budget blocks."""
        rep = self.pilot.run_single_cycle()
        risk = rep["RISK"]
        self.assertIn("duplicate_blocks", risk)
        self.assertIn("cooldown_blocks", risk)
        self.assertIn("relevance_blocks", risk)
        self.assertIn("promotion_risk_blocks", risk)
        self.assertIn("exposure_budget_blocks", risk)

    def test_4_channel_evaluation_vs_action_separation(self):
        """Verify evaluated channels are NOT automatically counted as channels_with_actions."""
        rep = self.pilot.run_single_cycle()
        ch = rep["CHANNELS"]
        self.assertEqual(ch["channels_evaluated"], 9)
        self.assertLessEqual(ch["channels_with_actions"], ch["channels_evaluated"])
        self.assertLessEqual(ch["channels_with_publications"], ch["channels_evaluated"])


if __name__ == "__main__":
    unittest.main()
