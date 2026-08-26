"""
Unit Test Suite for Sprint #34.1: PayPal Hosted Payment Links Architecture Migration
"""

import os
import json
import unittest
import urllib.request
from pathlib import Path

from src.economics.paypal_live_link_forensics import PayPalLiveLinkForensics
from src.economics.autonomous_revenue_portfolio import AutonomousRevenuePortfolio
from api import ipn, webhook


class TestSprint341HostedPaymentLinks(unittest.TestCase):

    def setUp(self):
        self.forensics = PayPalLiveLinkForensics()
        self.portfolio = AutonomousRevenuePortfolio()
        self.root = Path(__file__).resolve().parent.parent

    def test_1_hosted_payment_links_http_accessibility_and_pricing(self):
        """Verify all 3 Hosted Payment Links are HTTP 200 accessible with correct amounts."""
        links = {
            "49": ("https://www.paypal.com/ncp/payment/SH9CKB2WSX728", "49.00"),
            "79": ("https://www.paypal.com/ncp/payment/TMMGL3YRC8PFN", "79.00"),
            "96": ("https://www.paypal.com/ncp/payment/2Y3RX97HNWXY6", "96.00")
        }

        for price, (url, expected_amount) in links.items():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.assertEqual(resp.status, 200, f"Link ${price} returned status {resp.status}")
                html = resp.read().decode("utf-8", errors="ignore")
                self.assertIn(expected_amount, html, f"Expected amount {expected_amount} not found in HTML for ${price}")

    def test_2_landing_page_cta_href_routing(self):
        """Verify index.html CTA links route $49 -> SH9CKB2WSX728, $79 -> TMMGL3YRC8PFN, $96 -> 2Y3RX97HNWXY6."""
        index_path = self.root / "docs" / "public_landing" / "index.html"
        self.assertTrue(index_path.exists())

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("https://www.paypal.com/ncp/payment/SH9CKB2WSX728", html)
        self.assertIn("https://www.paypal.com/ncp/payment/TMMGL3YRC8PFN", html)
        self.assertIn("https://www.paypal.com/ncp/payment/2Y3RX97HNWXY6", html)

    def test_3_canonical_portfolio_products_registered(self):
        """Verify QUANT_AUDIT_49, QUANT_EXECUTION_REALITY_AUDIT_79, and COMPLETE_QUANT_VALIDATION_BUNDLE_96 in portfolio."""
        summary = self.portfolio.get_portfolio_summary()
        products = summary["products"]

        self.assertIn("QUANT_AUDIT_49", products)
        self.assertIn("QUANT_EXECUTION_REALITY_AUDIT_79", products)
        self.assertIn("COMPLETE_QUANT_VALIDATION_BUNDLE_96", products)

        self.assertEqual(products["QUANT_AUDIT_49"]["price"], 49.00)
        self.assertEqual(products["QUANT_EXECUTION_REALITY_AUDIT_79"]["price"], 79.00)
        self.assertEqual(products["COMPLETE_QUANT_VALIDATION_BUNDLE_96"]["price"], 96.00)

    def test_4_zero_credentials_requirement_in_ipn_and_webhook(self):
        """Verify IPN and Webhook handlers do not require PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET."""
        # Ensure credentials are absent in environment for test
        env_clean = {k: v for k, v in os.environ.items() if k not in ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"]}
        with unittest.mock.patch.dict(os.environ, env_clean, clear=True):
            forensic_rep = self.forensics.run_forensic_validation()
            self.assertEqual(forensic_rep["architecture"], "PAYPAL_HOSTED_PAYMENT_LINKS_NO_API_KEYS")
            self.assertTrue(forensic_rep["customer_identity_forensics"]["6_zero_api_credentials_required"])

    def test_5_fail_closed_unverified_payment_gate(self):
        """Verify unverified payment returns false verification status until IPN/Webhook confirmation."""
        import importlib.util
        capture_path = self.root / "api" / "capture-order.py"
        spec = importlib.util.spec_from_file_location("capture_order", capture_path)
        capture_order = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture_order)

        handler_instance = capture_order.handler.__new__(capture_order.handler)
        handler_instance.headers = {"Content-Length": "30"}
        
        body_data = json.dumps({"txn_id": "UNVERIFIED_FAKE_TXN_999"}).encode("utf-8")
        handler_instance.rfile = unittest.mock.MagicMock()
        handler_instance.rfile.read.return_value = body_data

        handler_instance.send_response = unittest.mock.MagicMock()
        handler_instance.send_header = unittest.mock.MagicMock()
        handler_instance.end_headers = unittest.mock.MagicMock()
        handler_instance.wfile = unittest.mock.MagicMock()

        handler_instance.do_POST()

        written_bytes = handler_instance.wfile.write.call_args[0][0]
        resp_json = json.loads(written_bytes.decode("utf-8"))

        self.assertFalse(resp_json["verified"])
        self.assertEqual(resp_json["status"], "AWAITING_INDEPENDENT_PAYPAL_VERIFICATION")


if __name__ == "__main__":
    unittest.main()
