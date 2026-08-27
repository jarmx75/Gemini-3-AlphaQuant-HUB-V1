"""
Unit Test Suite for Sprint #33 Autonomous Revenue Acquisition Engine

Tests all 13 required categories:
1. continuous_discovery
2. multi_channel_discovery
3. no_idle_invariant
4. cooldown
5. duplicate_prevention
6. persistent_observation_session
7. monitor_read_only
8. multi_product_portfolio
9. channel_learning
10. failed_channel_failover
11. opportunity_ranking
12. revenue_activity_rate
13. 24h_observation_persistence
"""

import unittest
import json
import time
from pathlib import Path
from src.economics.autonomous_opportunity_discovery_engine import (
    AutonomousOpportunityDiscoveryEngine, OpportunityScorer, BaseChannelAdapter
)
from src.economics.autonomous_revenue_portfolio import AutonomousRevenuePortfolio
from src.economics.autonomous_revenue_orchestrator import AutonomousRevenueOrchestrator
from src.economics.revenue_observation_session import RevenueObservationSession
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine


class TestSprint33AutonomousRevenueEngine(unittest.TestCase):

    def setUp(self):
        self.discovery_engine = AutonomousOpportunityDiscoveryEngine()
        self.portfolio_engine = AutonomousRevenuePortfolio()
        self.orchestrator = AutonomousRevenueOrchestrator()
        self.session_mgr = RevenueObservationSession()
        self.monitor = ManualRevenueFunnelMonitor()

    def test_1_continuous_discovery(self):
        pool = self.discovery_engine.discover_all_opportunities()
        self.assertGreaterEqual(len(pool), 1)

    def test_2_multi_channel_discovery(self):
        adapters = self.discovery_engine.adapters
        self.assertEqual(len(adapters), 9)
        channels = set(a.adapter_name for a in adapters)
        self.assertIn("GITHUB", channels)
        self.assertIn("REDDIT", channels)
        self.assertIn("SEO", channels)

    def test_3_no_idle_invariant(self):
        action = self.orchestrator.get_next_best_revenue_action()
        self.assertIn("action_type", action)
        self.assertEqual(action["status"], "ELIGIBLE")

    def test_4_cooldown(self):
        key = "test_thread_cooldown_key"
        self.assertFalse(self.discovery_engine.is_in_cooldown(key))
        self.discovery_engine.set_cooldown(key, duration_seconds=10)
        self.assertTrue(self.discovery_engine.is_in_cooldown(key))

    def test_5_duplicate_prevention(self):
        item = {
            "context_score": 85,
            "intent_score": 80,
            "promotion_risk": 10,
            "duplicate_risk": 1
        }
        is_qual, reason = OpportunityScorer.evaluate_publication_guards(item)
        self.assertFalse(is_qual)
        self.assertIn("REJECTED_DUPLICATE_RISK", reason)

    def test_6_persistent_observation_session(self):
        data1 = self.session_mgr.get_session_data()
        time.sleep(0.01)
        data2 = self.session_mgr.get_session_data()
        self.assertEqual(data1["session_id"], data2["session_id"])
        self.assertEqual(data1["start_time_utc"], data2["start_time_utc"])

    def test_7_monitor_read_only(self):
        snap = self.monitor.generate_snapshot()
        self.assertEqual(snap["monitor_integrity"]["MONITOR_MODE"], "READ_ONLY")
        self.assertEqual(snap["monitor_integrity"]["SIDE_EFFECTS"], 0)
        self.assertTrue(snap["monitor_integrity"]["CRON_UNTOUCHED"])

    def test_8_multi_product_portfolio(self):
        summary = self.portfolio_engine.get_portfolio_summary()
        self.assertGreaterEqual(summary["total_products"], 3)
        self.assertIn("QUANT_AUDIT", summary["products"])
        self.assertIn("DATA_PRODUCTS", summary["products"])

    def test_9_channel_learning(self):
        state = self.portfolio_engine.redistribute_effort()
        self.assertIn("QUANT_AUDIT", state["products"])

    def test_10_failed_channel_failover(self):
        action = {"action_type": "INVALID_BROKEN_ACTION", "opportunity_id": "opp_fail_1"}
        success, res = self.orchestrator.execute_action_with_failover(action)
        self.assertIn("result_status", res)
        self.assertIn(res["result_status"], ["SUCCESS", "FAILOVER_SUCCESS"])

    def test_11_opportunity_ranking(self):
        item_high = {"context_score": 95, "intent_score": 90, "commercial_score": 90, "promotion_risk": 5, "channel_score": 90, "time_to_revenue": 90, "automation_score": 90, "competition_score": 10}
        item_low = {"context_score": 40, "intent_score": 30, "commercial_score": 20, "promotion_risk": 80, "channel_score": 40, "time_to_revenue": 20, "automation_score": 40, "competition_score": 80}
        score_high = OpportunityScorer.calculate_score(item_high)
        score_low = OpportunityScorer.calculate_score(item_low)
        self.assertGreater(score_high, score_low)

    def test_12_revenue_activity_rate(self):
        audit = AcquisitionForensicAuditEngine().run_forensic_audit()
        rate = audit["runtime"]["revenue_activity_rate"]
        self.assertNotEqual(rate, "UNKNOWN")

    def test_13_24h_observation_persistence(self):
        info = RevenueObservationSession.get_session_info()
        self.assertGreaterEqual(info["remaining_hours_to_24h"], 0.0)
        if info["elapsed_hours"] <= 24.0:
            self.assertEqual(round(info["elapsed_hours"] + info["remaining_hours_to_24h"], 2), 24.0)
        else:
            self.assertEqual(info["remaining_hours_to_24h"], 0.0)


if __name__ == "__main__":
    unittest.main()
