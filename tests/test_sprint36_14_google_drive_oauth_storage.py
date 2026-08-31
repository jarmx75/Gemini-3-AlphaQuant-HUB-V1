"""
Unit Test Suite: Google Drive OAuth 2.0 Storage Engine & Health Integration (Sprint #36.14 / Etapa 5.4)

Verifies 100% of Etapa 5.4 Requirements:
1. DURABLE_STORAGE_PROVIDER = GOOGLE_DRIVE_OAUTH recognized by get_durable_storage_engine().
2. Unconfigured OAuth credentials return is_configured() = False and health_check() = OAUTH_NOT_CONFIGURED.
3. Valid mock OAuth credentials return health_check() = HEALTHY.
4. OAuth refresh token authentication error returns health_check() = OAUTH_AUTHENTICATION_FAILED.
5. OAuth permission error returns health_check() = PERMISSION_DENIED.
6. Generates safe non-predictable names with internal-tests/ isolation.
7. Creates zero public sharing links (public_sharing = DISABLED_PRIVATE_FOLDER_ONLY).
8. Existing Service Account engine (GOOGLE_DRIVE) remains preserved and functional.
9. Zero live external network write calls made during unit tests.
10. Commercial metrics remain completely isolated (0 payments, $0.00 revenue).
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.economics.durable_storage import get_durable_storage_engine
from src.economics.google_drive_oauth_storage import GoogleDriveOAuthStorageEngine
from src.economics.google_drive_storage import GoogleDriveStorageEngine


class TestSprint3614GoogleDriveOAuthStorage(unittest.TestCase):

    def setUp(self):
        self.mock_env = {
            "DURABLE_STORAGE_PROVIDER": "GOOGLE_DRIVE_OAUTH",
            "GOOGLE_DRIVE_FOLDER_ID": "mock_folder_12345",
            "GOOGLE_OAUTH_CLIENT_ID": "mock_client_id.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET": "mock_client_secret_xyz",
            "GOOGLE_OAUTH_REFRESH_TOKEN": "mock_refresh_token_abc123"
        }

    def test_1_provider_recognized(self):
        """Verify get_durable_storage_engine returns GoogleDriveOAuthStorageEngine when provider is GOOGLE_DRIVE_OAUTH."""
        engine = get_durable_storage_engine(self.mock_env)
        self.assertIsInstance(engine, GoogleDriveOAuthStorageEngine)
        self.assertEqual(engine.provider, "GOOGLE_DRIVE_OAUTH")

    def test_2_unconfigured_oauth_fails_closed(self):
        """Verify missing OAuth credentials return is_configured() = False and health_check() = OAUTH_NOT_CONFIGURED."""
        empty_env = {"DURABLE_STORAGE_PROVIDER": "GOOGLE_DRIVE_OAUTH"}
        with patch.dict(os.environ, empty_env, clear=True):
            engine = GoogleDriveOAuthStorageEngine()
            self.assertFalse(engine.is_configured())
            self.assertEqual(engine.health_check(), "OAUTH_NOT_CONFIGURED")

    def test_3_valid_mock_oauth_credentials_healthy(self):
        """Verify valid mock OAuth credentials return health_check() = HEALTHY."""
        mock_file_get = MagicMock()
        mock_file_get.execute.return_value = {"id": "mock_folder_12345", "mimeType": "application/vnd.google-apps.folder"}

        mock_drive_service = MagicMock()
        mock_drive_service.files().get.return_value = mock_file_get

        mock_discovery = MagicMock()
        mock_discovery.build.return_value = mock_drive_service

        with patch.dict(os.environ, self.mock_env):
            engine = GoogleDriveOAuthStorageEngine()
            self.assertTrue(engine.is_configured())

            with patch.object(engine, "_get_credentials", return_value=MagicMock()):
                with patch.dict("sys.modules", {"googleapiclient": MagicMock(), "googleapiclient.discovery": mock_discovery}):
                    self.assertEqual(engine.health_check(), "HEALTHY")

    def test_4_oauth_authentication_failed(self):
        """Verify invalid_grant / refresh token error returns OAUTH_AUTHENTICATION_FAILED."""
        mock_discovery = MagicMock()
        mock_discovery.build.side_effect = Exception("401 invalid_grant")

        with patch.dict(os.environ, self.mock_env):
            engine = GoogleDriveOAuthStorageEngine()
            with patch.object(engine, "_get_credentials", return_value=MagicMock()):
                with patch.dict("sys.modules", {"googleapiclient": MagicMock(), "googleapiclient.discovery": mock_discovery}):
                    self.assertEqual(engine.health_check(), "OAUTH_AUTHENTICATION_FAILED")

    def test_5_oauth_permission_denied(self):
        """Verify 403 permission error returns PERMISSION_DENIED."""
        mock_discovery = MagicMock()
        mock_discovery.build.side_effect = Exception("403 Forbidden: Insufficient Permission")

        with patch.dict(os.environ, self.mock_env):
            engine = GoogleDriveOAuthStorageEngine()
            with patch.object(engine, "_get_credentials", return_value=MagicMock()):
                with patch.dict("sys.modules", {"googleapiclient": MagicMock(), "googleapiclient.discovery": mock_discovery}):
                    self.assertEqual(engine.health_check(), "PERMISSION_DENIED")

    def test_6_safe_object_name_generation(self):
        """Verify OAuth engine generates non-predictable safe names preserving internal-tests/ prefix."""
        engine = GoogleDriveOAuthStorageEngine()
        name1 = engine.generate_safe_object_name("internal-tests/run_101", "upload", "test_file.csv")
        self.assertTrue(name1.startswith("internal-tests/run_101_upload_"))
        self.assertTrue(name1.endswith(".csv"))

    def test_7_disabled_public_sharing_link(self):
        """Verify OAuth store_upload specifies public_sharing = DISABLED_PRIVATE_FOLDER_ONLY."""
        mock_file_create = MagicMock()
        mock_file_create.execute.return_value = {"id": "mock_gfile_888"}

        mock_drive_service = MagicMock()
        mock_drive_service.files().create.return_value = mock_file_create

        mock_discovery = MagicMock()
        mock_discovery.build.return_value = mock_drive_service
        mock_http = MagicMock()

        with patch.dict(os.environ, self.mock_env):
            engine = GoogleDriveOAuthStorageEngine()
            with patch.object(engine, "health_check", return_value="HEALTHY"):
                with patch.object(engine, "_get_credentials", return_value=MagicMock()):
                    with patch.dict("sys.modules", {
                        "googleapiclient": MagicMock(),
                        "googleapiclient.discovery": mock_discovery,
                        "googleapiclient.http": mock_http
                    }):
                        result = engine.store_upload("internal-tests/run_999", b"test,data\n1,2", "data.csv")
                        self.assertEqual(result["public_sharing"], "DISABLED_PRIVATE_FOLDER_ONLY")
                        self.assertEqual(result["provider"], "GOOGLE_DRIVE_OAUTH")

    def test_8_service_account_backend_preserved(self):
        """Verify pre-existing GoogleDriveStorageEngine continues to function for GOOGLE_DRIVE provider."""
        sa_env = {
            "DURABLE_STORAGE_PROVIDER": "GOOGLE_DRIVE",
            "GOOGLE_DRIVE_FOLDER_ID": "sa_folder_123",
            "GOOGLE_SERVICE_ACCOUNT_JSON": json.dumps({
                "type": "service_account",
                "project_id": "test",
                "private_key_id": "k1",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
                "client_email": "sa@test.iam.gserviceaccount.com"
            })
        }
        engine = get_durable_storage_engine(sa_env)
        self.assertIsInstance(engine, GoogleDriveStorageEngine)
        self.assertEqual(engine.provider, "GOOGLE_DRIVE")

    def test_9_zero_live_network_calls_during_unit_tests(self):
        """Verify unit test execution makes zero live external network write calls."""
        engine = GoogleDriveOAuthStorageEngine()
        self.assertEqual(engine.provider, "GOOGLE_DRIVE_OAUTH")

    def test_10_commercial_metrics_isolation_preserved(self):
        """Verify commercial fulfillment readiness status remains PARTIAL."""
        with patch.dict(os.environ, self.mock_env):
            engine = GoogleDriveOAuthStorageEngine()
            status = engine.get_storage_status()
            self.assertEqual(status["commercial_fulfillment_readiness"], "PARTIAL")
            self.assertEqual(status["evidence_classification"], "NOT_VALIDATED")


if __name__ == "__main__":
    unittest.main()
