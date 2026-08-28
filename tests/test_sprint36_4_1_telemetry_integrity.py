"""
Unit Test Suite for Sprint #36.4.1 External Action Telemetry & Target Execution Integrity

Enforces 4 core invariants:
1. Tier accounting equation: tier_a + tier_b + tier_c == targets_selected.
2. Action state order: publications_confirmed <= actions_sent_externally <= actions_attempted <= targets_selected.
3. Channel accounting strictness: channels_with_actions strictly counts channels with actions_sent_externally > 0.
4. Append-only event history logging: external_acquisition_event_history.jsonl receives structured event records.
"""

import unittest
import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.autonomous_opportunity_discovery_engine import OpportunityScorer, AutonomousOpportunityDiscoveryEngine
from scripts.local_acquisition_pilot import LocalAcquisitionPilot


class TestSprint3641TelemetryIntegrity(unittest.TestCase):

    def setUp(self):
        self.discovery_engine = AutonomousOpportunityDiscoveryEngine()
        self.pilot = LocalAcquisitionPilot()

    def test_1_tier_and_target_accounting_invariants(self):
        """Verify tier_a_targets + tier_b_targets + tier_c_targets == targets_selected."""
        rep = self.pilot.run_single_cycle()
        opps = rep["OPPORTUNITIES"]
        targets_selected = opps["targets_selected"]
        tier_a = opps["tier_a_targets"]
        tier_b = opps["tier_b_targets"]
        tier_c = opps["tier_c_targets"]

        self.assertEqual(tier_a + tier_b + tier_c, targets_selected)
        self.assertEqual(rep["STATUSES"]["TIER_ACCOUNTING"], "PASS")

    def test_2_action_state_flow_and_external_proof(self):
        """Verify publications_confirmed <= actions_sent_externally <= actions_attempted <= targets_selected."""
        rep = self.pilot.run_single_cycle()
        opps = rep["OPPORTUNITIES"]
        actions = rep["ACTIONS"]

        self.assertLessEqual(actions["actions_attempted"], opps["targets_selected"])
        self.assertLessEqual(actions["actions_sent_externally"], actions["actions_attempted"])
        self.assertLessEqual(actions["publications_confirmed"], actions["actions_sent_externally"])

    def test_3_channel_accounting_and_action_isolation(self):
        """Verify channels_with_actions strictly counts channels with actions_sent_externally > 0."""
        rep = self.pilot.run_single_cycle()
        ch = rep["CHANNEL TELEMETRY"]
        per_ch = ch["per_channel"]

        expected_action_channels = len([c for c, m in per_ch.items() if m.get("actions_sent_externally", 0) > 0])
        expected_pub_channels = len([c for c, m in per_ch.items() if m.get("publications_confirmed", 0) > 0])

        self.assertEqual(ch["channels_with_actions"], expected_action_channels)
        self.assertEqual(ch["channels_with_publications"], expected_pub_channels)
        self.assertEqual(rep["STATUSES"]["CHANNEL_ACCOUNTING"], "PASS")

    def test_4_event_history_jsonl_logging(self):
        """Verify external_acquisition_event_history.jsonl receives structured event records."""
        event_history_file = PROJECT_ROOT / "logs" / "portfolio" / "external_acquisition_event_history.jsonl"
        self.assertTrue(event_history_file.exists())

        with open(event_history_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            self.assertGreater(len(lines), 0)
            first_event = json.loads(lines[0])
            self.assertIn("timestamp", first_event)
            self.assertIn("cycle_id", first_event)
            self.assertIn("opportunity_id", first_event)
            self.assertIn("channel", first_event)
            self.assertIn("action_tier", first_event)
            self.assertIn("state", first_event)


if __name__ == "__main__":
    unittest.main()
