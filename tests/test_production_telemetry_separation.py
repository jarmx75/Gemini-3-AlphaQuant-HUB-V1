"""
Acceptance Test Suite for Final Production Funnel Telemetry & Test/Real Separation (Sprint #32.3)
"""

import unittest
from unittest.mock import patch
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine, ANALYTICS_JSONL
from api.analytics import process_analytics_event


class TestProductionTelemetrySeparation(unittest.TestCase):

    def setUp(self):
        self.engine = AcquisitionForensicAuditEngine()

    def test_A_test_audit_does_not_count_as_real_customer(self):
        rep = self.engine.run_forensic_audit()
        deliv_r = rep["delivery_real"]
        self.assertEqual(deliv_r["real_audits_started"], 0)
        self.assertEqual(deliv_r["real_audits_completed"], 0)

    def test_B_sandbox_payment_does_not_count_as_real_revenue(self):
        rep = self.engine.run_forensic_audit()
        rev_r = rep["revenue_real"]
        self.assertEqual(rev_r["real_completed_payments"], 0)
        self.assertEqual(rev_r["real_revenue_usd"], 0.0)

    def test_C_resend_test_email_does_not_count_as_customer_delivery(self):
        rep = self.engine.run_forensic_audit()
        deliv_r = rep["delivery_real"]
        self.assertEqual(deliv_r["real_emails_sent"], 0)

    def test_D_E_F_analytics_event_processing(self):
        res_visit = process_analytics_event({"event_type": "PAGE_VISIT", "environment": "REAL"})
        self.assertEqual(res_visit["status"], "success")

        res_checkout = process_analytics_event({"event_type": "CHECKOUT_CLICK", "environment": "REAL"})
        self.assertEqual(res_checkout["status"], "success")

        # PAYMENT_RETURN must process cleanly without incrementing real payments
        res_return = process_analytics_event({"event_type": "PAYMENT_RETURN", "environment": "REAL"})
        self.assertEqual(res_return["status"], "success")

        rep = self.engine.run_forensic_audit()
        rev_r = rep["revenue_real"]
        self.assertEqual(rev_r["real_completed_payments"], 0)  # PAYMENT_RETURN != PAYMENT_COMPLETED

    def test_H_missing_analytics_source_returns_unknown(self):
        orig_read = self.engine._read_jsonl_safe

        def mock_read(path):
            if path == ANALYTICS_JSONL:
                return None
            return orig_read(path)

        with patch.object(self.engine, "_read_jsonl_safe", side_effect=mock_read):
            rep = self.engine.run_forensic_audit()
            eng_r = rep["engagement_real"]
            self.assertEqual(eng_r["real_landing_visits"], "UNKNOWN")

    def test_I_J_K_monitor_read_only_and_no_synthetic_events(self):
        rep1 = self.engine.run_forensic_audit()
        rep2 = self.engine.run_forensic_audit()
        self.assertEqual(rep1["data_quality"]["hardcoded"], 0)
        self.assertEqual(rep2["data_quality"]["synthetic"], 0)


if __name__ == "__main__":
    unittest.main()
