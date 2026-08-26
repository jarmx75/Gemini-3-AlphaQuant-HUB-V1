"""
Unit Test Suite for PayPal LIVE Link Forensics (Sprint #26)
"""

import unittest
from src.economics.paypal_live_link_forensics import PayPalLiveLinkForensics


class TestPayPalLiveLinkForensics(unittest.TestCase):

    def setUp(self):
        self.forensics = PayPalLiveLinkForensics()

    def test_1_run_forensic_validation(self):
        rep = self.forensics.run_forensic_validation()
        self.assertEqual(rep["architecture"], "PAYPAL_HOSTED_PAYMENT_LINKS_NO_API_KEYS")
        self.assertEqual(rep["currency"], "USD")
        self.assertEqual(rep["final_verdict"], "READY_FOR_FIRST_CUSTOMER")
        self.assertFalse(rep["first_revenue_achieved"])

    def test_2_customer_identity_qa(self):
        rep = self.forensics.run_forensic_validation()
        qa = rep["customer_identity_forensics"]
        self.assertTrue(qa["1_hosted_links_verified"])
        self.assertTrue(qa["6_zero_api_credentials_required"])
        self.assertTrue(qa["8_idempotent_fulfillment_verified"])

    def test_3_security_test_results(self):
        rep = self.forensics.run_forensic_validation()
        sec = rep["security_test_results"]
        self.assertEqual(sec["scenario_a_direct_success_access"], "REJECTED")
        self.assertEqual(sec["scenario_b_fake_order_id"], "REJECTED")
        self.assertEqual(sec["scenario_e_confirmed_verified_ipn_webhook"], "ACCEPTED")


if __name__ == "__main__":
    unittest.main()
