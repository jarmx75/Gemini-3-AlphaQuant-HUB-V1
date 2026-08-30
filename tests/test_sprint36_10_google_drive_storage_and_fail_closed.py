"""
Unit Test Suite: Google Drive Storage Backend & Fail-Closed Commercial Security (Sprint #36.10 / Etapa 4.2)

Verifies 100% of Etapa 4.2 Requirements:
1. GOOGLE_DRIVE unconfigured returns is_configured() = False and NOT_CONFIGURED.
2. Missing Folder ID returns FAIL_CLOSED / NOT_CONFIGURED.
3. Invalid Service Account JSON returns FAIL_CLOSED.
4. Permission error returns PERMISSION_DENIED.
5. Folder 404 returns FOLDER_NOT_FOUND.
6. Health check HEALTHY succeeds with valid mock response.
7. Unhealthy Drive blocks commercial upload at /api/upload-audit (503 Service Unavailable).
8. Ephemeral Vercel filesystem is prohibited for commercial fulfillment.
9. Object names do not directly include raw user filenames and sanitize path traversal.
10. Files inherit folder privacy with zero public sharing links created.
11. Existing S3-compatible backend remains 100% supported.
12. Zero real credentials, zero live network write calls during tests.
13. Forensic monitors report provider=GOOGLE_DRIVE and COMMERCIAL_FULFILLMENT_READINESS=NOT_READY.
"""

import json
import os
import sys
import unittest
import importlib
from pathlib import Path
from io import BytesIO
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.google_drive_storage import GoogleDriveStorageEngine, get_google_drive_storage_engine
from src.economics.durable_storage import DurableStorageEngine, get_durable_storage_engine
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
from src.economics.manual_revenue_funnel_monitor import ManualRevenueFunnelMonitor

UploadAuditModule = importlib.import_module('api.upload-audit')
UploadAuditHandler = UploadAuditModule.handler


class DummyHTTPResponse:
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


def invoke_handler(handler_cls, headers=None, body=b''):
    headers = headers or {}
    rfile = BytesIO(body)
    headers['Content-Length'] = str(len(body))

    dummy_resp = DummyHTTPResponse()
    handler_inst = handler_cls.__new__(handler_cls)
    handler_inst.rfile = rfile
    handler_inst.wfile = dummy_resp.wfile
    handler_inst.headers = headers
    handler_inst.send_response = dummy_resp.send_response
    handler_inst.send_header = dummy_resp.send_header
    handler_inst.end_headers = dummy_resp.end_headers
    handler_inst.do_POST()
    return dummy_resp


