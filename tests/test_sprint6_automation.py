"""
Unit Tests for Sprint #6 Automation Modules
"""

import unittest
from src.economics.autonomous_outreach import AutonomousOutreachEngine
from src.economics.daily_control_scheduler import DailyControlScheduler


class TestSprint6Automation(unittest.TestCase):

    def test_1_revenue_score_computation(self):
        engine = AutonomousOutreachEngine()
        prospect = {
            "fit": 9.0,
            "pain": 9.0,
            "reachable": 8.0,
            "willingness_to_pay": 8.0,
            "automation": 9.0,
            "outreach_cost": 1.0
        }
        score = engine.compute_revenue_score(prospect)
        self.assertGreater(score, 1000.0)

    def test_2_blocker_audit(self):
        engine = AutonomousOutreachEngine()
        blockers = engine.check_and_audit_blockers()
        self.assertIn("github_outreach_autonomous", blockers)

    def test_3_daily_control_scheduler(self):
        scheduler = DailyControlScheduler()
        audit = scheduler.run_0900_health_checks()
        self.assertEqual(audit["health_status"], "ALL_SYSTEMS_OPERATIONAL")
        self.assertIn("trading_status", audit)


if __name__ == "__main__":
    unittest.main()
