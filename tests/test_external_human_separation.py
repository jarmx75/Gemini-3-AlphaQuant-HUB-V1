"""
Acceptance Test Suite for Final Funnel Telemetry Reconciliation & External Human Separation (Sprint #32.4)
"""

import unittest
from unittest.mock import patch
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine, ANALYTICS_JSONL
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor
from api.analytics import process_analytics_event


class TestExternalHumanSeparation(unittest.TestCase):

    def setUp(self):
        self.audit_engine = AcquisitionForensicAuditEngine()
        self.monitor = ManualRevenueFunnelMonitor()

    def test_A_B_owner_visit_and_internal_test_separated_from_external_human(self):
        res_owner = process_analytics_event({"event_type": "PAGE_VISIT", "actor_type": "OWNER"})
        self.assertEqual(res_owner["status"], "success")

        res_test = process_analytics_event({"event_type": "PAGE_VISIT", "actor_type": "INTERNAL_TEST"})
        self.assertEqual(res_test["status"], "success")

        rep = self.audit_engine.run_forensic_audit()
        ext_f = rep["external_customer_funnel"]
        owner_f = rep["owner_test_funnel"]

        # Owner/test visits increment owner_landing_visits, NOT external landing_visits
        self.assertEqual(ext_f["landing_visits"], 0)
        self.assertGreater(owner_f["owner_landing_visits"], 0)

    def test_C_unknown_remains_unknown_if_source_missing(self):
        orig_read = self.audit_engine._read_jsonl_safe

        def mock_read(path):
            if path == ANALYTICS_JSONL:
                return None
            return orig_read(path)

        with patch.object(self.audit_engine, "_read_jsonl_safe", side_effect=mock_read):
            rep = self.audit_engine.run_forensic_audit()
            ext_f = rep["external_customer_funnel"]
            self.assertEqual(ext_f["landing_visits"], "UNKNOWN")

    def test_D_E_F_real_external_payment_requirements(self):
        process_analytics_event({"event_type": "CHECKOUT_CLICK", "actor_type": "EXTERNAL_HUMAN"})
        process_analytics_event({"event_type": "PAYMENT_RETURN", "actor_type": "EXTERNAL_HUMAN"})

        rep = self.audit_engine.run_forensic_audit()
        ext_f = rep["external_customer_funnel"]

        self.assertGreaterEqual(ext_f["checkout_starts"], 1)
        self.assertGreaterEqual(ext_f["payment_returns"], 1)
        self.assertEqual(ext_f["completed_payments"], 0)  # CHECKOUT_CLICK / PAYMENT_RETURN != PAYMENT_COMPLETED
        self.assertEqual(ext_f["revenue_usd"], 0.0)

    def test_G_H_monitor_manual_parity_and_read_only_integrity(self):
        rep = self.audit_engine.run_forensic_audit()
        snap = self.monitor.generate_snapshot()

        integ = snap["monitor_integrity"]
        self.assertEqual(integ["MONITOR_MODE"], "READ_ONLY")
        self.assertEqual(integ["SIDE_EFFECTS"], 0)

        # Exact parity check
        self.assertEqual(snap["external_customer_funnel"], rep["external_customer_funnel"])
        self.assertEqual(snap["owner_test_funnel"], rep["owner_test_funnel"])
        self.assertEqual(snap["conversion"], rep["conversion"])

    def test_I_J_conversion_rates_handle_zero_denominator(self):
        rep = self.audit_engine.run_forensic_audit()
        conv = rep["conversion"]
        # With 0 completed payments, checkout_to_payment must be UNKNOWN or 0.0% if checkouts > 0
        self.assertIn(conv["landing_to_payment"], ["0.0%", "UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
