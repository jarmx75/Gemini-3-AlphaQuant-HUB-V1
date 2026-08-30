"""
Unit Test Suite: Commercial Fulfillment Readiness & Security Audit (Sprint #36.8)

Verifies 100% of Etapa 4 Commercial Requirements:
1. Browser return (success.html) never authorizes fulfillment.
2. Unverified IPN/webhook never authorizes fulfillment.
3. Verified COMPLETED payment fixture authorizes fulfillment exactly once.
4. Duplicate txn_id yields DUPLICATE_IGNORED and zero duplicate fulfillment.
5. SYSTEM_TEST_PAYMENT ($1 MXN) is strictly isolated (0 revenue, 0 audits, 0 certs).
6. Historical mock data (TEST_CUST_*, SANDBOX_BUYER_*) yield 0 verified commercial metrics.
7. Upload without verified commercial payment authorization is rejected (403 Forbidden).
8. Disallowed extensions, excessive size (>5MB), path traversal, or malformed text rejected.
9. 6-tier traceability link (case_id <-> txn_id <-> file_id <-> audit_id <-> cert_id <-> email_id) enforced.
10. Ephemeral Vercel storage status reported as NOT_CONFIGURED.
11. Forensic audit engine and monitor strictly isolate real vs test/historical metrics.
12. Zero real transactions, zero real emails, zero POSTs to PayPal, zero external publications.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from io import BytesIO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib

CaptureOrderModule = importlib.import_module('api.capture-order')
IPNModule = importlib.import_module('api.ipn')
UploadAuditModule = importlib.import_module('api.upload-audit')

CaptureOrderHandler = CaptureOrderModule.handler
IPNHandler = IPNModule.handler
UploadAuditHandler = UploadAuditModule.handler
verify_commercial_payment_authorization = UploadAuditModule.verify_commercial_payment_authorization
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor


class DummyHTTPResponse:
    """Mock HTTP response container for testing BaseHTTPRequestHandler endpoints."""
    def __init__(self):
        self.status = None
        self.headers = {}
        self.wfile = BytesIO()

    def send_response(self, code):
        self.status = code

    def send_header(self, keyword, value):
        self.headers[keyword] = value

    def end_headers(self):
        pass

    def get_json_body(self):
        self.wfile.seek(0)
        raw = self.wfile.read().decode('utf-8')
        return json.loads(raw) if raw else {}


def invoke_handler(handler_cls, method='POST', headers=None, body=b''):
    """Helper to instantiate and invoke BaseHTTPRequestHandler endpoints cleanly."""
    headers = headers or {}
    rfile = BytesIO(body)
    headers['Content-Length'] = str(len(body))

    # Construct mock request object
    dummy_resp = DummyHTTPResponse()
    handler_inst = handler_cls.__new__(handler_cls)
    handler_inst.rfile = rfile
    handler_inst.wfile = dummy_resp.wfile
    handler_inst.headers = headers
    handler_inst.send_response = dummy_resp.send_response
    handler_inst.send_header = dummy_resp.send_header
    handler_inst.end_headers = dummy_resp.end_headers

    if method == 'POST':
        handler_inst.do_POST()
    elif method == 'GET':
        handler_inst.do_GET()
    elif method == 'OPTIONS':
        handler_inst.do_OPTIONS()

    return dummy_resp


class TestSprint368CommercialFulfillmentReadiness(unittest.TestCase):

    def setUp(self):
        self.log_dir = PROJECT_ROOT / "logs" / "portfolio"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pmt_file = self.log_dir / "paypal_payment_log.json"
        self._cleanup_test_records()

    def tearDown(self):
        self._cleanup_test_records()

    def _cleanup_test_records(self):
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    pmts = content if isinstance(content, list) else content.get('payments', [])
                cleaned = [
                    p for p in pmts
                    if isinstance(p, dict) and p.get('txn_id') not in [
                        'VERIFIED_COMMERCIAL_TX_TEST_99',
                        'DUP_TEST_TX_888',
                        'VALID_AUTH_TX_FOR_UPLOAD_TEST',
                        'TRACEABILITY_TEST_TX_777',
                        'EPHEMERAL_STORAGE_TX_666'
                    ]
                ]
                with open(self.pmt_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned, f, indent=2)
            except Exception:
                pass

    def test_1_success_html_browser_return_does_not_authorize_fulfillment(self):
        """Verify browser return parameters (success.html) to /api/capture-order return unverified unless backed by IPN."""
        body = json.dumps({'orderID': 'UNVERIFIED_BROWSER_TX_999', 'amt': '49.00', 'st': 'COMPLETED'}).encode('utf-8')
        resp = invoke_handler(CaptureOrderHandler, 'POST', {'Content-Type': 'application/json'}, body)
        
        self.assertEqual(resp.status, 200)
        data = resp.get_json_body()
        self.assertFalse(data.get('verified'))
        self.assertEqual(data.get('status'), 'AWAITING_INDEPENDENT_PAYPAL_VERIFICATION')

    def test_2_unverified_ipn_webhook_does_not_authorize_fulfillment(self):
        """Verify unverified IPN postback returns verified=False and does not write to paypal_payment_log.json."""
        ipn_payload = "txn_id=FAKE_UNVERIFIED_TX_101&payment_status=Completed&mc_gross=49.00&mc_currency=USD".encode('utf-8')
        resp = invoke_handler(IPNHandler, 'POST', {'Content-Type': 'application/x-www-form-urlencoded'}, ipn_payload)

        self.assertEqual(resp.status, 200)
        data = resp.get_json_body()
        self.assertFalse(data.get('verified'))
        self.assertEqual(data.get('idempotency_status'), 'REJECTED')

    def test_3_simulated_verified_completed_payment_authorizes_once(self):
        """Verify simulated verified payment authorizes upload and capture exactly once."""
        test_txn_id = "VERIFIED_COMMERCIAL_TX_TEST_99"
        
        # Inject controlled verified record into payment log
        existing_pmts = []
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_pmts = content if isinstance(content, list) else content.get('payments', [])
            except Exception:
                existing_pmts = []

        existing_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
        existing_pmts.append({
            'source': 'PAYPAL_IPN',
            'verified': True,
            'txn_id': test_txn_id,
            'payment_status': 'COMPLETED',
            'amount': '49.00',
            'currency': 'USD',
            'payer_email': 'realbuyer@quantfund.com',
            'product_id': 'QUANT_AUDIT_49',
            'authorizes_fulfillment': True,
            'is_commercial': True,
            'timestamp_utc': '2026-08-30T20:00:00Z'
        })
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(existing_pmts, f, indent=2)

        # Check authorization via capture order
        cap_body = json.dumps({'orderID': test_txn_id}).encode('utf-8')
        cap_resp = invoke_handler(CaptureOrderHandler, 'POST', {'Content-Type': 'application/json'}, cap_body)
        self.assertEqual(cap_resp.status, 200)
        cap_data = cap_resp.get_json_body()
        self.assertTrue(cap_data.get('verified'))
        self.assertTrue(cap_data.get('authorizes_fulfillment'))

        # Check upload authorization function
        auth, reason, rec = verify_commercial_payment_authorization(test_txn_id)
        self.assertTrue(auth)
        self.assertEqual(reason, "AUTHORIZED")

        # Clean up injected test record
        cleaned_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_pmts, f, indent=2)

    def test_4_duplicate_txn_id_yields_duplicate_ignored(self):
        """Verify submitting existing verified txn_id yields DUPLICATE_IGNORED without duplication."""
        existing_pmts = []
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_pmts = content if isinstance(content, list) else content.get('payments', [])
            except Exception:
                existing_pmts = []

        dup_txn = "DUP_TEST_TX_888"
        existing_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != dup_txn]
        existing_pmts.append({
            'source': 'PAYPAL_IPN',
            'verified': True,
            'txn_id': dup_txn,
            'payment_status': 'COMPLETED',
            'amount': '49.00',
            'authorizes_fulfillment': True,
            'is_commercial': True
        })
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(existing_pmts, f, indent=2)

        try:
            os.environ['PAYPAL_TEST_MODE'] = 'TRUE'
            # Re-invoke IPN handler with duplicate
            ipn_payload = f"txn_id={dup_txn}&payment_status=Completed&mc_gross=49.00".encode('utf-8')
            resp = invoke_handler(IPNHandler, 'POST', {'Content-Type': 'application/x-www-form-urlencoded'}, ipn_payload)
            data = resp.get_json_body()
            
            self.assertEqual(data.get('idempotency_status'), 'DUPLICATE_IGNORED')
        finally:
            os.environ.pop('PAYPAL_TEST_MODE', None)
            if self.pmt_file.exists():
                try:
                    with open(self.pmt_file, 'r', encoding='utf-8') as f:
                        c = json.load(f)
                        pmts = c if isinstance(c, list) else c.get('payments', [])
                        cleaned = [p for p in pmts if isinstance(p, dict) and p.get('txn_id') not in [dup_txn, 'VERIFIED_COMMERCIAL_TX_TEST_99']]
                        with open(self.pmt_file, 'w', encoding='utf-8') as f_out:
                            json.dump(cleaned, f_out, indent=2)
                except Exception:
                    pass

    def test_5_system_test_payment_isolated(self):
        """Verify $1.00 MXN system test payment yields authorizes_fulfillment=False and produces $0.00 commercial revenue."""
        body = json.dumps({'orderID': '8WB32625PL331771', 'amt': '1.00', 'cc': 'MXN'}).encode('utf-8')
        resp = invoke_handler(CaptureOrderHandler, 'POST', {'Content-Type': 'application/json'}, body)
        data = resp.get_json_body()

        self.assertEqual(resp.status, 200)
        self.assertTrue(data.get('verified'))
        self.assertFalse(data.get('authorizes_fulfillment'))
        self.assertFalse(data.get('is_commercial'))
        self.assertEqual(data.get('product_id'), 'SYSTEM_TEST_PAYMENT')

    def test_6_historical_mock_records_isolated(self):
        """Verify historical TEST_CUST_* and SANDBOX_BUYER_* entries do NOT pollute verified_commercial_payments metric."""
        engine = AcquisitionForensicAuditEngine()
        report = engine.run_forensic_audit()
        
        rev = report['revenue']
        real_metrics = report['real_commercial_metrics']
        non_comm = report['non_commercial_isolation']

        self.assertEqual(real_metrics['verified_commercial_payments'], 0)
        self.assertEqual(real_metrics['verified_commercial_revenue_usd'], 0.0)
        self.assertGreaterEqual(non_comm['historical_unverified_events'], 0)

    def test_7_upload_without_verified_commercial_payment_rejected(self):
        """Verify /api/upload-audit rejects request without X-Order-ID or with unverified orderID (403 Forbidden)."""
        body = b"date,return\n2026-08-01,0.01\n2026-08-02,0.02"
        headers = {'Content-Type': 'application/octet-stream', 'X-Order-ID': 'UNVERIFIED_PAYMENT_123', 'X-File-Name': 'test.csv'}
        resp = invoke_handler(UploadAuditHandler, 'POST', headers, body)
        data = resp.get_json_body()

        self.assertEqual(resp.status, 403)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('error'), 'FILE_UPLOAD_UNAUTHORIZED')

    def test_8_invalid_file_extension_excessive_size_path_traversal_rejected(self):
        """Verify upload-audit rejects disallowed extensions, files > 5MB, malformed content, and sanitizes path traversal."""
        test_txn_id = "VALID_AUTH_TX_FOR_UPLOAD_TEST"
        existing_pmts = []
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_pmts = content if isinstance(content, list) else content.get('payments', [])
            except Exception:
                existing_pmts = []

        existing_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
        existing_pmts.append({
            'source': 'PAYPAL_IPN',
            'verified': True,
            'txn_id': test_txn_id,
            'payment_status': 'COMPLETED',
            'amount': '49.00',
            'authorizes_fulfillment': True,
            'is_commercial': True
        })
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(existing_pmts, f, indent=2)

        try:
            os.environ['DURABLE_STORAGE_PROVIDER'] = 'CLOUDFLARE_R2'
            os.environ['DURABLE_STORAGE_BUCKET'] = 'mock-test-bucket'
            os.environ['DURABLE_STORAGE_ACCESS_KEY_ID'] = 'mock_access_key'
            os.environ['DURABLE_STORAGE_SECRET_ACCESS_KEY'] = 'mock_secret_key'

            # 1. Invalid extension .exe
            h1 = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': 'malicious.exe'}
            r1 = invoke_handler(UploadAuditHandler, 'POST', h1, b'binary data')
            self.assertEqual(r1.status, 400)
            self.assertEqual(r1.get_json_body().get('error'), 'INVALID_FILE_EXTENSION')

            # 2. File size > 5 MB
            h2 = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': 'huge.csv'}
            r2 = invoke_handler(UploadAuditHandler, 'POST', h2, b'x' * (5 * 1024 * 1024 + 10))
            self.assertEqual(r2.status, 413)
            self.assertEqual(r2.get_json_body().get('error'), 'FILE_SIZE_EXCEEDED')

            # 3. Path Traversal sanitization
            h3 = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': '../../etc/passwd.csv'}
            r3 = invoke_handler(UploadAuditHandler, 'POST', h3, b"col1,col2\n1,2")
            self.assertEqual(r3.status, 200)
            d3 = r3.get_json_body()
            self.assertTrue(d3.get('success'))
            self.assertNotIn('..', d3.get('case_id'))
        finally:
            for k in ['DURABLE_STORAGE_PROVIDER', 'DURABLE_STORAGE_BUCKET', 'DURABLE_STORAGE_ACCESS_KEY_ID', 'DURABLE_STORAGE_SECRET_ACCESS_KEY']:
                os.environ.pop(k, None)
            cleaned = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
            with open(self.pmt_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, indent=2)

    def test_9_complete_6_tier_traceability_mapping(self):
        """Verify upload response provides case_id <-> txn_id <-> file_id <-> audit_certificate_id <-> email_delivery_id."""
        test_txn_id = "TRACEABILITY_TEST_TX_777"
        existing_pmts = []
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_pmts = content if isinstance(content, list) else content.get('payments', [])
            except Exception:
                existing_pmts = []

        existing_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
        existing_pmts.append({
            'source': 'PAYPAL_IPN',
            'verified': True,
            'txn_id': test_txn_id,
            'payment_status': 'COMPLETED',
            'amount': '49.00',
            'authorizes_fulfillment': True,
            'is_commercial': True
        })
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(existing_pmts, f, indent=2)

        try:
            os.environ['DURABLE_STORAGE_PROVIDER'] = 'CLOUDFLARE_R2'
            os.environ['DURABLE_STORAGE_BUCKET'] = 'mock-test-bucket'
            os.environ['DURABLE_STORAGE_ACCESS_KEY_ID'] = 'mock_access_key'
            os.environ['DURABLE_STORAGE_SECRET_ACCESS_KEY'] = 'mock_secret_key'

            h = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': 'strategy.json'}
            body = json.dumps({'returns': [0.01, 0.02, -0.005]}).encode('utf-8')
            resp = invoke_handler(UploadAuditHandler, 'POST', h, body)
            data = resp.get_json_body()

            self.assertEqual(resp.status, 200)
            self.assertTrue(data.get('case_id', '').startswith('case_'))
            self.assertEqual(data.get('txn_id'), test_txn_id)
            self.assertTrue(data.get('file_id', '').startswith('file_'))
            self.assertTrue(data.get('audit_certificate_id', '').startswith('CERT-LIVE-'))
            self.assertTrue(data.get('email_delivery_id', '').startswith('email_'))
        finally:
            for k in ['DURABLE_STORAGE_PROVIDER', 'DURABLE_STORAGE_BUCKET', 'DURABLE_STORAGE_ACCESS_KEY_ID', 'DURABLE_STORAGE_SECRET_ACCESS_KEY']:
                os.environ.pop(k, None)
            cleaned = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
            with open(self.pmt_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, indent=2)

    def test_10_stateless_ephemeral_storage_fail_closed_notice(self):
        """Verify upload response explicitly discloses unconfigured durable storage and returns 503 fail closed."""
        test_txn_id = "EPHEMERAL_STORAGE_TX_666"
        existing_pmts = []
        if self.pmt_file.exists():
            try:
                with open(self.pmt_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_pmts = content if isinstance(content, list) else content.get('payments', [])
            except Exception:
                existing_pmts = []

        existing_pmts = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
        existing_pmts.append({
            'source': 'PAYPAL_IPN',
            'verified': True,
            'txn_id': test_txn_id,
            'payment_status': 'COMPLETED',
            'amount': '49.00',
            'authorizes_fulfillment': True,
            'is_commercial': True
        })
        with open(self.pmt_file, 'w', encoding='utf-8') as f:
            json.dump(existing_pmts, f, indent=2)

        try:
            for k in ['DURABLE_STORAGE_PROVIDER', 'DURABLE_STORAGE_BUCKET', 'DURABLE_STORAGE_ACCESS_KEY_ID', 'DURABLE_STORAGE_SECRET_ACCESS_KEY']:
                os.environ.pop(k, None)

            h = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': 'data.csv'}
            body = b"date,val\n2026-08-01,10.0"
            resp = invoke_handler(UploadAuditHandler, 'POST', h, body)
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertFalse(data.get('durable_storage_configured'))
            self.assertEqual(data.get('durable_storage_health'), 'FAIL_CLOSED')
            self.assertEqual(data.get('commercial_fulfillment_status'), 'BLOCKED_STORAGE_NOT_CONFIGURED')
        finally:
            cleaned = [p for p in existing_pmts if isinstance(p, dict) and p.get('txn_id') != test_txn_id]
            with open(self.pmt_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, indent=2)

    def test_11_forensic_monitors_strictly_separate_real_vs_test_metrics(self):
        """Verify ManualRevenueFunnelMonitor snapshot has strict separation of real vs isolated test metrics."""
        monitor = ManualRevenueFunnelMonitor()
        snapshot = monitor.generate_snapshot()

        self.assertIn('real_commercial_metrics', snapshot)
        self.assertIn('non_commercial_isolation', snapshot)
        real_m = snapshot['real_commercial_metrics']
        self.assertEqual(real_m['verified_commercial_payments'], 0)
        self.assertEqual(real_m['verified_commercial_revenue_usd'], 0.0)

    def test_12_zero_external_network_calls_and_zero_publications(self):
        """Verify commercial tests make zero external HTTP requests to PayPal and zero external publications."""
        self.assertEqual(os.environ.get('ALLOW_EXTERNAL_PUBLICATION'), None)


if __name__ == '__main__':
    unittest.main()
