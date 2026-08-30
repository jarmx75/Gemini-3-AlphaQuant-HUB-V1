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
from src.economics.prospect_pipeline_engine import ProspectPipelineEngine, classify_source_trust
from src.economics.autonomous_opportunity_discovery_engine import AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint3661PipelineIntegrity(unittest.TestCase):
    """Test suite for Sprint #36.6.1 / Etapa 2.1 prospect pipeline integrity and trust classification."""

    def test_1_owner_repo_candidate_blocked_self_target(self):
        """Verify candidate from owner repository yields blocked_self_target = 1 and prospects_eligible = 0."""
        candidate = {
            "channel": "GITHUB",
            "source_url": "https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1",
            "repository": "jarmx75/Gemini-3-AlphaQuant-HUB-V1",
            "author": "jarmx75",
            "context_score": 90,
            "intent_score": 90,
            "promotion_risk": 0
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertEqual(prospect["status"], "BLOCKED_SELF_TARGET")
        self.assertEqual(prospect["ownership_classification"], "SELF")
        self.assertEqual(prospect["source_trust_classification"], "INTERNAL_OR_SELF")
        self.assertIsNone(draft)

    def test_2_self_target_never_creates_draft(self):
        """Verify self-target candidate never creates a local draft."""
        candidates = [
            {"channel": "GITHUB", "source_url": "https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1", "author": "jarmx75"},
            {"channel": "GITHUB", "source_url": "https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/", "author": "alpha-quant1"}
        ]
        pipeline = ProspectPipelineEngine()
        for cand in candidates:
            prospect, draft = pipeline.process_candidate_opportunity(cand)
            self.assertEqual(prospect["status"], "BLOCKED_SELF_TARGET")
            self.assertIsNone(draft)

    def test_3_template_synthetic_never_creates_commercial_draft(self):
        """Verify template/synthetic candidates do not create commercial drafts."""
        candidate = {
            "channel": "REDDIT",
            "source_url": f"https://reddit.com/r/algotrading/comments/mock_synth_{os.urandom(4).hex()}",
            "target_identifier": f"reddit_synth_{os.urandom(4).hex()}",
            "is_synthetic": True,
            "context_score": 90,
            "intent_score": 85,
            "promotion_risk": 10
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertEqual(prospect["source_trust_classification"], "TEMPLATE_OR_SYNTHETIC")
        self.assertEqual(prospect["status"], "BLOCKED_TEMPLATE_OR_SYNTHETIC")
        self.assertIsNone(draft)

    def test_4_unverified_external_pending_verification(self):
        """Verify candidate without live API verification proof receives PENDING_SOURCE_VERIFICATION."""
        candidate = {
            "channel": "QUANTCONNECT",
            "source_url": f"https://quantconnect.com/forum/discussion/unverified_{os.urandom(4).hex()}",
            "target_identifier": f"qc_unverified_{os.urandom(4).hex()}",
            "source_trust_classification": "UNVERIFIED_EXTERNAL_SOURCE",
            "context_score": 85,
            "intent_score": 80,
            "promotion_risk": 10
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertEqual(prospect["status"], "PENDING_SOURCE_VERIFICATION")
        self.assertIsNone(draft)

    def test_5_only_verified_external_creates_draft(self):
        """Verify ONLY VERIFIED_EXTERNAL_SOURCE candidates can create local drafts."""
        candidate = {
            "channel": "GITHUB",
            "source_url": f"https://github.com/real-quant-lab/strategy-engine-{os.urandom(4).hex()}/issues/10",
            "target_identifier": f"github_real_{os.urandom(4).hex()}",
            "repository": "real-quant-lab/strategy-engine",
            "author": "external_quant_dev",
            "is_live_api_verified": True,
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "context_score": 88,
            "intent_score": 82,
            "promotion_risk": 10
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(candidate)

        self.assertEqual(prospect["source_trust_classification"], "VERIFIED_EXTERNAL_SOURCE")
        self.assertIn(prospect["status"], ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"])
        self.assertIsNotNone(draft)
        self.assertEqual(draft["approval_status"], "PENDING_HUMAN_APPROVAL")

    def test_6_pipeline_mathematical_invariants(self):
        """Verify mathematical invariants of PROSPECT_PIPELINE block."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        report = pilot.run_single_cycle()
        pipe = report["PROSPECT_PIPELINE"]
        telemetry = pilot.discovery_engine.prospect_engine.evaluate_pipeline_telemetry()

        disc = telemetry["prospects_discovered"]
        elig = telemetry["prospects_eligible"]
        blocked_self = telemetry["blocked_self_target"]
        blocked_dup = telemetry["blocked_duplicate"]
        pending_verif = telemetry["pending_source_verification"]
        tmpl_synth = telemetry["template_or_synthetic"]
        low_relev = telemetry.get("blocked_low_relevance", 0)
        hist_unverif = telemetry.get("blocked_historical_unverified", 0)
        max_cap = telemetry.get("blocked_max_drafts_cap", 0)

        self.assertEqual(disc, elig + blocked_self + blocked_dup + pending_verif + tmpl_synth + low_relev + hist_unverif + max_cap)

        # Invariant 2: Drafts created <= prospects eligible
        self.assertLessEqual(pipe["local_drafts_created"], pipe["prospects_eligible"])

        # Invariant 3: No negative values
        for k, v in pipe.items():
            if isinstance(v, (int, float)):
                self.assertGreaterEqual(v, 0)

    def test_7_invalidated_drafts_not_approvable(self):
        """Verify invalidated drafts from mock sources are excluded from active human approval count."""
        pipeline = ProspectPipelineEngine()
        drafts = pipeline.load_all_drafts()
        unverified_pending = [d for d in drafts if d.get("approval_status") == "PENDING_HUMAN_APPROVAL" and d.get("source_trust_classification") != "VERIFIED_EXTERNAL_SOURCE"]
        invalidated = [d for d in drafts if d.get("approval_status") == "INVALIDATED_SOURCE_NOT_VERIFIED"]

        # All mock drafts generated in previous run must be invalidated
        self.assertEqual(len(unverified_pending), 0)
        self.assertGreater(len(invalidated), 0)

    def test_8_zero_external_publication(self):
        """Verify single cycle run produces zero external publication and EXTERNAL_PUBLICATION_ATTEMPTED = False."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        report = pilot.run_single_cycle()

        self.assertFalse(report["EXTERNAL_PUBLICATION_ATTEMPTED"])
        self.assertFalse(report["OUTREACH_SAFETY"]["external_publication_attempted"])
        self.assertEqual(report["ACTIONS"]["actions_sent_externally"], 0)


if __name__ == "__main__":
    unittest.main()
