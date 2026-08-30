import unittest
import os
import sys
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path bootstrap
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.self_identity_config import SelfIdentityConfig
from src.economics.prospect_pipeline_engine import ProspectPipelineEngine, classify_source_trust
from src.economics.autonomous_opportunity_discovery_engine import GitHubAdapter
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


def mock_github_api_search_response(items=None, status=200, remaining=50):
    if items is None:
        items = [
            {
                "html_url": f"https://github.com/quant-org/repo-{i}/issues/{i}",
                "repository_url": f"https://api.github.com/repos/quant-org/repo-{i}",
                "number": i,
                "title": f"Backtest overfitting diagnostic issue #{i}",
                "body": "Lookahead bias and out-of-sample Sharpe ratio degradation problem",
                "user": {"login": f"quant_trader_{i}"},
                "url": f"https://api.github.com/repos/quant-org/repo-{i}/issues/{i}",
                "created_at": "2026-08-30T10:00:00Z",
                "updated_at": "2026-08-30T10:30:00Z"
            }
            for i in range(1, 20)
        ]

    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.headers = {
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Reset": "1770000000"
    }
    mock_resp.read.return_value = json.dumps({"total_count": len(items), "items": items}).encode("utf-8")
    return MagicMock(__enter__=MagicMock(return_value=mock_resp))


class TestSprint3671GitHubDataIntegrity(unittest.TestCase):
    """Test suite for Sprint #36.7.1 / Etapa 3.1 GitHub Data Integrity & Hard Limits."""

    def test_1_http_403_produces_zero_verified_sources_and_drafts(self):
        """Verify HTTP 403 Forbidden produces 0 verified external sources and 0 current cycle drafts."""
        adapter = GitHubAdapter()
        err_resp = urllib.error.HTTPError(
            url="https://api.github.com/search/issues",
            code=403,
            msg="API rate limit exceeded",
            hdrs={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": "60"},
            fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err_resp):
            opportunities = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(opportunities), 0)
            self.assertEqual(adapter.telemetry["github_http_200_responses_current_cycle"], 0)
            self.assertEqual(adapter.telemetry["github_external_sources_verified_current_cycle"], 0)
            self.assertEqual(adapter.telemetry["github_drafts_created_current_cycle"], 0)
            self.assertIn("403", str(adapter.telemetry["github_api_error_current_cycle"]))

    def test_2_http_429_produces_zero_verified_sources_and_drafts(self):
        """Verify HTTP 429 Too Many Requests produces 0 verified sources and 0 drafts."""
        adapter = GitHubAdapter()
        err_resp = urllib.error.HTTPError(
            url="https://api.github.com/search/issues",
            code=429,
            msg="Too Many Requests",
            hdrs={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": "60"},
            fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err_resp):
            opportunities = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(opportunities), 0)
            self.assertEqual(adapter.telemetry["github_http_200_responses_current_cycle"], 0)
            self.assertEqual(adapter.telemetry["github_external_sources_verified_current_cycle"], 0)

    def test_3_timeout_network_error_produces_zero_verified_sources_and_drafts(self):
        """Verify network timeout / exception produces 0 verified sources and 0 drafts."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
            opportunities = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(opportunities), 0)
            self.assertEqual(adapter.telemetry["github_http_200_responses_current_cycle"], 0)
            self.assertEqual(adapter.telemetry["github_external_sources_verified_current_cycle"], 0)

    def test_4_http_200_zero_items_produces_zero_verified_sources_and_drafts(self):
        """Verify HTTP 200 response with 0 items produces 0 verified sources and 0 drafts."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response(items=[])):
            opportunities = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(opportunities), 0)
            self.assertEqual(adapter.telemetry["github_http_200_responses_current_cycle"], 1)
            self.assertEqual(adapter.telemetry["github_external_sources_verified_current_cycle"], 0)

    def test_5_valid_http_200_respects_max_10_verified_prospects_cap(self):
        """Verify valid HTTP 200 response caps verified external sources at max 10 per run."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()):
            opportunities = adapter.discover_opportunities(max_queries=1)
            self.assertLessEqual(len(opportunities), 10)
            self.assertEqual(adapter.telemetry["github_external_sources_verified_current_cycle"], 10)

    def test_6_valid_drafts_respect_max_5_cap(self):
        """Verify local draft generation enforces hard cap of max 5 drafts per run."""
        pipeline = ProspectPipelineEngine()
        pipeline.drafts_created_this_run = 0
        run_id = os.urandom(4).hex()

        created_drafts = []
        for i in range(10):
            cand = {
                "channel": "GITHUB",
                "source_url": f"https://github.com/quant-org-{run_id}/cap-test-{i}/issues/{i}",
                "target_identifier": f"github_quant_org_{run_id}_cap_test_{i}_{i}",
                "repository": f"quant-org-{run_id}/cap-test-{i}",
                "author": f"user_{i}",
                "context_summary": f"Backtest overfitting diagnostic #{i}",
                "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
                "is_live_api_verified": True,
                "verification_proof": {
                    "github_api_endpoint": "https://api.github.com/search/issues",
                    "fetched_at_utc": "2026-08-30T10:00:00Z",
                    "repository_full_name": f"quant-org-{run_id}/cap-test-{i}",
                    "issue_number": i,
                    "html_url": f"https://github.com/quant-org-{run_id}/cap-test-{i}/issues/{i}",
                    "api_url": f"https://api.github.com/repos/quant-org-{run_id}/cap-test-{i}/issues/{i}",
                    "http_status": 200,
                    "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"
                },
                "context_score": 90,
                "intent_score": 80,
                "promotion_risk": 10
            }
            prospect, draft = pipeline.process_candidate_opportunity(cand)
            if draft:
                created_drafts.append(draft)

        self.assertEqual(len(created_drafts), 5)
        self.assertEqual(pipeline.drafts_created_this_run, 5)

    def test_7_historical_records_without_proof_not_verified(self):
        """Verify historical records without full HTTP 200 API proof are NOT classified as VERIFIED_EXTERNAL_SOURCE."""
        cand_no_proof = {
            "channel": "GITHUB",
            "source_url": "https://github.com/old-repo/test/issues/1",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "verification_proof": None
        }
        trust = classify_source_trust(cand_no_proof)
        self.assertNotEqual(trust, "VERIFIED_EXTERNAL_SOURCE")
        self.assertEqual(trust, "UNVERIFIED_EXTERNAL_SOURCE")

    def test_8_invalidated_drafts_not_approvable(self):
        """Verify remediated pre-existing unverified drafts are INVALIDATED_SOURCE_NOT_VERIFIED and 0 remain approvable."""
        pipeline = ProspectPipelineEngine()
        pipeline.remediate_existing_data()
        drafts = pipeline.load_all_drafts()
        pending = [d for d in drafts if d.get("approval_status") == "PENDING_HUMAN_APPROVAL"]
        self.assertEqual(len(pending), 0)

    def test_9_zero_external_publication_attempted(self):
        """Verify single cycle run in safe mode produces EXTERNAL_PUBLICATION_ATTEMPTED = False."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()):
            report = pilot.run_single_cycle()
            self.assertFalse(report["EXTERNAL_PUBLICATION_ATTEMPTED"])
            self.assertEqual(report["PROSPECT_PIPELINE"]["external_publications"], 0)
            self.assertFalse(report["PROSPECT_PIPELINE"]["external_publication_attempted"])


if __name__ == "__main__":
    unittest.main()
