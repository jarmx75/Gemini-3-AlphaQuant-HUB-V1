"""
Unit Test Suite for Real Outreach Execution Engine (Sprint #24)
"""

import unittest
from src.economics.outreach_execution_engine import RealOutreachExecutionEngine


class TestRealOutreachExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RealOutreachExecutionEngine()

    def test_1_search_github_quant_issues(self):
        leads = self.engine.search_github_quant_issues()
        self.assertIsInstance(leads, list)

    def test_2_execute_outreach_cycle(self):
        rep = self.engine.execute_outreach_cycle()
        self.assertIn("verified_leads", rep)
        self.assertIn("published_count", rep)
        self.assertIn("blocked_count", rep)
        self.assertIn("real_publication_urls", rep)
        self.assertFalse(rep["FIRST_REVENUE_ACHIEVED"])


if __name__ == "__main__":
    unittest.main()
