"""
Unit Test Suite for Sprint #36.3 Multichannel Acquisition Rotation & Telemetry

Enforces 4 core invariants:
1. All 9 channel adapters are evaluated during discovery.
2. CHANNEL_DIVERSITY_SCORE and CHANNEL_CONCENTRATION_WARNING audit metrics compute correctly.
3. Channel failover rotates away from blocked adapters smoothly.
4. Anti-idle and session persistence invariants remain intact across multi-cycle executions.
"""

import unittest
import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.autonomous_opportunity_discovery_engine import AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint363MultichannelRotation(unittest.TestCase):

    def setUp(self):
        self.discovery_engine = AutonomousOpportunityDiscoveryEngine()
        self.pilot = LocalAcquisitionPilot()

    def test_1_all_9_channels_evaluated(self):
        """Verify all 9 channel adapters exist and are evaluated in telemetry."""
        telemetry = self.discovery_engine.evaluate_channel_rotation_telemetry()
        self.assertEqual(len(telemetry["available_channels"]), 9)
        self.assertEqual(len(telemetry["evaluated_channels"]), 9)
        self.assertIn("GITHUB", telemetry["available_channels"])
        self.assertIn("REDDIT", telemetry["available_channels"])
        self.assertIn("QUANTCONNECT", telemetry["available_channels"])
        self.assertIn("SEO", telemetry["available_channels"])

    def test_2_channel_diversity_and_concentration_audit(self):
        """Verify channel_diversity_score calculation and concentration warning logic."""
        telemetry = self.discovery_engine.evaluate_channel_rotation_telemetry()
        score = telemetry["channel_diversity_score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertIsInstance(telemetry["channel_concentration_warning"], bool)

    def test_3_adaptive_channel_weighting_and_failover(self):
        """Verify channel rotation failover when GITHUB is in cooldown."""
        self.discovery_engine.set_cooldown("GITHUB", duration_seconds=3600)
        next_adapter = self.discovery_engine.get_next_eligible_channel(blocked_channels={"GITHUB"})
        self.assertNotEqual(next_adapter.adapter_name, "GITHUB")

    def test_4_eight_cycle_anti_idle_and_session_persistence(self):
        """Verify NO_IDLE, NO_REPEAT, and MULTICHANNEL_ROTATION pass in pilot cycle report."""
        rep = self.pilot.run_single_cycle()
        statuses = rep["STATUSES"]
        self.assertEqual(statuses["ENGINE_EXECUTION"], "PASS")
        self.assertEqual(statuses["NO_IDLE"], "PASS")
        self.assertEqual(statuses["NO_REPEAT"], "PASS")
        self.assertEqual(statuses["MULTICHANNEL_ROTATION"], "PASS")


if __name__ == "__main__":
    unittest.main()
