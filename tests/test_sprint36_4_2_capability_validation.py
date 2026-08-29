import unittest
import os
from unittest.mock import patch, MagicMock

from src.economics.autonomous_opportunity_discovery_engine import (
    AutonomousOpportunityDiscoveryEngine,
    OpportunityScorer,
    GitHubAdapter,
    RedditAdapter,
    QuantConnectAdapter,
    SEOAdapter,
    TechnicalCommunitiesAdapter,
    DeveloperForumsAdapter,
    B2BDirectoriesAdapter,
    MarketplacesAdapter,
    ContentDiscoveryAdapter
)
from src.economics.outreach_execution_engine import RealOutreachExecutionEngine


class TestSprint3642CapabilityValidation(unittest.TestCase):
    """Test suite for Sprint #36.4.2 Channel Capability Model & Action Execution Invariants."""

    def test_1_channel_capability_declarations(self):
        """Verify all 9 adapters explicitly declare capability attributes."""
        engine = AutonomousOpportunityDiscoveryEngine()
        self.assertEqual(len(engine.adapters), 9)

        for adapter in engine.adapters:
            caps = adapter.get_capabilities()
            self.assertTrue(caps.get("discovery_supported"))
            self.assertTrue(caps.get("qualification_supported"))
            self.assertTrue(caps.get("content_generation_supported"))
            self.assertIn("automated_submission_supported", caps)
            self.assertIn("publication_confirmation_supported", caps)
            self.assertIn("capability_mode", caps)

            if adapter.adapter_name == "GITHUB":
                self.assertTrue(caps["automated_submission_supported"])
                self.assertEqual(caps["capability_mode"], "AUTOMATION_READY")
            else:
                self.assertFalse(caps["automated_submission_supported"])
                self.assertIn(caps["capability_mode"], ["DISCOVERY_ONLY", "AUTH_REQUIRED"])

    def test_2_tier_assignment_with_channel_capabilities(self):
        """Verify Tier A requires automated_submission_supported == True."""
        gh_adapter = GitHubAdapter()
        reddit_adapter = RedditAdapter()

        high_score_opp = {
            "channel": "GITHUB",
            "context_score": 90,
            "intent_score": 85,
            "promotion_risk": 10,
            "duplicate_risk": 0
        }

        # On GitHub (automated_submission_supported=True) -> TIER_A_AUTO_PUBLISH
        res_gh = OpportunityScorer.evaluate_publication_guards(high_score_opp, channel_adapter=gh_adapter)
        self.assertTrue(res_gh.is_qual)
        self.assertEqual(res_gh.action_tier, "TIER_A_AUTO_PUBLISH")

        # On Reddit (automated_submission_supported=False) -> TIER_B_VALUE_CONTRIBUTION
        high_score_opp["channel"] = "REDDIT"
        res_reddit = OpportunityScorer.evaluate_publication_guards(high_score_opp, channel_adapter=reddit_adapter)
        self.assertTrue(res_reddit.is_qual)
        self.assertEqual(res_reddit.action_tier, "TIER_B_VALUE_CONTRIBUTION")

    def test_3_action_attempt_sum_invariant(self):
        """Verify actions_attempted == actions_generated_locally + actions_sent_externally + action_failed + action_blocked."""
        engine = AutonomousOpportunityDiscoveryEngine()
        telemetry = engine.evaluate_channel_rotation_telemetry()
        per_channel = telemetry.get("per_channel_metrics", {})

        for ch, m in per_channel.items():
            attempted = m.get("actions_attempted", 0)
            local = m.get("actions_generated_locally", 0)
            external = m.get("actions_sent_externally", 0)
            failed = m.get("failures", 0)
            blocked = m.get("blocked", 0)
            self.assertEqual(attempted, local + external + failed + blocked)

    def test_4_github_external_action_submission(self):
        """Verify GitHub API action posting handling and remote URL capture."""
        outreach_engine = RealOutreachExecutionEngine()

        # Case A: Without GITHUB_TOKEN -> ACTION_GENERATED_LOCALLY
        with patch.object(outreach_engine, "get_github_token", return_value=None):
            res = outreach_engine.post_github_issue_comment("https://api.github.com/repos/test/repo/issues/1/comments", "Test body")
            self.assertFalse(res["external_sent"])
            self.assertFalse(res["publication_confirmed"])
            self.assertEqual(res["state"], "ACTION_GENERATED_LOCALLY")

        # Case B: With GITHUB_TOKEN and successful API call -> PUBLICATION_CONFIRMED
        with patch.object(outreach_engine, "get_github_token", return_value="mock_token_123"):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.status = 201
                mock_resp.read.return_value = b'{"id": 123, "html_url": "https://github.com/test/repo/issues/1#issuecomment-123"}'
                
                mock_verify_resp = MagicMock()
                mock_verify_resp.status = 200
                mock_verify_resp.read.return_value = b'{"id": 123, "html_url": "https://github.com/test/repo/issues/1#issuecomment-123"}'

                mock_urlopen.side_effect = [
                    MagicMock(__enter__=MagicMock(return_value=mock_resp)),
                    MagicMock(__enter__=MagicMock(return_value=mock_verify_resp))
                ]

                res = outreach_engine.post_github_issue_comment("https://api.github.com/repos/test/repo/issues/1/comments", "Test body")
                self.assertTrue(res["external_sent"])
                self.assertTrue(res["publication_confirmed"])
                self.assertEqual(res["state"], "PUBLICATION_CONFIRMED")
                self.assertEqual(res["comment_url"], "https://github.com/test/repo/issues/1#issuecomment-123")


if __name__ == "__main__":
    unittest.main()
