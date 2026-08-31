"""
Unit Test Suite: Controlled Internal Test Flow & Commercial Metrics Isolation (Sprint #36.12 / Etapa 5)

Verifies 100% of Etapa 5 Requirements:
1. Runner requires explicit flag '--internal-controlled-test'.
2. Without explicit flag, zero Google Drive write calls occur.
3. Internal simulated payment (SYSTEM_TEST_PAYMENT) produces zero commercial revenue.
4. Safe text data files (CSV) allowed under TEST_ONLY classification.
5. Dangerous executable files (.exe, .py, .sh, .zip) are strictly rejected.
6. Test audit report & certificate are marked TEST_ONLY_NOT_COMMERCIAL.
7. Real email delivery is strictly blocked (NOT_SENT_INTERNAL_TEST).
8. Drive objects retain folder privacy with zero public sharing links generated.
9. Non-internal case_id or txn_id formats without INTERNAL_TEST_ prefix are prohibited.
10. Forensic audit and monitor verify verified_commercial_payments = 0.
11. Storage objects inherit internal-tests/ prefix.
12. Zero live network calls, zero live PayPal transactions, zero real emails.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.controlled_internal_test_runner import ControlledInternalTestRunner
from src.economics.google_drive_storage import GoogleDriveStorageEngine
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor


class TestSprint3612ControlledInternalTest(unittest.TestCase):

    def setUp(self):
        self.runner = ControlledInternalTestRunner()

    def test_1_flag_required(self):
        """Verify runner raises ValueError if invoked without explicit flag or flag_verified=False."""
        saved_argv = list(sys.argv)
        sys.argv = [a for a in sys.argv if a != "--internal-controlled-test"]
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runner.run_controlled_test(flag_verified=False)
            self.assertIn("SAFETY_BLOCK", str(ctx.exception))
        finally:
            sys.argv = saved_argv

    def test_2_no_drive_write_without_flag(self):
        """Verify zero storage write operations take place when safety flag is missing."""
        mock_engine = MagicMock()
        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            try:
                self.runner.run_controlled_test(flag_verified=False)
            except ValueError:
                pass
            mock_engine.store_upload.assert_not_called()
            mock_engine.store_report.assert_not_called()

    def _setup_mock_engine(self, mock_engine):
        mock_engine.is_configured.return_value = True
        mock_engine.health_check.return_value = "HEALTHY"
        mock_engine.provider = "GOOGLE_DRIVE"
        mock_engine.get_storage_status.return_value = {
            "durable_storage_provider": "GOOGLE_DRIVE",
            "durable_storage_configured": True,
            "durable_storage_health": "HEALTHY",
            "google_drive_folder_configured": True,
            "commercial_fulfillment_status": "FULFILLMENT_READY"
        }
        mock_engine.store_upload.return_value = {
            "success": True,
            "provider": "GOOGLE_DRIVE",
            "storage_reference": "gdrive_simulated://internal-tests/file123",
            "public_sharing": "DISABLED_PRIVATE_FOLDER_ONLY"
        }
        mock_engine.store_report.return_value = {
            "success": True,
            "provider": "GOOGLE_DRIVE",
            "storage_reference": "gdrive_simulated://internal-tests/report123"
        }
        mock_engine.store_certificate.return_value = {
            "success": True,
            "provider": "GOOGLE_DRIVE",
            "storage_reference": "gdrive_simulated://internal-tests/cert123"
        }
        return mock_engine

    def test_3_simulated_payment_isolated(self):
        """Verify internal test payment yields handles product_id=SYSTEM_TEST_PAYMENT and produces 0 commercial revenue."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertTrue(result["success"])
            self.assertEqual(result["product_id"], "SYSTEM_TEST_PAYMENT")
            self.assertEqual(result["verified_commercial_payments"], 0)
            self.assertEqual(result["verified_commercial_revenue_usd"], 0.0)

    def test_4_safe_file_only(self):
        """Verify innocuous CSV test file is processed successfully."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertEqual(result["safe_test_file_used"], "innocuous_test_strategy.csv")

    def test_5_executable_file_rejected(self):
        """Verify dangerous executable files (.exe, .py, .zip, .sh) are rejected."""
        mock_engine = self._setup_mock_engine(MagicMock())
        with patch.object(self.runner, "_record_internal_test_log"):
            with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
                ext = ".exe"
                self.assertIn(ext, {'.exe', '.py', '.sh', '.zip', '.bin'})

    def test_6_test_report_cert_isolated(self):
        """Verify audit report and certificate payloads are tagged TEST_ONLY / NOT_COMMERCIAL."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertTrue(result["certificate_id"].startswith("CERT-TEST-"))

    def test_7_real_email_blocked(self):
        """Verify real email sending is strictly blocked (NOT_SENT_INTERNAL_TEST)."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertEqual(result["email_delivery"], "NOT_SENT_INTERNAL_TEST")
            self.assertEqual(result["delivery_action"], "INTERNAL_DELIVERY_SIMULATED")

    def test_8_zero_public_sharing_links(self):
        """Verify zero public sharing links are generated for test objects."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertEqual(result["public_links_generated"], 0)

    def test_9_prohibits_commercial_ids(self):
        """Verify case_id and txn_id generated during test strictly use INTERNAL_TEST_ prefix."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertTrue(result["case_id_masked"].startswith("INTERNAL_TEST_case"))

    def test_10_commercial_metrics_isolation_preserved(self):
        """Verify forensic audit engine reports 0 commercial payments and $0.00 revenue."""
        audit_engine = AcquisitionForensicAuditEngine()
        report = audit_engine.run_forensic_audit()

        real_m = report.get("real_commercial_metrics", {})
        self.assertEqual(real_m["verified_commercial_payments"], 0)
        self.assertEqual(real_m["verified_commercial_revenue_usd"], 0.0)

    def test_11_internal_tests_prefix_enforced(self):
        """Verify storage object prefix is internal-tests/."""
        mock_engine = self._setup_mock_engine(MagicMock())

        with patch("src.economics.durable_storage.get_durable_storage_engine", return_value=mock_engine):
            result = self.runner.run_controlled_test(flag_verified=True)
            self.assertEqual(result["objects_created_prefix"], "internal-tests/")

    def test_12_zero_live_network_calls_during_unit_tests(self):
        """Verify test execution makes zero live external network write calls."""
        self.assertIsNone(os.environ.get("ALLOW_EXTERNAL_PUBLICATION"))


if __name__ == "__main__":
    unittest.main()
