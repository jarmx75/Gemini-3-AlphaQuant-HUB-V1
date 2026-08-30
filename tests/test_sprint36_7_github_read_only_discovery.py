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
from src.economics.prospect_pipeline_engine import ProspectPipelineEngine
from src.economics.autonomous_opportunity_discovery_engine import GitHubAdapter, AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


def mock_github_api_search_response(items=None, status=200, remaining=50):
    if items is None:
        items = [
            {
                "html_url": "https://github.com/quant-research-group/alpha-engine/issues/105",
                "repository_url": "https://api.github.com/repos/quant-research-group/alpha-engine",
                "number": 105,
                "title": "Severe backtest overfitting detected in walk-forward cross validation",
                "body": "How to prevent lookahead bias and reduce backtest overfitting when calculating out-of-sample Sharpe ratios?",
                "user": {"login": "external_trader_42"},
                "url": "https://api.github.com/repos/quant-research-group/alpha-engine/issues/105",
                "created_at": "2026-08-30T10:00:00Z",
                "updated_at": "2026-08-30T10:30:00Z"
            }
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


class TestSprint367GitHubReadOnlyDiscovery(unittest.TestCase):
    """Test suite for Sprint #36.7 / Etapa 3 Read-Only GitHub Search API Discovery Adapter."""

    def test_1_only_get_requests_issued(self):
        """Verify GitHubAdapter issues ONLY HTTP GET requests."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()) as mock_urlopen:
            adapter.discover_opportunities(max_queries=1)
            self.assertTrue(mock_urlopen.called)
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_method(), "GET")
            self.assertIn("api.github.com/search/issues", req.full_url)
            self.assertFalse(adapter.publication_capability)
            self.assertFalse(adapter.automated_submission_supported)

    def test_2_owner_repository_blocked(self):
        """Verify issues from self-owned repos (jarmx75) are blocked as BLOCKED_SELF_TARGET."""
        self_item = {
            "html_url": "https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1",
            "repository_url": "https://api.github.com/repos/jarmx75/Gemini-3-AlphaQuant-HUB-V1",
            "number": 1,
            "title": "Sharpe ratio degradation audit",
            "user": {"login": "jarmx75"},
            "created_at": "2026-08-30T10:00:00Z"
        }
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response([self_item])):
            results = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(results), 1)
            cand = results[0]
            self.assertTrue(cand["self_target_flag"])
            self.assertEqual(cand["prospect_status"], "BLOCKED_SELF_TARGET")
            self.assertEqual(cand["source_trust_classification"], "INTERNAL_OR_SELF")

    def test_3_valid_external_issue_verified_source(self):
        """Verify valid third-party issue from GitHub API GET response receives VERIFIED_EXTERNAL_SOURCE."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()):
            results = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(results), 1)
            cand = results[0]
            self.assertFalse(cand["self_target_flag"])
            self.assertEqual(cand["source_trust_classification"], "VERIFIED_EXTERNAL_SOURCE")
            self.assertTrue(cand["is_live_api_verified"])
            self.assertIn("verification_proof", cand)
            self.assertEqual(cand["verification_proof"]["source_trust_classification"], "VERIFIED_EXTERNAL_SOURCE")

    def test_4_duplicate_issue_blocked(self):
        """Verify duplicate issue URL is blocked as BLOCKED_DUPLICATE by prospect pipeline."""
        pipeline = ProspectPipelineEngine()
        test_id = os.urandom(4).hex()
        candidate = {
            "channel": "GITHUB",
            "source_url": f"https://github.com/external-quant/repo-{test_id}/issues/42",
            "target_identifier": f"github_external_quant_repo_{test_id}_42",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "verification_proof": {
                "github_api_endpoint": "https://api.github.com/search/issues",
                "fetched_at_utc": "2026-08-30T10:00:00Z",
                "repository_full_name": f"external-quant/repo-{test_id}",
                "issue_number": 42,
                "html_url": f"https://github.com/external-quant/repo-{test_id}/issues/42",
                "api_url": f"https://api.github.com/repos/external-quant/repo-{test_id}/issues/42",
                "http_status": 200,
                "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"
            },
            "context_score": 85,
            "intent_score": 80,
            "promotion_risk": 10
        }
        prospect1, draft1 = pipeline.process_candidate_opportunity(candidate)
        self.assertIn(prospect1["status"], ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"])

        prospect2, draft2 = pipeline.process_candidate_opportunity(candidate)
        self.assertEqual(prospect2["status"], "BLOCKED_DUPLICATE")
        self.assertIsNone(draft2)

    def test_5_low_relevance_issue_blocked(self):
        """Verify issue with low context/intent score is blocked as BLOCKED_LOW_RELEVANCE."""
        low_item = {
            "html_url": f"https://github.com/random/repo/issues/{os.urandom(2).hex()}",
            "repository_url": "https://api.github.com/repos/random/repo",
            "number": 1,
            "title": "unrelated readme typo fix",
            "body": "fixed a typo in line 10",
            "user": {"login": "random_user"},
            "created_at": "2026-08-30T10:00:00Z"
        }
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response([low_item])):
            results = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(results), 1)
            cand = results[0]
            self.assertEqual(cand["prospect_status"], "BLOCKED_LOW_RELEVANCE")

    def test_6_synthetic_template_not_verified(self):
        """Verify mock or template items do NOT receive VERIFIED_EXTERNAL_SOURCE."""
        test_id = os.urandom(4).hex()
        candidate = {
            "channel": "GITHUB",
            "source_url": f"https://github.com/mock/repo-{test_id}/issues/1",
            "target_identifier": f"github_mock_{test_id}_1",
            "is_synthetic": True
        }
        pipeline = ProspectPipelineEngine()
        prospect, draft = pipeline.process_candidate_opportunity(candidate)
        self.assertNotEqual(prospect["source_trust_classification"], "VERIFIED_EXTERNAL_SOURCE")
        self.assertEqual(prospect["status"], "BLOCKED_TEMPLATE_OR_SYNTHETIC")

    def test_7_valid_prospect_creates_local_draft(self):
        """Verify valid VERIFIED_EXTERNAL_SOURCE prospect creates a local draft with PENDING_HUMAN_APPROVAL."""
        pipeline = ProspectPipelineEngine()
        pipeline.drafts_created_this_run = 0
        test_id = os.urandom(4).hex()
        candidate = {
            "channel": "GITHUB",
            "source_url": f"https://github.com/real-quant-dev/backtest-lib-{test_id}/issues/7",
            "target_identifier": f"github_real_quant_dev_{test_id}_7",
            "repository": f"real-quant-dev/backtest-lib-{test_id}",
            "author": "trader_alice",
            "context_summary": "Walk-forward optimization overfitting diagnostic | Issue details",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "verification_proof": {
                "github_api_endpoint": "https://api.github.com/search/issues",
                "fetched_at_utc": "2026-08-30T10:00:00Z",
                "repository_full_name": f"real-quant-dev/backtest-lib-{test_id}",
                "issue_number": 7,
                "html_url": f"https://github.com/real-quant-dev/backtest-lib-{test_id}/issues/7",
                "api_url": f"https://api.github.com/repos/real-quant-dev/backtest-lib-{test_id}/issues/7",
                "http_status": 200,
                "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"
            },
            "context_score": 90,
            "intent_score": 85,
            "promotion_risk": 10
        }
        prospect, draft = pipeline.process_candidate_opportunity(candidate)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["approval_status"], "PENDING_HUMAN_APPROVAL")
        self.assertEqual(draft["external_publication_status"], "NOT_ATTEMPTED")
        self.assertTrue(draft["human_approval_required"])
        self.assertEqual(draft["source_trust_classification"], "VERIFIED_EXTERNAL_SOURCE")

    def test_8_zero_external_publication_attempted(self):
        """Verify pilot cycle in safe mode produces EXTERNAL_PUBLICATION_ATTEMPTED = False."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()):
            report = pilot.run_single_cycle()
            self.assertFalse(report["EXTERNAL_PUBLICATION_ATTEMPTED"])
            self.assertEqual(report["ACTIONS"]["actions_sent_externally"], 0)
            self.assertEqual(report["ACTIONS"]["publications_confirmed"], 0)

    def test_9_rate_limit_and_error_handling(self):
        """Verify rate limit (HTTP 403) and missing token states are handled cleanly in telemetry."""
        adapter = GitHubAdapter()
        err_resp = urllib.error.HTTPError(
            url="https://api.github.com/search/issues",
            code=403,
            msg="API rate limit exceeded",
            hdrs={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": "60"},
            fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err_resp):
            results = adapter.discover_opportunities(max_queries=1)
            self.assertEqual(len(results), 0)
            self.assertEqual(adapter.telemetry["github_api_requests_made_current_cycle"], 1)
            self.assertEqual(adapter.telemetry["github_api_rate_limit_status_current_cycle"]["status"], "RATE_LIMITED")

    def test_10_conservative_run_limits_respected(self):
        """Verify per-run limits (max 3 API calls) are respected by GitHubAdapter."""
        adapter = GitHubAdapter()
        with patch("urllib.request.urlopen", return_value=mock_github_api_search_response()) as mock_urlopen:
            results = adapter.discover_opportunities(max_queries=5)
            self.assertLessEqual(adapter.telemetry["github_api_requests_made_current_cycle"], 3)


if __name__ == "__main__":
    unittest.main()
