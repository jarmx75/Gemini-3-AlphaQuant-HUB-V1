"""
Unit Test Suite for Sprint #34.2: Verify PayPal IPN Production Handshake Before Real Customer Payment
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

import importlib.util
from src.economics.paypal_ipn_production_verifier import PayPalIPNProductionVerifier
from api import ipn


class TestSprint342IPNVerification(unittest.TestCase):

    def setUp(self):
        self.verifier = PayPalIPNProductionVerifier()
        self.root = Path(__file__).resolve().parent.parent

    def test_1_txn_id_primary_idempotency_key_deduplication(self):
        """Verify txn_id is enforced as primary key and duplicate IPNs yield DUPLICATE_IGNORED."""
        handler_instance = ipn.handler.__new__(ipn.handler)
        handler_instance.headers = {"Content-Length": "75"}
        
        raw_payload = "txn_id=TXN_REAL_1001&payment_status=Completed&mc_gross=49.00&mc_currency=USD&payer_email=cust@example.com"
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = raw_payload.encode("utf-8")

        mock_cm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"VERIFIED"
        mock_cm.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"PAYPAL_MODE": "SANDBOX"}):
            with patch("urllib.request.urlopen", return_value=mock_cm):
                handler_instance.send_response = MagicMock()
                handler_instance.send_header = MagicMock()
                handler_instance.end_headers = MagicMock()
                handler_instance.wfile = MagicMock()

                # First delivery -> NEW_VERIFIED
                handler_instance.do_POST()
                res1 = json.loads(handler_instance.wfile.write.call_args[0][0].decode("utf-8"))
                self.assertTrue(res1.get("verified"))
                self.assertEqual(res1.get("idempotency_status"), "NEW_VERIFIED")

                # Second delivery -> DUPLICATE_IGNORED
                handler_instance.do_POST()
                res2 = json.loads(handler_instance.wfile.write.call_args[0][0].decode("utf-8"))
                self.assertTrue(res2.get("verified"))
                self.assertEqual(res2.get("idempotency_status"), "DUPLICATE_IGNORED")

    def test_2_invalid_ipn_payload_rejection(self):
        """Verify INVALID IPN handshake response yields verified=False and REJECTED status."""
        handler_instance = ipn.handler.__new__(ipn.handler)
        handler_instance.headers = {"Content-Length": "60"}
        
        raw_payload = "txn_id=TXN_INVALID_999&payment_status=Completed&mc_gross=49.00"
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = raw_payload.encode("utf-8")

        mock_cm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"INVALID"
        mock_cm.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"PAYPAL_MODE": "SANDBOX"}):
            with patch("urllib.request.urlopen", return_value=mock_cm):
                handler_instance.send_response = MagicMock()
                handler_instance.send_header = MagicMock()
                handler_instance.end_headers = MagicMock()
                handler_instance.wfile = MagicMock()

                handler_instance.do_POST()
                res = json.loads(handler_instance.wfile.write.call_args[0][0].decode("utf-8"))
                self.assertFalse(res.get("verified"))
                self.assertEqual(res.get("idempotency_status"), "REJECTED")

    def test_3_product_amount_mapping_rules(self):
        """Verify $49 -> QUANT_AUDIT_49, $79 -> QUANT_EXECUTION_REALITY_AUDIT_79, $96 -> COMPLETE_QUANT_VALIDATION_BUNDLE_96."""
        amounts_expected = [
            ("49.00", "QUANT_AUDIT_49"),
            ("79.00", "QUANT_EXECUTION_REALITY_AUDIT_79"),
            ("96.00", "COMPLETE_QUANT_VALIDATION_BUNDLE_96")
        ]

        mock_cm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"VERIFIED"
        mock_cm.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"PAYPAL_MODE": "SANDBOX"}):
            with patch("urllib.request.urlopen", return_value=mock_cm):
                for amt, expected_pid in amounts_expected:
                    handler_instance = ipn.handler.__new__(ipn.handler)
                    handler_instance.headers = {"Content-Length": "80"}
                    raw_payload = f"txn_id=TXN_AMT_{amt}&payment_status=Completed&mc_gross={amt}&mc_currency=USD&payer_email=test@quant.com"
                    handler_instance.rfile = MagicMock()
                    handler_instance.rfile.read.return_value = raw_payload.encode("utf-8")
                    handler_instance.send_response = MagicMock()
                    handler_instance.send_header = MagicMock()
                    handler_instance.end_headers = MagicMock()
                    handler_instance.wfile = MagicMock()

                    handler_instance.do_POST()

        # Inspect verified log file
        log_file = self.root / "logs" / "portfolio" / "paypal_payment_log.json"
        self.assertTrue(log_file.exists())
        with open(log_file, "r", encoding="utf-8") as f:
            pmts = json.load(f)
            for amt, expected_pid in amounts_expected:
                match = next((p for p in pmts if isinstance(p, dict) and p.get("txn_id") == f"TXN_AMT_{amt}"), None)
                self.assertIsNotNone(match, f"No payment record found for TXN_AMT_{amt}")
                self.assertEqual(match["product_id"], expected_pid)

    def test_4_verifier_telemetry_report(self):
        """Verify verifier engine reports IPN_PRODUCTION_CONFIGURED=True and IPN_REAL_EVENT_RECEIVED=False."""
        rep = self.verifier.run_production_verification()

        self.assertTrue(rep["ipn_production_configured"])
        self.assertIn("IPN_PRODUCTION_HANDSHAKE_READY", rep["final_verdict"])
        self.assertFalse(rep["first_revenue_achieved"])
        self.assertEqual(rep["metrics"]["production_validation_status"], "VERIFIED_HANDSHAKE_READY")
        self.assertEqual(rep["metrics"]["duplicate_protection_status"], "IDEMPOTENT_TXN_KEY_ENFORCED")
        self.assertEqual(rep["metrics"]["product_mapping_status"], "MAPPED_49_79_96")


if __name__ == "__main__":
    unittest.main()
