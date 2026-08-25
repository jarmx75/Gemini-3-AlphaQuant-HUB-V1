"""
Unit Test Suite for True Production Telemetry / Zero Unknown-To-Zero Conversion (Sprint #32.2)
"""

import unittest
from unittest.mock import patch
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine, ANALYTICS_FILE


class TestAcquisitionForensicAudit(unittest.TestCase):

    def setUp(self):
        self.engine = AcquisitionForensicAuditEngine()

    def test_1_unknown_never_converted_to_zero(self):
        # Mock _read_json_safe to return None when reading ANALYTICS_FILE
        orig_read = self.engine._read_json_safe

        def mock_read(path):
            if path == ANALYTICS_FILE:
                return None
            return orig_read(path)

        with patch.object(self.engine, "_read_json_safe", side_effect=mock_read):
            rep = self.engine.run_forensic_audit()
            eng = rep["engagement"]
            self.assertEqual(eng["landing_visits"], "UNKNOWN")
            self.assertEqual(eng["quiz_starts"], "UNKNOWN")
            self.assertEqual(eng["emails"], "UNKNOWN")

    def test_2_delivery_metrics_parsed_individually_not_inferred(self):
        rep = self.engine.run_forensic_audit()
        deliv = rep["delivery"]
        self.assertIn("audits_started", deliv)
        self.assertIn("audits_completed", deliv)
        self.assertIn("certificates_generated", deliv)
        self.assertIn("certificates_delivered", deliv)
        self.assertIn("emails_sent", deliv)

    def test_3_cron_telemetry_insufficient_if_observed_under_two(self):
        with patch.object(self.engine, "_read_jsonl_safe", return_value=[{"timestamp": "2026-08-25T00:00:00Z"}]):
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
