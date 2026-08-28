"""
Unit Test Suite for Sprint #36.1 Telemetry Invariants & Customer Isolation

Enforces 4 core invariants:
1. Historical/internal/test events CANNOT increase REAL CUSTOMER FUNNEL metrics.
2. Running the monitor or pilot multiple times DOES NOT reset session_start_utc.
3. Running --once DOES NOT trigger continuous loop.
4. Read-only monitor creates ZERO side-effects.
"""

import unittest
import sys
import os
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.revenue_observation_session import RevenueObservationSession
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint361TelemetryInvariants(unittest.TestCase):

    def test_1_historical_events_isolated_from_real_customer_funnel(self):
        """Verify historical test certificates (e.g. 114) are excluded from real customer metrics."""
        pilot = LocalAcquisitionPilot()
        report = pilot.run_single_cycle()

        # Delivery & revenue current cycle real metrics must NOT aggregate historical 114 test certificates
        self.assertEqual(report["DELIVERY"]["real_audits"], 0)
        self.assertEqual(report["DELIVERY"]["real_certificates"], 0)
        self.assertEqual(report["DELIVERY"]["real_emails_delivered"], 0)
        self.assertEqual(report["REVENUE"]["revenue_usd"], 0.0)

        # Historical certificates must be isolated under HISTORICAL / INTERNAL
        self.assertGreaterEqual(report["HISTORICAL / INTERNAL"]["historical_certificates"], 100)
        self.assertGreaterEqual(report["HISTORICAL / INTERNAL"]["historical_audits"], 100)
        self.assertEqual(report["HISTORICAL / INTERNAL"]["historical_test_payments"], 1)

    def test_2_monitor_and_pilot_preserve_session_start(self):
        """Verify running monitor or pilot multiple times preserves original session_start_utc."""
        session_info1 = RevenueObservationSession.get_session_info()
        start1 = session_info1["start_time_utc"]

        # Instantiate pilot and execute cycle
        pilot = LocalAcquisitionPilot()
        rep1 = pilot.run_single_cycle()
        start2 = rep1["SESSION"]["session_start_utc"]

        # Run monitor
        monitor = ManualRevenueFunnelMonitor()
        snap = monitor.generate_snapshot()
        start3 = snap["session"]["start_time_utc"]

        # Run pilot second cycle
        rep2 = pilot.run_single_cycle()
        start4 = rep2["SESSION"]["session_start_utc"]

        # All session_start_utc values must match exactly
        self.assertEqual(start1, start2)
        self.assertEqual(start1, start3)
        self.assertEqual(start1, start4)

    def test_3_once_flag_does_not_trigger_continuous_loop(self):
        """Verify running single cycle returns a complete report dictionary without infinite loop."""
        pilot = LocalAcquisitionPilot()
        rep = pilot.run_single_cycle()
        self.assertIsInstance(rep, dict)
        self.assertIn("SESSION", rep)
        self.assertIn("RUNTIME", rep)
        self.assertIn("STATUSES", rep)
        self.assertEqual(rep["STATUSES"]["ENGINE_EXECUTION"], "PASS")

    def test_4_read_only_monitor_zero_side_effects(self):
        """Verify ManualRevenueFunnelMonitor creates zero side effects and enforces read-only mode."""
        monitor = ManualRevenueFunnelMonitor()
        snap = monitor.generate_snapshot()

        self.assertEqual(snap["monitor_integrity"]["MONITOR_MODE"], "READ_ONLY")
        self.assertEqual(snap["monitor_integrity"]["SIDE_EFFECTS"], 0)
        self.assertTrue(snap["monitor_integrity"]["CRON_UNTOUCHED"])


if __name__ == "__main__":
    unittest.main()
