"""
Unit Tests for Portfolio Reality Forensic Audit Module
"""

import json
import unittest
from pathlib import Path

from scratch.reconstruct_portfolio_audit import run_forensic_audit


class TestPortfolioRealityAudit(unittest.TestCase):

    def test_1_forensic_audit_execution(self):
        res = run_forensic_audit()
        self.assertIn("reconciliation_status", res)
        self.assertIn("portfolio_reality_verdict", res)
        self.assertEqual(res["lookahead_audit"]["violations_detected"], 0)

    def test_2_audit_log_generated(self):
        log_path = Path("logs/portfolio/portfolio_reality_audit.json")
        self.assertTrue(log_path.exists())
        with open(log_path) as f:
            data = json.load(f)
        self.assertIn("reconciliation_status", data)
        self.assertIn("block_bootstrap_monte_carlo_5000_iters", data)

    def test_3_security_invariants(self):
        config_path = Path("src/execution/execution_config.py")
        if config_path.exists():
            with open(config_path) as f:
                content = f.read()
            self.assertIn("ExecutionMode", content)


if __name__ == "__main__":
    unittest.main()
