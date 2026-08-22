"""
Unit Tests for PayPal Payment Gateway & Automated Pipeline
"""

import unittest
from pathlib import Path
from src.economics.payment_gateway import PayPalPaymentGateway


class TestPayPalPaymentGateway(unittest.TestCase):

    def test_1_create_checkout_sandbox(self):
        gw = PayPalPaymentGateway()
        res = gw.create_checkout("TEST_CUST_01", 49.0, "Test_Strategy_v1")
        self.assertIn("payment_id", res)
        self.assertEqual(res["status"], "PAYMENT_PENDING")
        self.assertIn("paypal", res["checkout_url"])

    def test_2_verify_payment_sandbox(self):
        gw = PayPalPaymentGateway()
        res_create = gw.create_checkout("TEST_CUST_02", 49.0, "Test_Strategy_v2")
        pid = res_create["payment_id"]

        verif = gw.verify_payment(pid, mock_verification_token="SANDBOX_OK_TOKEN")
        self.assertTrue(verif["verified"])
        self.assertEqual(verif["status"], "PAYMENT_VERIFIED")

    def test_3_pipeline_state_update(self):
        gw = PayPalPaymentGateway()
        res_create = gw.create_checkout("TEST_CUST_03", 49.0, "Test_Strategy_v3")
        pid = res_create["payment_id"]

        updated = gw.update_pipeline_state(pid, "AUDIT_RUNNING")
        self.assertTrue(updated)


if __name__ == "__main__":
    unittest.main()
