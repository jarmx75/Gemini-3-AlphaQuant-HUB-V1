"""
Unit Test Suite for Sprint #34: Second Revenue Product Validation (QUANT_EXECUTION_REALITY_AUDIT $79 USD)
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.economics.quant_execution_reality_audit import (
    QuantExecutionRealityAuditEngine,
    REAL_WORLD_EXECUTION_PROBLEMS
)
from src.economics.autonomous_revenue_portfolio import AutonomousRevenuePortfolio
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor


class TestSprint34SecondProductValidation(unittest.TestCase):

    def setUp(self):
        self.execution_engine = QuantExecutionRealityAuditEngine()
        self.portfolio_engine = AutonomousRevenuePortfolio()
        self.audit_engine = AcquisitionForensicAuditEngine()
        self.monitor = ManualRevenueFunnelMonitor()

    def test_1_demand_taxonomy_completeness(self):
        """Verify at least 20 verified real-world execution problems with required taxonomy metrics."""
        self.assertGreaterEqual(len(REAL_WORLD_EXECUTION_PROBLEMS), 20)
        
        required_keys = {
            "id", "title", "domain", "source", "description",
            "frequency", "buyer_intent_score", "severity",
            "compatibility", "competition", "est_time_to_first_sale"
        }
        
        for prob in REAL_WORLD_EXECUTION_PROBLEMS:
            self.assertTrue(required_keys.issubset(prob.keys()), f"Problem {prob.get('id')} missing keys")
            self.assertIn(prob["frequency"], ["CRITICAL", "HIGH", "MED", "LOW"])
            self.assertGreaterEqual(prob["buyer_intent_score"], 0)
            self.assertLessEqual(prob["buyer_intent_score"], 100)
            self.assertIn(prob["severity"], ["FATAL", "HIGH", "MED", "LOW"])
            self.assertIn(prob["compatibility"], ["DIRECT", "EXTENDED"])
            self.assertIn(prob["competition"], ["LOW", "MED", "HIGH"])

    def test_2_product_portfolio_registration_and_validating_status(self):
        """Verify QUANT_EXECUTION_REALITY_AUDIT is registered in AutonomousRevenuePortfolio with status VALIDATING."""
        summary = self.portfolio_engine.get_portfolio_summary()
        products = summary["products"]

        self.assertIn("QUANT_EXECUTION_REALITY_AUDIT", products)
        product = products["QUANT_EXECUTION_REALITY_AUDIT"]

        self.assertEqual(product["product_id"], "QUANT_EXECUTION_REALITY_AUDIT")
        self.assertEqual(product["price"], 79.00)
        self.assertEqual(product["status"], "VALIDATING")
        self.assertTrue(product["deployed_in_production"])

    def test_3_execution_reality_audit_calculation_and_verdict(self):
        """Test QuantExecutionRealityAuditEngine execution decay calculations and verdict logic."""
        report = self.execution_engine.run_execution_reality_audit(
            strategy_name="Unit Test Execution Strategy",
            initial_capital_usd=10000.0,
            trades_count=100,
            baseline_sharpe=2.5,
            baseline_return_pct=30.0,
            baseline_max_drawdown_pct=5.0,
            avg_spread_bps=3.0,
            commission_per_trade_usd=1.0,
            volatility_slippage_bps=2.0
        )

        self.assertEqual(report["product_id"], "QUANT_EXECUTION_REALITY_AUDIT")
        self.assertEqual(report["price_usd"], 79.00)
        self.assertTrue(report["certificate_id"].startswith("CERT-EXEC-"))
        self.assertIn(report["verdict"], [
            "REALITY_SURVIVOR", "EXECUTION_FRAGILE",
            "HIGH_SLIPPAGE_DECAY", "UNVIABLE_UNDER_COSTS"
        ])
        
        # Verify friction calculations
        friction = report["friction_breakdown"]
        self.assertGreater(friction["total_friction_usd"], 0)
        self.assertGreater(report["baseline"]["return_pct"], report["execution_adjusted"]["return_pct"])

    def test_4_certificate_generation_and_persistence(self):
        """Verify certificate file is created with CERT-EXEC- prefix."""
        report = self.execution_engine.run_execution_reality_audit(strategy_name="Cert Generation Test")
        cert_id = report["certificate_id"]
        cert_path = Path(report["certificate_path"])

        self.assertTrue(cert_id.startswith("CERT-EXEC-"))
        self.assertTrue(cert_path.exists())

        with open(cert_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("QUANT EXECUTION REALITY AUDIT CERTIFICATE", content)
            self.assertIn(cert_id, content)
            self.assertIn("$79 USD", content)

    def test_5_paypal_create_order_pricing_routing(self):
        """Verify api/create-order.py returns Hosted Payment Link mapping without requiring Orders API credentials."""
        import importlib.util
        file_path = Path(__file__).resolve().parent.parent / "api" / "create-order.py"
        spec = importlib.util.spec_from_file_location("create_order", file_path)
        create_order = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_order)
        
        handler_instance = create_order.handler.__new__(create_order.handler)
        handler_instance.headers = {"Content-Length": "48"}
        
        body_data = json.dumps({"product_id": "QUANT_EXECUTION_REALITY_AUDIT_79"}).encode("utf-8")
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = body_data

        handler_instance.send_response = MagicMock()
        handler_instance.send_header = MagicMock()
        handler_instance.end_headers = MagicMock()
        handler_instance.wfile = MagicMock()

        handler_instance.do_POST()

        written_bytes = handler_instance.wfile.write.call_args[0][0]
        payload_json = json.loads(written_bytes.decode("utf-8"))

        self.assertEqual(payload_json["status"], "DEPRECATED_MIGRATED_TO_HOSTED_LINKS")
        self.assertIn("https://www.paypal.com/ncp/payment/", payload_json["approvalUrl"])

    def test_6_quant_audit_49_and_monitor_backward_compatibility(self):
        """Verify Quant Audit $49 and Read-Only Monitor maintain 100% backward compatibility."""
        rep = self.audit_engine.run_forensic_audit()
        snap = self.monitor.generate_snapshot()

        # Check core keys present
        self.assertIn("external_customer_funnel", rep)
        self.assertIn("product_portfolio", rep)
        self.assertIn("QUANT_AUDIT", rep["product_portfolio"]["products"])
        self.assertIn("QUANT_EXECUTION_REALITY_AUDIT", rep["product_portfolio"]["products"])

        # Check Read-Only Monitor integrity
        self.assertEqual(snap["monitor_integrity"]["MONITOR_MODE"], "READ_ONLY")
        self.assertEqual(snap["monitor_integrity"]["SIDE_EFFECTS"], 0)


if __name__ == "__main__":
    unittest.main()
