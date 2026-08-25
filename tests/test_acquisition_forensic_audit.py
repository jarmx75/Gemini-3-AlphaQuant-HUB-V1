"""
Unit Test Suite for Forensic Telemetry & Real Execution Audit (Sprint #32.1)
"""

import unittest, json
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine


class TestAcquisitionForensicAudit(unittest.TestCase):

    def setUp(self):
        self.engine = AcquisitionForensicAuditEngine()

    def test_1_no_numeric_fallbacks_for_missing_sources(self):
        rep = self.engine.run_forensic_audit()
        dq = rep["data_quality"]
        self.assertEqual(dq["hardcoded"], 0)
        self.assertEqual(dq["fallback"], 0)
        self.assertEqual(dq["synthetic"], 0)

    def test_2_elapsed_time_calculated_dynamically(self):
        rep = self.engine.run_forensic_audit()
        obs = rep["observation"]
        self.assertIn("start", obs)
        self.assertIn("now", obs)
        self.assertTrue(isinstance(obs["elapsed"], (int, float)) or obs["elapsed"] == "UNKNOWN")

    def test_3_unknown_state_preserves_string_not_zero(self):
        # Temporarily mock missing file path
        original_obs_file = self.engine._read_json_safe
        self.engine._read_json_safe = lambda p: None

        rep = self.engine.run_forensic_audit()
        self.assertEqual(rep["observation"]["elapsed"], "UNKNOWN")
        self.assertEqual(rep["outreach"]["published"], "UNKNOWN")

        # Restore
        self.engine._read_json_safe = original_obs_file

    def test_4_valid_final_verdicts(self):
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
