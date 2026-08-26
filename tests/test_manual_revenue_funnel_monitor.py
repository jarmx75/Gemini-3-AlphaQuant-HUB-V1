"""
Unit Test Suite for Read-Only Manual Revenue Funnel Monitor (Sprint #32.4)
"""

import unittest
from unittest.mock import patch
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor, SNAPSHOT_JSON_FILE, OBSERVATION_FILE


class TestManualRevenueFunnelMonitor(unittest.TestCase):

    def setUp(self):
        self.monitor = ManualRevenueFunnelMonitor()

    def test_1_monitor_creates_zero_tasks(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["TASKS_CREATED_BY_MONITOR"], 0)

    def test_2_monitor_sends_zero_emails(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["EMAILS_SENT_BY_MONITOR"], 0)

    def test_3_monitor_creates_zero_paypal_orders(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["PAYMENTS_CREATED_BY_MONITOR"], 0)

    def test_4_monitor_executes_zero_audits(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["AUDITS_STARTED_BY_MONITOR"], 0)

    def test_5_real_revenue_excludes_test_payments(self):
        snap = self.monitor.generate_snapshot()
        ext_f = snap["external_customer_funnel"]
        self.assertEqual(ext_f["completed_payments"], 0)
        self.assertEqual(ext_f["revenue_usd"], 0.0)

    def test_6_funnel_contains_required_stages(self):
        snap = self.monitor.generate_snapshot()
        ext_f = snap["external_customer_funnel"]
        required_stages = [
            "landing_visits", "quiz_starts", "emails",
            "checkout_starts", "completed_payments", "revenue_usd",
            "audits_completed", "certificates_delivered", "emails_delivered"
        ]
        for stage in required_stages:
            self.assertIn(stage, ext_f)

    def test_7_side_effects_zero(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["SIDE_EFFECTS"], 0)
        self.assertTrue(snap["monitor_integrity"]["CRON_UNTOUCHED"])


if __name__ == "__main__":
    unittest.main()
