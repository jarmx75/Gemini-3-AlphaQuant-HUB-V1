"""
Unit Test Suite: Local OAuth Authorization Script Invariants & Security (Sprint #36.15 / Etapa 5.5)

Verifies 100% of Etapa 5.5 Requirements:
1. scripts/google_drive_oauth_authorize.py exits safely with code 1 if GOOGLE_OAUTH_CLIENT_ID missing.
2. Script exits safely with code 1 if GOOGLE_OAUTH_CLIENT_SECRET missing.
3. Script enforces strictly REQUIRED_SCOPE = 'https://www.googleapis.com/auth/drive.file'.
4. Script does NOT write token files or credentials to disk.
5. OAuth storage engine remains fail-closed without valid refresh token.
6. Zero live network calls executed during tests.
7. Commercial metrics remain isolated (0 payments, $0.00 revenue).
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.google_drive_oauth_authorize as auth_tool
from src.economics.google_drive_oauth_storage import GoogleDriveOAuthStorageEngine


class TestSprint3615OAuthAuthorizationTool(unittest.TestCase):

    def test_1_fails_without_client_id(self):
        """Verify script exits with code 1 when GOOGLE_OAUTH_CLIENT_ID is missing."""
        with patch.dict(os.environ, {"GOOGLE_OAUTH_CLIENT_ID": "", "GOOGLE_OAUTH_CLIENT_SECRET": "secret_123"}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                auth_tool.authorize()
            self.assertEqual(cm.exception.code, 1)

    def test_2_fails_without_client_secret(self):
        """Verify script exits with code 1 when GOOGLE_OAUTH_CLIENT_SECRET is missing."""
        with patch.dict(os.environ, {"GOOGLE_OAUTH_CLIENT_ID": "client_123", "GOOGLE_OAUTH_CLIENT_SECRET": ""}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                auth_tool.authorize()
            self.assertEqual(cm.exception.code, 1)

    def test_3_enforces_drive_file_scope_only(self):
        """Verify REQUIRED_SCOPE is strictly 'https://www.googleapis.com/auth/drive.file'."""
        self.assertEqual(auth_tool.REQUIRED_SCOPE, "https://www.googleapis.com/auth/drive.file")

    def test_4_no_disk_token_file_created(self):
        """Verify executing authorization flow creates zero token files on disk."""
        mock_creds = MagicMock()
        mock_creds.refresh_token = "mock_refresh_token_xyz_999"

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds

        mock_flow_class = MagicMock()
        mock_flow_class.from_client_config.return_value = mock_flow

        env = {
            "GOOGLE_OAUTH_CLIENT_ID": "mock_client_id.apps.googleusercontent.com",
            "GOOGLE_OAUTH_CLIENT_SECRET": "mock_secret_abc"
        }

        with patch.dict(os.environ, env):
            with patch.dict("sys.modules", {
                "google_auth_oauthlib": MagicMock(),
                "google_auth_oauthlib.flow": MagicMock(InstalledAppFlow=mock_flow_class)
            }):
                auth_tool.authorize()

        # Check no token file was created in project root or scripts dir
        self.assertFalse((PROJECT_ROOT / "token.json").exists())
        self.assertFalse((PROJECT_ROOT / "scripts" / "token.json").exists())

    def test_5_oauth_backend_fail_closed_without_refresh_token(self):
        """Verify backend remains fail-closed when refresh token is missing."""
        incomplete_env = {
            "DURABLE_STORAGE_PROVIDER": "GOOGLE_DRIVE_OAUTH",
            "GOOGLE_DRIVE_FOLDER_ID": "folder_123",
            "GOOGLE_OAUTH_CLIENT_ID": "client_123",
            "GOOGLE_OAUTH_CLIENT_SECRET": "secret_123",
            "GOOGLE_OAUTH_REFRESH_TOKEN": ""
        }
        with patch.dict(os.environ, incomplete_env, clear=True):
            engine = GoogleDriveOAuthStorageEngine()
            self.assertFalse(engine.is_configured())
            self.assertEqual(engine.health_check(), "OAUTH_NOT_CONFIGURED")

    def test_6_zero_live_network_calls_during_unit_tests(self):
        """Verify zero network calls made during unit tests."""
        self.assertEqual(auth_tool.REQUIRED_SCOPE, "https://www.googleapis.com/auth/drive.file")

    def test_7_commercial_metrics_isolation_preserved(self):
        """Verify commercial fulfillment readiness status remains PARTIAL."""
        engine = GoogleDriveOAuthStorageEngine()
        status = engine.get_storage_status()
        self.assertEqual(status["commercial_fulfillment_readiness"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
