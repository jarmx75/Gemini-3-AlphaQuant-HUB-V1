import unittest
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path bootstrap
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.self_identity_config import SelfIdentityConfig
from src.economics.prospect_pipeline_engine import ProspectPipelineEngine
from src.economics.autonomous_opportunity_discovery_engine import AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint366ProspectPipeline(unittest.TestCase):
    """Test suite for Sprint #36.6 / Etapa 2 non-contact prospect pipeline & local draft generation."""

    def test_1_self_targeting_blocked(self):
        """Verify owner repo/user/domain opportunities are blocked as BLOCKED_SELF_TARGET."""
        owner_candidate = {
            "channel": "GITHUB",
            "source_url": "https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1",
            "repository": "jarmx75/Gemini-3-AlphaQuant-HUB-V1",
            "author": "jarmx75",
            "context_score": 90,
            "intent_score": 85,
            "promotion_risk": 10
        }
        is_self, reason, ownership = SelfIdentityConfig.is_self_target(owner_candidate)
        self.assertTrue(is_self)
        self.assertEqual(ownership, "SELF")

        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(owner_candidate)
        self.assertTrue(prospect["self_target_flag"])
        self.assertEqual(prospect["ownership_classification"], "SELF")
        self.assertEqual(prospect["status"], "BLOCKED_SELF_TARGET")
        self.assertIsNone(draft)

    def test_2_duplicate_target_blocked(self):
        """Verify repeated target URL or identifier is blocked as BLOCKED_DUPLICATE."""
        test_id = os.urandom(4).hex()
        candidate = {
            "channel": "GITHUB",
            "source_url": f"https://github.com/stat-arb/pairs-trading-engine-{test_id}/issues/42",
            "target_identifier": f"github_stat_arb_{test_id}",
            "repository": f"stat-arb/pairs-trading-engine-{test_id}",
            "author": "quant_researcher_x",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "context_score": 85,
            "intent_score": 80,
            "promotion_risk": 10
        }
        pipeline = ProspectPipelineEngine()
        pipeline.drafts_created_this_run = 0
        
        # First processing -> ELIGIBLE_FOR_DRAFT / DRAFT_CREATED
        prospect1, draft1 = pipeline.process_candidate_opportunity(candidate)
        self.assertIn(prospect1["status"], ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"])

        # Second processing -> BLOCKED_DUPLICATE
        prospect2, draft2 = pipeline.process_candidate_opportunity(candidate)
        self.assertTrue(prospect2["duplicate_flag"])
        self.assertEqual(prospect2["status"], "BLOCKED_DUPLICATE")
        self.assertIsNone(draft2)

    def test_3_eligible_creates_single_local_draft(self):
        """Verify an eligible third-party prospect creates exactly one local draft."""
        candidate = {
            "channel": "REDDIT",
            "source_url": f"https://reddit.com/r/algotrading/comments/test_overfitting_{os.urandom(4).hex()}",
            "target_identifier": f"reddit_test_{os.urandom(4).hex()}",
            "author": "external_trader_99",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "context_score": 88,
            "intent_score": 82,
            "promotion_risk": 15
        }
        pipeline = ProspectPipelineEngine()
        pipeline.drafts_created_this_run = 0
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertFalse(prospect["self_target_flag"])
        self.assertFalse(prospect["duplicate_flag"])
        self.assertEqual(prospect["ownership_classification"], "THIRD_PARTY")
        self.assertIsNotNone(draft)
        self.assertEqual(draft["prospect_id"], prospect["prospect_id"])

    def test_4_draft_requires_human_approval(self):
        """Verify generated drafts enforce PENDING_HUMAN_APPROVAL and NOT_ATTEMPTED."""
        candidate = {
            "channel": "QUANTCONNECT",
            "source_url": f"https://quantconnect.com/forum/discussion/test_{os.urandom(4).hex()}",
            "target_identifier": f"qc_forum_{os.urandom(4).hex()}",
            "author": "qc_user_123",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "context_score": 90,
            "intent_score": 85,
            "promotion_risk": 10
        }
        pipeline = ProspectPipelineEngine()
        pipeline.drafts_created_this_run = 0
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertIsNotNone(draft)
        self.assertEqual(draft["approval_status"], "PENDING_HUMAN_APPROVAL")
        self.assertEqual(draft["external_publication_status"], "NOT_ATTEMPTED")
        self.assertTrue(draft["human_approval_required"])

    def test_5_no_external_publication_during_pipeline(self):
        """Verify prospect pipeline execution makes zero external HTTP requests."""
        pipeline = ProspectPipelineEngine()
        candidate = {
            "channel": "DEV_FORUMS",
            "source_url": f"https://devforum.example.com/t/{os.urandom(4).hex()}",
            "target_identifier": f"dev_forum_{os.urandom(4).hex()}",
            "author": "dev_user_77",
            "context_score": 85,
            "intent_score": 80,
            "promotion_risk": 10
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            prospect, draft = pipeline.process_candidate_opportunity(candidate)
            mock_urlopen.assert_not_called()

    def test_6_once_execution_safe_mode_zero_publications(self):
        """Verify --once execution in default safe mode produces EXTERNAL_PUBLICATION_ATTEMPTED = False."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        report = pilot.run_single_cycle()

        self.assertFalse(report["EXTERNAL_PUBLICATION_ATTEMPTED"])
        self.assertEqual(report["OPERATING_MODE"], "DISCOVERY_AND_DRAFT_ONLY")
        self.assertEqual(report["OUTREACH_SAFETY"]["operating_mode"], "DISCOVERY_AND_DRAFT_ONLY")
        self.assertFalse(report["OUTREACH_SAFETY"]["external_publication_attempted"])
        self.assertEqual(report["ACTIONS"]["actions_sent_externally"], 0)
        self.assertEqual(report["ACTIONS"]["publications_confirmed"], 0)

    def test_7_test_synthetic_data_isolation(self):
        """Verify sandbox test data do not count as eligible commercial prospects."""
        owner_candidate = {
            "channel": "GITHUB",
            "source_url": "https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1",
            "author": "jarmx75",
            "context_score": 90,
            "intent_score": 90,
            "promotion_risk": 0
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(owner_candidate)
        self.assertEqual(prospect["status"], "BLOCKED_SELF_TARGET")
        self.assertIsNone(draft)


if __name__ == "__main__":
    unittest.main()
