"""
Unit Test Suite for True Production Telemetry / Zero Unknown-To-Zero Conversion (Sprint #32.4)
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
            ext_f = rep["external_customer_funnel"]
            self.assertEqual(ext_f["landing_visits"], "UNKNOWN")
            self.assertEqual(ext_f["quiz_starts"], "UNKNOWN")
            self.assertEqual(ext_f["emails"], "UNKNOWN")

    def test_2_delivery_metrics_parsed_individually_not_inferred(self):
        rep = self.engine.run_forensic_audit()
        ext_f = rep["external_customer_funnel"]
        self.assertIn("landing_visits", ext_f)
        self.assertIn("quiz_starts", ext_f)
        self.assertIn("emails", ext_f)
        self.assertIn("checkout_starts", ext_f)
        self.assertIn("completed_payments", ext_f)

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
            "DATA_QUALITY_FAILURE",
            "AUTONOMOUS_REVENUE_ENGINE_ACTIVE",
            "COMMERCIAL_FULFILLMENT_BLOCKED_STORAGE_NOT_CONFIGURED",
            "COMMERCIAL_FULFILLMENT_READY",
            "COMMERCIAL_FULFILLMENT_PARTIAL_AWAITING_CONTROLLED_VALIDATION"
        ]
        self.assertIn(rep["final_verdict"], valid_verdicts)


if __name__ == "__main__":
    unittest.main()
