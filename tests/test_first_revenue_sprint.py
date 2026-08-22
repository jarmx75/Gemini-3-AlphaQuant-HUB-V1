"""
Unit Tests for Sprint #2 First Revenue Modules
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path

from src.economics.quant_audit_micro_saas import QuantAuditMicroSaaS
from src.economics.outreach_engine import OutreachEngine
from src.economics.first_revenue_gate import FirstRevenueGate


class TestFirstRevenueSprint(unittest.TestCase):

    def test_1_micro_saas_customer_registration_and_audit(self):
        saas = QuantAuditMicroSaaS()
        cust = saas.register_customer("Test Quant Trader", "trader@test.com", "Prop Desk")
        self.assertIn("customer_id", cust)

        rets = pd.Series(np.random.normal(0.001, 0.005, 100))
        report = saas.audit_client_returns_data(cust["customer_id"], "Pairs_StatArb_Test", rets, is_paid=True)

        self.assertEqual(report["payment_status"], "PAID")
        self.assertIn("certificate_id", report)

        summary = saas.get_revenue_summary()
        self.assertGreaterEqual(summary["total_revenue_usd"], 49.0)
        self.assertTrue(summary["first_revenue_achieved"])

        # Cleanup test revenue logs to maintain 0 real payments
        with open(Path("logs/portfolio/customer_ledger.json"), "w") as f:
            import json
            json.dump({"customers": [], "total_customers": 0}, f, indent=2)
        with open(Path("logs/portfolio/revenue_log.json"), "w") as f:
            import json
            json.dump({"revenue_events": [], "total_revenue_usd": 0.0}, f, indent=2)

    def test_2_outreach_engine_20_prospects(self):
        engine = OutreachEngine()
        prospects = engine.get_all_prospects()
        self.assertEqual(len(prospects), 20)

    def test_3_first_revenue_gate(self):
        gate = FirstRevenueGate()
        audit = gate.audit_first_revenue_status()
        self.assertTrue(audit["first_revenue_ready"])


if __name__ == "__main__":
    unittest.main()