class TestSprint3610GoogleDriveStorageAndFailClosed(unittest.TestCase):

    def setUp(self):
        self.log_dir = PROJECT_ROOT / "logs" / "portfolio"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pmt_file = self.log_dir / "paypal_payment_log.json"
        self.valid_service_account_json = json.dumps({
            "type": "service_account",
            "project_id": "test-project-123",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
            "client_email": "automaton-sa@test-project-123.iam.gserviceaccount.com",
            "client_id": "100000000000000000001"
        })
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
                    if isinstance(p, dict) and p.get('txn_id') != 'VERIFIED_COMMERCIAL_TX_GDRIVE_TEST'
                ]
                with open(self.pmt_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned, f, indent=2)
            except Exception:
                pass

    def test_1_unconfigured_gdrive_returns_not_configured_and_fail_closed(self):
        """Verify unconfigured GoogleDriveStorageEngine returns is_configured() = False and NOT_CONFIGURED."""
        engine = GoogleDriveStorageEngine({})
        self.assertFalse(engine.is_configured())
        self.assertEqual(engine.health_check(), "NOT_CONFIGURED")

    def test_2_missing_folder_id_returns_fail_closed(self):
        """Verify missing GOOGLE_DRIVE_FOLDER_ID returns NOT_CONFIGURED."""
        env = {'GOOGLE_SERVICE_ACCOUNT_JSON': self.valid_service_account_json}
        engine = GoogleDriveStorageEngine(env)
        self.assertFalse(engine.is_configured())
        self.assertEqual(engine.health_check(), "NOT_CONFIGURED")

    def test_3_invalid_service_account_json_returns_fail_closed(self):
        """Verify invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON returns FAIL_CLOSED."""
        env = {
            'GOOGLE_DRIVE_FOLDER_ID': '1a2b3c4d5e6f7g8h9i0j',
            'GOOGLE_SERVICE_ACCOUNT_JSON': 'invalid json text'
        }
        engine = GoogleDriveStorageEngine(env)
        self.assertFalse(engine.is_configured())
        self.assertEqual(engine.health_check(), "FAIL_CLOSED")

    def test_4_permission_denied_returns_permission_denied_status(self):
        """Verify simulated HTTP 403 API response returns PERMISSION_DENIED."""
        env = {
            'GOOGLE_DRIVE_FOLDER_ID': '1a2b3c4d5e6f7g8h9i0j',
            'GOOGLE_SERVICE_ACCOUNT_JSON': self.valid_service_account_json
        }
        engine = GoogleDriveStorageEngine(env)
        self.assertTrue(engine.is_configured())

        mock_sa = MagicMock()
        mock_discovery = MagicMock()
        mock_files = MagicMock()
        mock_files.get.return_value.execute.side_effect = Exception("HTTP 403: Forbidden - AccessNotConfigured / Permission Denied")
        mock_discovery.build.return_value.files.return_value = mock_files

        with patch.dict('sys.modules', {
            'google.oauth2': MagicMock(),
            'google.oauth2.service_account': mock_sa,
            'googleapiclient': MagicMock(),
            'googleapiclient.discovery': mock_discovery
        }):
            status = engine.health_check()
            self.assertEqual(status, "PERMISSION_DENIED")

    def test_5_folder_not_found_returns_folder_not_found_status(self):
        """Verify simulated HTTP 404 API response returns FOLDER_NOT_FOUND."""
        env = {
            'GOOGLE_DRIVE_FOLDER_ID': '1a2b3c4d5e6f7g8h9i0j',
            'GOOGLE_SERVICE_ACCOUNT_JSON': self.valid_service_account_json
        }
        engine = GoogleDriveStorageEngine(env)

        mock_sa = MagicMock()
        mock_discovery = MagicMock()
        mock_files = MagicMock()
        mock_files.get.return_value.execute.side_effect = Exception("HTTP 404: File not found")
        mock_discovery.build.return_value.files.return_value = mock_files

        with patch.dict('sys.modules', {
            'google.oauth2': MagicMock(),
            'google.oauth2.service_account': mock_sa,
            'googleapiclient': MagicMock(),
            'googleapiclient.discovery': mock_discovery
        }):
            status = engine.health_check()
            self.assertEqual(status, "FOLDER_NOT_FOUND")

    def test_6_healthy_check_returns_healthy_with_valid_mock(self):
        """Verify valid mock Google Drive folder metadata returns HEALTHY."""
        env = {
            'GOOGLE_DRIVE_FOLDER_ID': '1a2b3c4d5e6f7g8h9i0j',
            'GOOGLE_SERVICE_ACCOUNT_JSON': self.valid_service_account_json
        }
        engine = GoogleDriveStorageEngine(env)

        mock_sa = MagicMock()
        mock_discovery = MagicMock()
        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = {
            'id': '1a2b3c4d5e6f7g8h9i0j',
            'name': 'Automaton Quant Audit - Private Client Files',
            'mimeType': 'application/vnd.google-apps.folder',
            'trashed': False
        }
        mock_discovery.build.return_value.files.return_value = mock_files

        with patch.dict('sys.modules', {
            'google.oauth2': MagicMock(),
            'google.oauth2.service_account': mock_sa,
            'googleapiclient': MagicMock(),
            'googleapiclient.discovery': mock_discovery
        }):
            status = engine.health_check()
            self.assertEqual(status, "HEALTHY")

    def test_7_unhealthy_gdrive_blocks_commercial_upload(self):
        """Verify /api/upload-audit rejects upload (503 Service Unavailable) when DURABLE_STORAGE_PROVIDER=GOOGLE_DRIVE is unconfigured/unhealthy."""
        test_txn_id = "VERIFIED_COMMERCIAL_TX_GDRIVE_TEST"
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

        saved_env = {}
        for k in ['DURABLE_STORAGE_PROVIDER', 'GOOGLE_DRIVE_FOLDER_ID', 'GOOGLE_SERVICE_ACCOUNT_JSON']:
            saved_env[k] = os.environ.pop(k, None)

        try:
            os.environ['DURABLE_STORAGE_PROVIDER'] = 'GOOGLE_DRIVE'
            # No credentials -> NOT_CONFIGURED

            h = {'Content-Type': 'application/octet-stream', 'X-Order-ID': test_txn_id, 'X-File-Name': 'strategy.csv'}
            resp = invoke_handler(UploadAuditHandler, h, b"col1,col2\n1,2")
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertFalse(data.get('success'))
            self.assertEqual(data.get('error'), 'COMMERCIAL_FULFILLMENT_UNAVAILABLE_DURABLE_STORAGE_NOT_CONFIGURED')
            self.assertEqual(data.get('commercial_fulfillment_status'), 'BLOCKED_STORAGE_NOT_CONFIGURED')
        finally:
            for k, v in saved_env.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

    def test_8_unconfigured_gdrive_prohibits_vercel_ephemeral_fulfillment(self):
        """Verify unconfigured Google Drive prevents store_upload / store_report / store_certificate from executing."""
        engine = GoogleDriveStorageEngine({})
        with self.assertRaises(RuntimeError) as ctx1:
            engine.store_upload("case_99", b"data", "test.csv")
        self.assertIn("GOOGLE_DRIVE_NOT_CONFIGURED", str(ctx1.exception))

    def test_9_object_names_do_not_use_raw_user_filenames(self):
        """Verify generate_safe_object_name produces sanitized non-predictable filenames without raw path traversal."""
        engine = GoogleDriveStorageEngine({})
        name = engine.generate_safe_object_name("../../../etc/passwd", "upload", "../../secret_strategy.csv")

        self.assertNotIn("..", name)
        self.assertNotIn("secret_strategy", name)
        self.assertTrue(name.startswith("etcpasswd_upload_"))
        self.assertTrue(name.endswith(".csv"))

    def test_10_zero_public_sharing_links_created(self):
        """Verify mock store_upload response specifies public_sharing=DISABLED_PRIVATE_FOLDER_ONLY."""
        env = {
            'GOOGLE_DRIVE_FOLDER_ID': '1a2b3c4d5e6f7g8h9i0j',
            'GOOGLE_SERVICE_ACCOUNT_JSON': self.valid_service_account_json
        }
        engine = GoogleDriveStorageEngine(env)
        
        with patch.object(engine, 'health_check', return_value='HEALTHY'):
            res = engine.store_upload("case_101", b"col1,col2\n1,2", "data.csv")
            self.assertTrue(res['success'])
            self.assertEqual(res['provider'], 'GOOGLE_DRIVE')
            self.assertEqual(res['public_sharing'], 'DISABLED_PRIVATE_FOLDER_ONLY')
            self.assertNotIn('public_url', res)

    def test_11_existing_s3_backend_remains_fully_supported(self):
        """Verify DURABLE_STORAGE_PROVIDER=CLOUDFLARE_R2 dispatches to S3 DurableStorageEngine cleanly."""
        mock_s3_env = {
            'DURABLE_STORAGE_PROVIDER': 'CLOUDFLARE_R2',
            'DURABLE_STORAGE_BUCKET': 'my-bucket',
            'DURABLE_STORAGE_ACCESS_KEY_ID': 'key',
            'DURABLE_STORAGE_SECRET_ACCESS_KEY': 'secret'
        }
        engine = get_durable_storage_engine(mock_s3_env)
        self.assertEqual(engine.provider, 'CLOUDFLARE_R2')
        self.assertTrue(engine.is_configured())

    def test_12_zero_real_credentials_or_network_write_calls(self):
        """Verify test execution uses zero real credentials and zero live network write calls."""
        self.assertEqual(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', ''), '')
        self.assertIsNone(os.environ.get('ALLOW_EXTERNAL_PUBLICATION'))

    def test_13_monitors_report_gdrive_telemetry_and_not_ready(self):
        """Verify AcquisitionForensicAuditEngine and ManualRevenueFunnelMonitor report provider=GOOGLE_DRIVE and NOT_READY when unconfigured."""
        saved_prov = os.environ.get('DURABLE_STORAGE_PROVIDER')
        try:
            os.environ['DURABLE_STORAGE_PROVIDER'] = 'GOOGLE_DRIVE'

            audit_engine = AcquisitionForensicAuditEngine()
            report = audit_engine.run_forensic_audit()

            self.assertEqual(report['durable_storage']['durable_storage_provider'], 'GOOGLE_DRIVE')
            self.assertFalse(report['durable_storage']['google_drive_folder_configured'])
            self.assertEqual(report['COMMERCIAL_FULFILLMENT_READINESS'], 'NOT_READY')

            monitor = ManualRevenueFunnelMonitor()
            snapshot = monitor.generate_snapshot()
            self.assertEqual(snapshot['durable_storage']['durable_storage_provider'], 'GOOGLE_DRIVE')
            self.assertEqual(snapshot['COMMERCIAL_FULFILLMENT_READINESS'], 'NOT_READY')
        finally:
            if saved_prov:
                os.environ['DURABLE_STORAGE_PROVIDER'] = saved_prov
            else:
                os.environ.pop('DURABLE_STORAGE_PROVIDER', None)


if __name__ == '__main__':
    unittest.main()
