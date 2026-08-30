import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path bootstrap check
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor
from src.economics.outreach_execution_engine import RealOutreachExecutionEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint365SafeModeAndAuditFixes(unittest.TestCase):
    """Test suite for Sprint #36.5 safe mode defaults, script execution, delta consistency, and telemetry isolation."""

    def test_1_audit_and_monitor_scripts_load_from_root(self):
        """Verify audit and monitor engines initialize and run cleanly without ModuleNotFoundError."""
        audit_engine = AcquisitionForensicAuditEngine()
        audit_report = audit_engine.run_forensic_audit()
        self.assertIsNotNone(audit_report)
        self.assertIn("session", audit_report)

        monitor_engine = ManualRevenueFunnelMonitor()
        snapshot = monitor_engine.generate_snapshot()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["monitor_integrity"]["MONITOR_MODE"], "READ_ONLY")

    def test_2_default_mode_blocks_external_publication(self):
        """Verify default acquisition pilot mode DISCOVERY_AND_DRAFT_ONLY blocks external publication."""
        pilot = LocalAcquisitionPilot()
        self.assertFalse(pilot.allow_external_publication)
        self.assertEqual(pilot.operating_mode, "DISCOVERY_AND_DRAFT_ONLY")

        outreach_engine = RealOutreachExecutionEngine()
        post_res = outreach_engine.post_github_issue_comment(
            "https://api.github.com/repos/test/repo/issues/1/comments",
            "Test body",
            allow_external_publication=False
        )
        self.assertFalse(post_res["external_sent"])
        self.assertFalse(post_res["publication_confirmed"])
        self.assertEqual(post_res["state"], "ACTION_GENERATED_LOCALLY")
        self.assertEqual(post_res["reason"], "EXTERNAL_PUBLICATION_REQUIRES_EXPLICIT_APPROVAL")

    def test_3_explicit_flag_required_for_external_publication(self):
        """Verify external publication is allowed ONLY when allow_external_publication=True."""
        pilot_enabled = LocalAcquisitionPilot(allow_external_publication=True)
        self.assertTrue(pilot_enabled.allow_external_publication)
        self.assertEqual(pilot_enabled.operating_mode, "EXTERNAL_PUBLICATION_ALLOWED")

        outreach_engine = RealOutreachExecutionEngine()
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

                res = outreach_engine.post_github_issue_comment(
                    "https://api.github.com/repos/test/repo/issues/1/comments",
                    "Test body",
                    allow_external_publication=True
                )
                self.assertTrue(res["external_sent"])
                self.assertTrue(res["publication_confirmed"])
                self.assertEqual(res["state"], "PUBLICATION_CONFIRMED")

    def test_4_delta_metrics_consistency(self):
        """Verify DELTA metrics accurately calculate net session changes per cycle."""
        pilot = LocalAcquisitionPilot(allow_external_publication=False)
        rep = pilot.run_single_cycle()
        delta = rep.get("DELTA", {})
        self.assertEqual(delta.get("opportunities_evaluated_delta"), 90)
        self.assertGreaterEqual(delta.get("targets_selected_delta"), 0)
        self.assertEqual(delta.get("actions_sent_externally_delta"), 0)

    def test_5_internal_test_synthetic_data_isolation(self):
        """Verify internal/test/synthetic data are excluded from real customer metrics."""
        audit_engine = AcquisitionForensicAuditEngine()
        report = audit_engine.run_forensic_audit()

        cust_funnel = report.get("external_customer_funnel", {})
        self.assertEqual(cust_funnel.get("completed_payments"), 0)
        self.assertEqual(cust_funnel.get("revenue_usd"), 0.0)

        # Internal/test items must be tracked under owner_test_funnel
        owner_funnel = report.get("owner_test_funnel", {})
        self.assertIn("test_payments", owner_funnel)


if __name__ == "__main__":
    unittest.main()
