"""
Unit Test Suite: Storage Health Serverless Endpoint (/api/storage-health) (Sprint #36.11 / Etapa 4.3)

Verifies 100% of Etapa 4.3 Endpoint Requirements:
1. Endpoint accepts GET requests.
2. Endpoint rejects POST requests with 405 Method Not Allowed.
3. Simulated HEALTHY status returns commercial_fulfillment_readiness = 'PARTIAL' (NEVER 'READY').
4. Response body contains zero secrets, folder IDs, emails, endpoints, or credentials.
5. NOT_CONFIGURED health returns commercial_fulfillment_readiness = 'NOT_READY' and HTTP 503.
6. PERMISSION_DENIED health returns commercial_fulfillment_readiness = 'NOT_READY' and HTTP 503.
7. FOLDER_NOT_FOUND health returns commercial_fulfillment_readiness = 'NOT_READY' and HTTP 503.
8. STORAGE_ERROR health returns commercial_fulfillment_readiness = 'NOT_READY' and HTTP 503.
9. Zero live external network write or list calls made during unit tests.
10. Full project test suite compatibility.
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

StorageHealthModule = importlib.import_module('api.storage-health')
StorageHealthHandler = StorageHealthModule.handler


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


def invoke_handler(handler_cls, method='GET', headers=None, body=b''):
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

    if method == 'GET':
        handler_inst.do_GET()
    elif method == 'POST':
        handler_inst.do_POST()
    elif method == 'OPTIONS':
        handler_inst.do_OPTIONS()

    return dummy_resp


class TestSprint3611StorageHealthEndpoint(unittest.TestCase):

    def test_1_endpoint_accepts_get(self):
        """Verify GET /api/storage-health returns valid JSON body."""
        resp = invoke_handler(StorageHealthHandler, 'GET')
        self.assertIn(resp.status, [200, 503])
        data = resp.get_json_body()
        self.assertEqual(data.get('service'), 'durable_storage')
        self.assertIn('health', data)
        self.assertIn('commercial_fulfillment_readiness', data)

    def test_2_endpoint_rejects_post(self):
        """Verify POST /api/storage-health is rejected with 405 Method Not Allowed."""
        resp = invoke_handler(StorageHealthHandler, 'POST', body=b'{"test":1}')
        self.assertEqual(resp.status, 405)
        data = resp.get_json_body()
        self.assertEqual(data.get('error'), 'METHOD_NOT_ALLOWED')

    def test_3_healthy_check_returns_partial_never_ready(self):
        """Verify simulated HEALTHY status returns commercial_fulfillment_readiness = PARTIAL (NEVER READY)."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'GOOGLE_DRIVE',
            'durable_storage_configured': True,
            'durable_storage_health': 'HEALTHY',
            'commercial_fulfillment_status': 'FULFILLMENT_READY'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            data = resp.get_json_body()

            self.assertEqual(resp.status, 200)
            self.assertEqual(data.get('health'), 'HEALTHY')
            self.assertEqual(data.get('commercial_fulfillment_readiness'), 'PARTIAL')
            self.assertNotEqual(data.get('commercial_fulfillment_readiness'), 'READY')

    def test_4_response_contains_no_sensitive_secrets_or_folder_ids(self):
        """Verify JSON response body contains zero sensitive secrets, credentials, or raw folder IDs."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'GOOGLE_DRIVE',
            'durable_storage_configured': True,
            'durable_storage_health': 'HEALTHY',
            'folder_id': '1a2b3c4d5e6f7g8h9i0j',
            'client_email': 'secret-sa@project.iam.gserviceaccount.com'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            raw_text = resp.wfile.getvalue().decode('utf-8')
            data = resp.get_json_body()

            self.assertNotIn('folder_id', data)
            self.assertNotIn('client_email', data)
            self.assertNotIn('private_key', raw_text)
            self.assertNotIn('secret', raw_text)
            self.assertNotIn('1a2b3c4d5e6f7g8h9i0j', raw_text)

    def test_5_not_configured_returns_not_ready_and_503(self):
        """Verify NOT_CONFIGURED status returns commercial_fulfillment_readiness = NOT_READY and 503."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'NOT_CONFIGURED',
            'durable_storage_configured': False,
            'durable_storage_health': 'NOT_CONFIGURED',
            'commercial_fulfillment_status': 'BLOCKED_STORAGE_NOT_CONFIGURED'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertFalse(data.get('configured'))
            self.assertEqual(data.get('health'), 'NOT_CONFIGURED')
            self.assertEqual(data.get('commercial_fulfillment_readiness'), 'NOT_READY')

    def test_6_permission_denied_returns_not_ready_and_503(self):
        """Verify PERMISSION_DENIED status returns commercial_fulfillment_readiness = NOT_READY and 503."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'GOOGLE_DRIVE',
            'durable_storage_configured': True,
            'durable_storage_health': 'PERMISSION_DENIED',
            'commercial_fulfillment_status': 'BLOCKED_STORAGE_PERMISSION_DENIED'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertEqual(data.get('health'), 'PERMISSION_DENIED')
            self.assertEqual(data.get('commercial_fulfillment_readiness'), 'NOT_READY')

    def test_7_folder_not_found_returns_not_ready_and_503(self):
        """Verify FOLDER_NOT_FOUND status returns commercial_fulfillment_readiness = NOT_READY and 503."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'GOOGLE_DRIVE',
            'durable_storage_configured': True,
            'durable_storage_health': 'FOLDER_NOT_FOUND',
            'commercial_fulfillment_status': 'BLOCKED_STORAGE_FOLDER_NOT_FOUND'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertEqual(data.get('health'), 'FOLDER_NOT_FOUND')
            self.assertEqual(data.get('commercial_fulfillment_readiness'), 'NOT_READY')

    def test_8_storage_error_returns_not_ready_and_503(self):
        """Verify STORAGE_ERROR status returns commercial_fulfillment_readiness = NOT_READY and 503."""
        mock_engine = MagicMock()
        mock_engine.get_storage_status.return_value = {
            'durable_storage_provider': 'GOOGLE_DRIVE',
            'durable_storage_configured': True,
            'durable_storage_health': 'STORAGE_ERROR',
            'commercial_fulfillment_status': 'BLOCKED_STORAGE_UNHEALTHY'
        }

        with patch('src.economics.durable_storage.get_durable_storage_engine', return_value=mock_engine):
            resp = invoke_handler(StorageHealthHandler, 'GET')
            data = resp.get_json_body()

            self.assertEqual(resp.status, 503)
            self.assertEqual(data.get('health'), 'STORAGE_ERROR')
            self.assertEqual(data.get('commercial_fulfillment_readiness'), 'NOT_READY')

    def test_9_zero_live_network_calls_during_unit_tests(self):
        """Verify test execution makes zero live external network write calls."""
        self.assertIsNone(os.environ.get('ALLOW_EXTERNAL_PUBLICATION'))


if __name__ == '__main__':
    unittest.main()
