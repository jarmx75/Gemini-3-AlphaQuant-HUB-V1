"""
Unit Test Suite for True 24-Hour Production Observation (Sprint #31.1)
"""

import unittest
from src.economics.autonomous_24h_observation_engine import Autonomous24hObservationEngine, OBSERVATION_LOG_FILE


class TestAutonomous24hObservationEngine(unittest.TestCase):

    def setUp(self):
        if OBSERVATION_LOG_FILE.exists():
            OBSERVATION_LOG_FILE.unlink()
        self.engine = Autonomous24hObservationEngine()

    def test_1_get_or_create_observation_state(self):
        state = self.engine.get_or_create_observation_state()
        self.assertIn("observation_start_utc", state)
        self.assertIn("first_heartbeat", state)

    def test_2_run_observation_audit(self):
        rep = self.engine.run_observation_audit()
        self.assertIn("actual_elapsed_hours", rep)
        self.assertIn("PRODUCTION_RUNTIME_24H_PROVEN", rep)
        self.assertFalse(rep["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
