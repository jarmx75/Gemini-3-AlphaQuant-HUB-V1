"""
Unit Test Suite for Sprint #34.2: Verify PayPal IPN Production Handshake Before Real Customer Payment
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

import tempfile
import shutil
import importlib.util
from src.economics.paypal_ipn_production_verifier import PayPalIPNProductionVerifier
from api import ipn

spec_capture = importlib.util.spec_from_file_location("capture_order", Path(__file__).resolve().parent.parent / "api" / "capture-order.py")
capture_order = importlib.util.module_from_spec(spec_capture)
spec_capture.loader.exec_module(capture_order)


class TestSprint342IPNVerification(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_payment_log = os.path.join(self.temp_dir, "paypal_payment_log.json")
        self.temp_events_log = os.path.join(self.temp_dir, "paypal_ipn_events.jsonl")
        
        self.p1 = patch("src.economics.paypal_ipn_production_verifier.PAYMENT_LOG_FILE", Path(self.temp_payment_log))
        self.p2 = patch("src.economics.paypal_ipn_production_verifier.EVENTS_LOG_FILE", Path(self.temp_events_log))
        self.p3 = patch.dict(os.environ, {"PAYPAL_MODE": "SANDBOX", "PAYPAL_LOG_DIR": self.temp_dir})
        self.p1.start()
        self.p2.start()
        self.p3.start()
        
        self.verifier = PayPalIPNProductionVerifier()

    def tearDown(self):
        self.p1.stop()
        self.p2.stop()
        self.p3.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_1_txn_id_primary_idempotency_key_deduplication(self):
        """Verify txn_id is enforced as primary key and duplicate IPNs yield DUPLICATE_IGNORED."""
        raw_payload = "txn_id=TXN_REAL_1001&payment_status=Completed&mc_gross=49.00&mc_currency=USD&payer_email=test_cust@example.com"
        raw_bytes = raw_payload.encode("utf-8")

        handler_instance = ipn.handler.__new__(ipn.handler)
        handler_instance.headers = {"Content-Length": str(len(raw_bytes))}
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = raw_bytes

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
        raw_payload = "txn_id=TXN_INVALID_999&payment_status=Completed&mc_gross=49.00"
        raw_bytes = raw_payload.encode("utf-8")

        handler_instance = ipn.handler.__new__(ipn.handler)
        handler_instance.headers = {"Content-Length": str(len(raw_bytes))}
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = raw_bytes

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
                    raw_payload = f"txn_id=TXN_AMT_{amt}&payment_status=Completed&mc_gross={amt}&mc_currency=USD&payer_email=test@quant.com"
                    raw_bytes = raw_payload.encode("utf-8")
                    handler_instance.headers = {"Content-Length": str(len(raw_bytes))}
                    handler_instance.rfile = MagicMock()
                    handler_instance.rfile.read.return_value = raw_bytes
                    handler_instance.send_response = MagicMock()
                    handler_instance.send_header = MagicMock()
                    handler_instance.end_headers = MagicMock()
                    handler_instance.wfile = MagicMock()

                    handler_instance.do_POST()

        # Inspect verified log file
        log_file = Path(self.temp_dir) / "paypal_payment_log.json"
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

        self.assertTrue(rep["IPN_PRODUCTION_CONFIGURED"])
        self.assertIn(rep["final_verdict"], ["BLOCKED_PENDING_VERCEL_BACKEND_REDEPLOYMENT", "READY"])
        self.assertFalse(rep["FIRST_REVENUE_ACHIEVED"])
        self.assertEqual(rep["REAL_REVENUE_USD"], 0.0)
        self.assertEqual(rep["metrics"]["production_validation_status"], "VERIFIED_HANDSHAKE_READY")
        self.assertEqual(rep["metrics"]["duplicate_protection_status"], "IDEMPOTENT_TXN_KEY_ENFORCED")

    def test_5_system_test_payment_mapping_and_zero_fulfillment(self):
        """Verify $1.00 MXN or item_number 4EMBJBQD7482S maps to SYSTEM_TEST_PAYMENT with zero commercial fulfillment."""
        handler_instance = ipn.handler.__new__(ipn.handler)
        raw_payload = "txn_id=TXN_TEST_1MXN_001&payment_status=Completed&mc_gross=1.00&mc_currency=MXN&payer_email=buyer@paypal.com&item_number=4EMBJBQD7482S"
        raw_bytes = raw_payload.encode("utf-8")
        handler_instance.headers = {"Content-Length": str(len(raw_bytes))}
        handler_instance.rfile = MagicMock()
        handler_instance.rfile.read.return_value = raw_bytes

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

                handler_instance.do_POST()
                res = json.loads(handler_instance.wfile.write.call_args[0][0].decode("utf-8"))
                self.assertTrue(res.get("verified"))

        # Inspect verified log file
        log_file = Path(self.temp_payment_log)
        self.assertTrue(log_file.exists())
        with open(log_file, "r", encoding="utf-8") as f:
            pmts = json.load(f)
            match = next((p for p in pmts if isinstance(p, dict) and p.get("txn_id") == "TXN_TEST_1MXN_001"), None)
            self.assertIsNotNone(match)
            self.assertEqual(match["product_id"], "SYSTEM_TEST_PAYMENT")
            self.assertFalse(match["authorizes_fulfillment"])
            self.assertFalse(match["is_commercial"])

    def test_6_hosted_payment_link_return_parameter_mapping(self):
        """Verify transaction 8WB32625PL331771 and return params tx, st, amt, cc map to SYSTEM_TEST_PAYMENT in capture-order handler."""
        capture_handler = capture_order.handler.__new__(capture_order.handler)
        raw_payload = json.dumps({
            "tx": "8WB32625PL331771",
            "st": "COMPLETED",
            "amt": "1.00",
            "cc": "MXN"
        }).encode("utf-8")

        capture_handler.headers = {"Content-Length": str(len(raw_payload))}
        capture_handler.rfile = MagicMock()
        capture_handler.rfile.read.return_value = raw_payload
        capture_handler.send_response = MagicMock()
        capture_handler.send_header = MagicMock()
        capture_handler.end_headers = MagicMock()
        capture_handler.wfile = MagicMock()

        capture_handler.do_POST()
        res = json.loads(capture_handler.wfile.write.call_args[0][0].decode("utf-8"))

        self.assertTrue(res.get("verified"))
        self.assertEqual(res.get("product_id"), "SYSTEM_TEST_PAYMENT")
        self.assertFalse(res.get("authorizes_fulfillment"))

    def test_7_end_to_end_ready_blocked_when_vercel_endpoints_return_404(self):
        """Verify END_TO_END_READY_FOR_CUSTOMER is False when backend endpoints return HTTP 404."""
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None)):
            rep = self.verifier.run_production_verification()
            verdict = rep.get("verdict_fields", {})

            self.assertFalse(verdict.get("END_TO_END_READY_FOR_CUSTOMER"))
            self.assertEqual(verdict.get("BACKEND_PUBLIC_REACHABILITY"), "HTTP_404_DEPLOYMENT_NOT_FOUND")
            self.assertEqual(rep.get("final_verdict"), "BLOCKED_PENDING_VERCEL_BACKEND_REDEPLOYMENT")

    def test_8_dynamic_txn_id_prefix_matching(self):
        """Verify 16-char redirect tx (8WB32625PL331771) and 17-char IPN/email txn_id (8WB32625PL3317718) correlate cleanly."""
        capture_handler = capture_order.handler.__new__(capture_order.handler)
        raw_payload = json.dumps({
            "tx": "8WB32625PL3317718",
            "st": "COMPLETED",
            "amt": "1.00",
            "cc": "MXN"
        }).encode("utf-8")

        capture_handler.headers = {"Content-Length": str(len(raw_payload))}
        capture_handler.rfile = MagicMock()
        capture_handler.rfile.read.return_value = raw_payload
        capture_handler.send_response = MagicMock()
        capture_handler.send_header = MagicMock()
        capture_handler.end_headers = MagicMock()
        capture_handler.wfile = MagicMock()

        capture_handler.do_POST()
        res = json.loads(capture_handler.wfile.write.call_args[0][0].decode("utf-8"))

        self.assertTrue(res.get("verified"))
        self.assertEqual(res.get("product_id"), "SYSTEM_TEST_PAYMENT")
        self.assertFalse(res.get("authorizes_fulfillment"))


if __name__ == "__main__":
    unittest.main()
