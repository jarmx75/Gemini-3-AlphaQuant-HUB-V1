"""
Google Drive OAuth 2.0 Durable Storage Engine (Sprint #36.14 / Etapa 5.4)

Provides durable, private file persistence in personal Google Drive using OAuth 2.0 refresh tokens.
Eliminates Service Account storage quota limitations (0 byte quota for shared personal folders).

Security Controls & Invariants:
1. Files created via OAuth inherit ownership and 15 GB quota of the user's personal Google account (e.g. jarmx72@gmail.com).
2. Uses official google.oauth2.credentials.Credentials with serverless-compatible refresh_token flow.
3. Does NOT require browser interaction or interactive logins inside Vercel.
4. Generates non-predictable, sanitized filenames with case_id isolation.
5. All uploaded objects remain strictly private (public_sharing = DISABLED_PRIVATE_FOLDER_ONLY).
6. Fails closed (OAUTH_NOT_CONFIGURED / OAUTH_AUTHENTICATION_FAILED / PERMISSION_DENIED) if credentials missing/unhealthy.
"""

import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GoogleDriveOAuthStorageEngine:
    """Storage engine for persisting files into personal Google Drive using OAuth 2.0 credentials."""

    def __init__(self):
        self.folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        self.client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        self.refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()
        self.provider = "GOOGLE_DRIVE_OAUTH"

    def is_configured(self) -> bool:
        """Returns True if all required OAuth 2.0 credentials and folder ID are present."""
        invalid_placeholders = {"REDACTED", "YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET", "YOUR_REFRESH_TOKEN", "YOUR_FOLDER_ID", ""}
        return bool(
            self.folder_id and self.folder_id not in invalid_placeholders and
            self.client_id and self.client_id not in invalid_placeholders and
            self.client_secret and self.client_secret not in invalid_placeholders and
            self.refresh_token and self.refresh_token not in invalid_placeholders
        )

    def _get_credentials(self):
        """Constructs Google OAuth 2.0 credentials object from refresh token."""
        from google.oauth2.credentials import Credentials

        return Credentials(
            token=None,
            refresh_token=self.refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=[
                'https://www.googleapis.com/auth/drive.file'
            ]
        )

    def health_check(self) -> str:
        """
        Validates read accessibility of target Google Drive folder via OAuth 2.0.
        Returns: 'HEALTHY', 'OAUTH_NOT_CONFIGURED', 'OAUTH_AUTHENTICATION_FAILED', 'PERMISSION_DENIED', 'FOLDER_NOT_FOUND'.
        """
        if not self.is_configured():
            return "OAUTH_NOT_CONFIGURED"

        try:
            from googleapiclient.discovery import build

            credentials = self._get_credentials()
            drive_service = build('drive', 'v3', credentials=credentials)

            folder_metadata = drive_service.files().get(
                fileId=self.folder_id,
                fields='id, name, mimeType'
            ).execute()

            if folder_metadata.get('mimeType') != 'application/vnd.google-apps.folder':
                logger.warning(f"[OAUTH DRIVE HEALTH]: Target ID '{self.folder_id[:8]}...' is not a Google Drive folder.")
                return "FOLDER_NOT_FOUND"

            return "HEALTHY"
        except ImportError:
            logger.warning("[OAUTH DRIVE HEALTH]: Required google-api-python-client library missing.")
            return "OAUTH_DEPENDENCY_ERROR"
        except Exception as err:
            err_msg = str(err).lower()
            err_type = type(err).__name__
            logger.warning(f"[OAUTH DRIVE HEALTH ERROR]: {err_type}: {err_msg}")
            if "404" in err_msg or "notfound" in err_msg:
                return "FOLDER_NOT_FOUND"
            elif "403" in err_msg or "permission" in err_msg:
                return "PERMISSION_DENIED"
            elif "401" in err_msg or "invalid_grant" in err_msg or "unauthorized" in err_msg or "token" in err_msg:
                return "OAUTH_AUTHENTICATION_FAILED"
            return "STORAGE_ERROR"

    def get_storage_status(self) -> Dict[str, Any]:
        """Returns metadata status dictionary for diagnostic endpoints."""
        health = self.health_check()
        return {
            "durable_storage_provider": "GOOGLE_DRIVE_OAUTH",
            "durable_storage_configured": self.is_configured(),
            "durable_storage_health": health,
            "google_drive_folder_configured": bool(self.folder_id),
            "commercial_fulfillment_status": "FULFILLMENT_READY" if health == "HEALTHY" else "BLOCKED_STORAGE_UNHEALTHY",
            "evidence_classification": "NOT_VALIDATED",
            "commercial_fulfillment_readiness": "PARTIAL"
        }

    def generate_safe_object_name(self, case_id: str, file_type: str, raw_filename: str = "") -> str:
        """
        Generates safe, sanitized, non-predictable Google Drive file name.
        Preserves 'internal-tests/' prefix if present and isolates by case_id.
        """
        prefix = ""
        clean_case = case_id
        if case_id.startswith("internal-tests/"):
            prefix = "internal-tests/"
            clean_case = case_id[15:]

        sanitized_case = re.sub(r'[^a-zA-Z0-9_\-]', '', clean_case) or f"case_{uuid.uuid4().hex[:8]}"
        sanitized_type = re.sub(r'[^a-zA-Z0-9_\-]', '', file_type) or "data"

        ext = ".data"
        if raw_filename:
            raw_ext = os.path.splitext(os.path.basename(raw_filename))[1].lower()
            if raw_ext in {'.csv', '.json', '.pdf', '.txt'}:
                ext = raw_ext

        random_suffix = uuid.uuid4().hex[:12]
        return f"{prefix}{sanitized_case}_{sanitized_type}_{random_suffix}{ext}"

    def store_upload(self, case_id: str, data: bytes, raw_filename: str = "") -> Dict[str, Any]:
        """
        Uploads file into private personal Google Drive folder using OAuth 2.0.
        Inherits 15 GB storage quota of the personal Google account.
        Fails closed if not configured or unhealthy.
        """
        if not self.is_configured():
            raise RuntimeError("COMMERCIAL_FULFILLMENT_UNAVAILABLE_GOOGLE_DRIVE_OAUTH_NOT_CONFIGURED: Google Drive OAuth storage is not configured.")

        health = self.health_check()
        if health != "HEALTHY":
            raise RuntimeError(f"COMMERCIAL_FULFILLMENT_UNAVAILABLE_STORAGE_UNHEALTHY: Google Drive OAuth health check failed with status '{health}'.")

        object_name = self.generate_safe_object_name(case_id, "upload", raw_filename)

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload
            from io import BytesIO

            credentials = self._get_credentials()
            drive_service = build('drive', 'v3', credentials=credentials)

            file_metadata = {
                'name': object_name,
                'parents': [self.folder_id]
            }
            media = MediaIoBaseUpload(BytesIO(data), mimetype='application/octet-stream', resumable=False)

            drive_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, createdTime'
            ).execute()

            drive_file_id = drive_file.get('id', f"gfile_{uuid.uuid4().hex[:12]}")
            storage_ref = f"gdrive_oauth://{self.folder_id[:8]}.../{drive_file_id}"
        except ImportError:
            raise RuntimeError("GOOGLE_DRIVE_DEPENDENCY_ERROR: Required google-api-python-client dependency is missing.")
        except Exception as err:
            err_msg = str(err).lower()
            err_type = type(err).__name__
            if "403" in err_msg or "permission" in err_msg:
                raise RuntimeError("GOOGLE_DRIVE_WRITE_PERMISSION_DENIED: OAuth account lacks write permission on target Google Drive folder.")
            elif "401" in err_msg or "invalid_grant" in err_msg or "unauthorized" in err_msg:
                raise RuntimeError("GOOGLE_DRIVE_AUTHENTICATION_FAILED: OAuth 2.0 refresh token invalid or expired.")
            elif "404" in err_msg or "notfound" in err_msg:
                raise RuntimeError("GOOGLE_DRIVE_FOLDER_WRITE_ERROR: Target Google Drive folder ID not found or unreachable.")
            raise RuntimeError(f"GOOGLE_DRIVE_UPLOAD_API_ERROR: Google Drive OAuth upload failed ({err_type}).")

        return {
            "success": True,
            "provider": "GOOGLE_DRIVE_OAUTH",
            "drive_file_id": drive_file_id,
            "object_name": object_name,
            "storage_reference": storage_ref,
            "size_bytes": len(data),
            "public_sharing": "DISABLED_PRIVATE_FOLDER_ONLY"
        }

    def store_report(self, case_id: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Uploads JSON audit report into private personal Google Drive folder."""
        raw_bytes = json.dumps(report_data, indent=2).encode('utf-8')
        return self.store_upload(case_id, raw_bytes, "audit_report.json")

    def store_certificate(self, case_id: str, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Uploads JSON certificate into private personal Google Drive folder."""
        raw_bytes = json.dumps(cert_data, indent=2).encode('utf-8')
        return self.store_upload(case_id, raw_bytes, "audit_certificate.json")
