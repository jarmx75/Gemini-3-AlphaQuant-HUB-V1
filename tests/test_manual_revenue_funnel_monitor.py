"""
Unit Test Suite for Read-Only Manual Revenue Funnel Monitor (Sprint #31.2)
"""

import unittest
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor, SNAPSHOT_JSON_FILE, OBSERVATION_FILE


class TestManualRevenueFunnelMonitor(unittest.TestCase):

    def setUp(self):
        self.monitor = ManualRevenueFunnelMonitor()

    def test_1_monitor_creates_zero_tasks(self):
        snap = self.monitor.generate_snapshot()
        integ = snap["monitor_integrity"]
        self.assertEqual(integ["TASKS_CREATED_BY_MONITOR"], 0)
        self.assertEqual(integ["SIDE_EFFECTS"], 0)
        self.assertTrue(integ["CRON_UNTOUCHED"])

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
        rev = snap["revenue_summary"]
        self.assertEqual(rev["REAL_REVENUE_USD"], 0.0)
        self.assertEqual(rev["COMPLETED_PAYMENTS_COUNT"], 0)

    def test_6_funnel_contains_required_stages(self):
        snap = self.monitor.generate_snapshot()
        funnel = snap["full_funnel"]
        self.assertIn("Traffic", funnel)
        self.assertIn("Landing Visits", funnel)
        self.assertIn("Quiz Starts", funnel)
        self.assertIn("Payments Completed", funnel)
        self.assertIn("Revenue USD", funnel)

    def test_7_safe_repeated_execution(self):
        snap1 = self.monitor.generate_snapshot()
        snap2 = self.monitor.generate_snapshot()
        self.assertEqual(snap1["monitor_integrity"]["SIDE_EFFECTS"], 0)
        self.assertEqual(snap2["monitor_integrity"]["SIDE_EFFECTS"], 0)


if __name__ == "__main__":
    unittest.main()
