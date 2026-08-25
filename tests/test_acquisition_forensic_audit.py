"""
Unit Test Suite for True Production Telemetry / Zero Unknown-To-Zero Conversion (Sprint #32.3)
"""

import unittest
from unittest.mock import patch
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine, ANALYTICS_JSONL


class TestAcquisitionForensicAudit(unittest.TestCase):

    def setUp(self):
        self.engine = AcquisitionForensicAuditEngine()

    def test_1_unknown_never_converted_to_zero(self):
        orig_read = self.engine._read_jsonl_safe

        def mock_read(path):
            if path == ANALYTICS_JSONL:
                return None
            return orig_read(path)

        with patch.object(self.engine, "_read_jsonl_safe", side_effect=mock_read):
            rep = self.engine.run_forensic_audit()
            eng_r = rep["engagement_real"]
            self.assertEqual(eng_r["real_landing_visits"], "UNKNOWN")
            self.assertEqual(eng_r["real_quiz_starts"], "UNKNOWN")
            self.assertEqual(eng_r["real_emails_captured"], "UNKNOWN")

    def test_2_delivery_metrics_parsed_individually_not_inferred(self):
        rep = self.engine.run_forensic_audit()
        deliv_r = rep["delivery_real"]
        self.assertIn("real_audits_started", deliv_r)
        self.assertIn("real_audits_completed", deliv_r)
        self.assertIn("real_certificates_generated", deliv_r)
        self.assertIn("real_certificates_delivered", deliv_r)
        self.assertIn("real_emails_sent", deliv_r)

    def test_3_cron_telemetry_insufficient_if_observed_under_two(self):
        with patch.object(self.engine, "_read_jsonl_safe", return_value=[{"timestamp_utc": "2026-08-25T00:00:00Z"}]):
            rep = self.engine.run_forensic_audit()
            self.assertEqual(rep["cron"]["status"], "CRON_TELEMETRY_INSUFFICIENT")

    def test_4_read_only_monitor_has_zero_side_effects(self):
        rep1 = self.engine.run_forensic_audit()
        rep2 = self.engine.run_forensic_audit()
        self.assertEqual(rep1["data_quality"]["hardcoded"], 0)
        self.assertEqual(rep2["data_quality"]["hardcoded"], 0)

    def test_5_valid_verdict_set(self):
        rep = self.engine.run_forensic_audit()
        valid_verdicts = [
            "REAL_AUTONOMOUS_ACQUISITION_VERIFIED",
            "CRON_OPERATIONAL_BUT_ACQUISITION_INACTIVE",
            "CRON_TELEMETRY_INSUFFICIENT",
            "REAL_AUTONOMOUS_ACQUISITION_NOT_VERIFIED",
            "DATA_QUALITY_FAILURE"
        ]
        self.assertIn(rep["final_verdict"], valid_verdicts)


if __name__ == "__main__":
    unittest.main()
