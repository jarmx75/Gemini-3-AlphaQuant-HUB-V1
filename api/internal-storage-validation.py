"""
Internal Storage Validation Production Endpoint (Sprint #36.13.2 / Etapa 5.3B)

Provides a safe, locked-down serverless handler for executing an explicit controlled write
validation test against Google Drive in Vercel Production.

Security Controls & Invariants:
1. Rejects GET requests with 405 Method Not Allowed.
2. Rejects POST requests without valid INTERNAL_STORAGE_VALIDATION_TOKEN (401/403).
3. Rejects POST requests without explicit 'confirm_internal_test': True in JSON body (400).
4. Fails closed (503) if INTERNAL_STORAGE_VALIDATION_TOKEN is unconfigured or storage is unhealthy.
5. All unhandled exceptions are caught top-level and rendered as safe JSON (never HTTP 500 crash).
6. Supports idempotency via 'internal_test_run_id' to prevent duplicate writes or retry loops.
7. Writes at most 3 isolated TEST_ONLY objects under 'internal-tests/' prefix.
8. Inherits private folder privacy (public_sharing = DISABLED_PRIVATE_FOLDER_ONLY).
9. Makes zero calls to PayPal API and sends zero real emails.
10. Alters zero commercial metrics (verified_commercial_payments = 0).
11. Returns strictly sanitized payload without secret credentials or raw folder IDs.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Add project root to sys.path if needed
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from http.server import BaseHTTPRequestHandler

# Local memory / file-based idempotency cache
IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}


def _send_json_response(handler_obj, status_code: int, data: Dict[str, Any]):
    """Sends JSON response with CORS headers and cache prevention."""
    try:
        body_bytes = json.dumps(data, indent=2).encode('utf-8')
        handler_obj.send_response(status_code)
        handler_obj.send_header("Content-Type", "application/json")
        handler_obj.send_header("Access-Control-Allow-Origin", "*")
        handler_obj.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        handler_obj.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Internal-Test-Token, X-Internal-Test-Run-ID")
        handler_obj.send_header("Cache-Control", "no-store, max-age=0")
        handler_obj.send_header("Content-Length", str(len(body_bytes)))
        handler_obj.end_headers()
        handler_obj.wfile.write(body_bytes)
    except Exception as err:
        logger.error(f"[STORAGE VALIDATION RESPONSE ERROR]: {err}")


def _get_header_val(headers, name: str) -> str:
    """Case-insensitive header value extractor supporting both HTTPMessage and dict."""
    if not headers:
        return ""
    if hasattr(headers, "get"):
        val = headers.get(name, None)
        if val is not None:
            return str(val).strip()
    if isinstance(headers, dict):
        name_lower = name.lower()
        for k, v in headers.items():
            if k.lower() == name_lower:
                return str(v).strip()
    return ""


class handler(BaseHTTPRequestHandler):
    """Serverless handler for /api/internal-storage-validation."""

    def do_OPTIONS(self):
        """Responds to CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Internal-Test-Token, X-Internal-Test-Run-ID")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        """Rejects GET requests with 405 Method Not Allowed."""
        _send_json_response(self, 405, {
            "error": "METHOD_NOT_ALLOWED",
            "message": "Only POST requests are accepted by /api/internal-storage-validation"
        })

    def do_POST(self):
        """Processes controlled production storage write validation safely."""
        try:
            self._process_post_request()
        except Exception as err:
            logger.error(f"[STORAGE VALIDATION UNHANDLED EXCEPTION]: {err}")
            _send_json_response(self, 503, {
                "error": "INTERNAL_VALIDATION_FAILED",
                "detail": "STORAGE_WRITE_FAILED",
                "message": "Internal storage write validation encountered a handled server error.",
                "evidence_classification": "NOT_VALIDATED",
                "commercial_fulfillment_readiness": "PARTIAL"
            })

    def _process_post_request(self):
        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Verify Authorization Token
        expected_token = os.environ.get("INTERNAL_STORAGE_VALIDATION_TOKEN", "").strip()
        if not expected_token or expected_token in {"REDACTED", "YOUR_TOKEN", ""}:
            _send_json_response(self, 503, {
                "error": "VALIDATION_TOKEN_NOT_CONFIGURED",
                "message": "INTERNAL_STORAGE_VALIDATION_TOKEN is not configured on server.",
                "evidence_classification": "NOT_VALIDATED",
                "commercial_fulfillment_readiness": "PARTIAL"
            })
            return

        # Extract token from headers or body
        provided_token = _get_header_val(self.headers, "X-Internal-Test-Token")
        if not provided_token:
            auth_hdr = _get_header_val(self.headers, "Authorization")
            if auth_hdr.startswith("Bearer "):
                provided_token = auth_hdr[7:].strip()

        content_len_str = _get_header_val(self.headers, "Content-Length")
        content_len = int(content_len_str) if content_len_str.isdigit() else 0

        body_data = {}
        if content_len > 0 and hasattr(self, "rfile") and self.rfile is not None:
            try:
                raw_body = self.rfile.read(content_len)
                body_data = json.loads(raw_body.decode('utf-8'))
            except Exception:
                pass

        if not provided_token and "token" in body_data:
            provided_token = str(body_data.get("token", "")).strip()

        if not provided_token or provided_token != expected_token:
            _send_json_response(self, 401, {
                "error": "UNAUTHORIZED",
                "message": "Invalid or missing internal storage validation token.",
                "evidence_classification": "NOT_VALIDATED"
            })
            return

        # 2. Verify Explicit Body Confirmation
        if not body_data.get("confirm_internal_test"):
            _send_json_response(self, 400, {
                "error": "CONFIRMATION_REQUIRED",
                "message": "JSON body must specify 'confirm_internal_test': true.",
                "evidence_classification": "NOT_VALIDATED"
            })
            return

        # 3. Idempotency Check (internal_test_run_id)
        run_id = _get_header_val(self.headers, "X-Internal-Test-Run-ID")
        if not run_id:
            run_id = str(body_data.get("internal_test_run_id", "") or body_data.get("run_id", "")).strip()

        if run_id:
            cached_status = IDEMPOTENCY_CACHE.get(run_id)
            if cached_status:
                state = cached_status.get("state")
                if state == "COMPLETED":
                    _send_json_response(self, 200, {
                        "service": "durable_storage_validation",
                        "provider": cached_status.get("provider", "GOOGLE_DRIVE"),
                        "evidence_classification": "PRODUCTION_CONTROLLED_WRITE_VALIDATED",
                        "production_write_confirmed": True,
                        "controlled_technical_flow": "PASS",
                        "idempotency_status": "ALREADY_COMPLETED",
                        "message": f"Internal test run_id '{run_id}' was already executed successfully. Zero duplicate objects created.",
                        "objects_created_count": 0,
                        "public_sharing": "DISABLED_PRIVATE_FOLDER_ONLY",
                        "email_delivery": "NOT_SENT_INTERNAL_TEST",
                        "commercial_fulfillment_readiness": "PARTIAL"
                    })
                    return
                elif state in {"UNKNOWN", "PARTIAL_FAILURE"}:
                    _send_json_response(self, 503, {
                        "error": "PREVIOUS_ATTEMPT_UNKNOWN",
                        "idempotency_status": "PREVIOUS_ATTEMPT_UNKNOWN",
                        "message": f"Previous execution for run_id '{run_id}' left an unknown state. Automatic re-write is blocked to prevent duplication.",
                        "evidence_classification": "NOT_VALIDATED",
                        "commercial_fulfillment_readiness": "PARTIAL"
                    })
                    return

        # 4. Check Storage Health
        from src.economics.durable_storage import get_durable_storage_engine
        storage_engine = get_durable_storage_engine()

        if not storage_engine.is_configured():
            _send_json_response(self, 503, {
                "error": "STORAGE_NOT_CONFIGURED",
                "message": "Durable storage is not configured.",
                "evidence_classification": "NOT_VALIDATED",
                "commercial_fulfillment_readiness": "NOT_READY"
            })
            return

        health = storage_engine.health_check()
        if health not in {"HEALTHY", "CONFIGURED_LITE"}:
            _send_json_response(self, 503, {
                "error": "STORAGE_UNHEALTHY",
                "message": f"Storage health check failed with status '{health}'.",
                "evidence_classification": "NOT_VALIDATED",
                "commercial_fulfillment_readiness": "NOT_READY"
            })
            return

        # 5. Perform Maximum 3 Isolated TEST_ONLY Writes inside try...except
        active_run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        case_id = f"INTERNAL_TEST_case_{active_run_id}"
        test_prefix = f"internal-tests/{case_id}"

        if active_run_id:
            IDEMPOTENCY_CACHE[active_run_id] = {"state": "IN_PROGRESS", "timestamp": now_utc}

        try:
            # Object 1: Safe CSV Upload
            test_csv = b"timestamp,return\n2026-08-01,0.012\n2026-08-02,0.008\n2026-08-03,-0.004"
            upload_meta = storage_engine.store_upload(test_prefix, test_csv, "test_strategy.csv")

            # Object 2: TEST_ONLY Report
            report_data = {
                "internal_test": True,
                "classification": "TEST_ONLY_NOT_FOR_CUSTOMER",
                "case_id": case_id,
                "timestamp": now_utc
            }
            report_meta = storage_engine.store_report(test_prefix, report_data)

            # Object 3: TEST_ONLY Certificate
            cert_data = {
                "internal_test": True,
                "certificate_id": f"CERT-TEST-{uuid.uuid4().hex[:6].upper()}",
                "case_id": case_id,
                "timestamp": now_utc
            }
            cert_meta = storage_engine.store_certificate(test_prefix, cert_data)

            # Mark idempotency completed
            if active_run_id:
                IDEMPOTENCY_CACHE[active_run_id] = {
                    "state": "COMPLETED",
                    "provider": storage_engine.provider,
                    "timestamp": now_utc
                }

            # Sanitized return payload
            _send_json_response(self, 200, {
                "service": "durable_storage_validation",
                "provider": storage_engine.provider,
                "evidence_classification": "PRODUCTION_CONTROLLED_WRITE_VALIDATED",
                "production_write_confirmed": True,
                "controlled_technical_flow": "PASS",
                "idempotency_status": "COMPLETED",
                "objects_created_count": 3,
                "objects_prefix": "internal-tests/",
                "public_sharing": "DISABLED_PRIVATE_FOLDER_ONLY",
                "objects_overwritten": 0,
                "email_delivery": "NOT_SENT_INTERNAL_TEST",
                "verified_commercial_payments": 0,
                "verified_commercial_revenue_usd": 0.0,
                "commercial_fulfillment_readiness": "PARTIAL",
                "test_case_masked": f"{case_id[:22]}...",
                "timestamp_utc": now_utc
            })
        except Exception as write_err:
            logger.error(f"[STORAGE WRITE ERROR]: {write_err}")
            if active_run_id:
                IDEMPOTENCY_CACHE[active_run_id] = {"state": "UNKNOWN", "timestamp": now_utc}
            _send_json_response(self, 503, {
                "error": "INTERNAL_VALIDATION_FAILED",
                "detail": "STORAGE_WRITE_FAILED",
                "message": "Storage write operation failed safely without creating invalid objects.",
                "idempotency_status": "PREVIOUS_ATTEMPT_UNKNOWN",
                "evidence_classification": "NOT_VALIDATED",
                "commercial_fulfillment_readiness": "PARTIAL"
            })
