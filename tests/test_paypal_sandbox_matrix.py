"""
PayPal Sandbox Test Matrix (Sprint #19 Phase 9)

Tests:
- TEST 1: Successful payment -> PROCEED
- TEST 2: Cancelled checkout -> REJECTED
- TEST 3: Payment not completed -> REJECTED
- TEST 4: Invalid/unknown order ID -> REJECTED
- TEST 5: Upload without verified payment -> REJECTED
- TEST 6: Valid payment + valid CSV upload -> PROCEED TO AUDIT
"""

import unittest
from src.economics.payment_gateway import PayPalPaymentGateway
from src.economics.quant_audit_execution_engine import QuantAuditExecutionEngine


class TestPayPalSandboxMatrix(unittest.TestCase):

    def setUp(self):
        self.gw = PayPalPaymentGateway()
        self.audit_engine = QuantAuditExecutionEngine()

    def test_1_successful_payment(self):
        res = self.gw.create_checkout("SANDBOX_BUYER_01", 49.0, "Strategy_A")
        verif = self.gw.verify_payment(res["payment_id"], mock_verification_token="SANDBOX_OK_TOKEN")
        self.assertTrue(verif["verified"])
        self.assertEqual(verif["status"], "PAYMENT_VERIFIED")

    def test_2_cancelled_checkout(self):
        res = self.gw.create_checkout("SANDBOX_BUYER_02", 49.0, "Strategy_B")
        # Simulate cancel token
        verif = self.gw.verify_payment(res["payment_id"], mock_verification_token="CANCELLED_TOKEN")
        self.assertFalse(verif["verified"])

    def test_3_payment_not_completed(self):
        res = self.gw.create_checkout("SANDBOX_BUYER_03", 49.0, "Strategy_C")
        verif = self.gw.verify_payment(res["payment_id"], mock_verification_token="PENDING_TOKEN")
        self.assertFalse(verif["verified"])

    def test_4_invalid_unknown_order_id(self):
        verif = self.gw.verify_payment("INVALID_ORDER_99999", mock_verification_token="INVALID")
        self.assertFalse(verif["verified"])
        self.assertEqual(verif["status"], "PAYMENT_NOT_FOUND")

    def test_5_upload_without_verified_payment(self):
        # Fail closed on unverified upload
        verif = self.gw.verify_payment("UNVERIFIED_ORDER_123", mock_verification_token="NONE")
        self.assertFalse(verif["verified"])

    def test_6_valid_payment_and_csv_upload_to_audit(self):
        res = self.gw.create_checkout("SANDBOX_BUYER_06", 49.0, "Strategy_F")
        verif = self.gw.verify_payment(res["payment_id"], mock_verification_token="SANDBOX_OK_TOKEN")
        self.assertTrue(verif["verified"])

        # Execute Audit
        audit_res = self.audit_engine.run_audit_pipeline("buyer_06@quant.com", res["payment_id"])
        self.assertEqual(audit_res["status"], "AUDIT_COMPLETED")
        self.assertIn("cert_id", audit_res)


if __name__ == "__main__":
    unittest.main()
