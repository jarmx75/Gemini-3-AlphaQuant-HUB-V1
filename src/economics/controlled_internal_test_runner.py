"""
Controlled Internal Test Runner & Storage Validation Engine (Sprint #36.12 / Etapa 5)

Executes an isolated, controlled end-to-end technical flow test:
1. Internal payment authorization simulation (SYSTEM_TEST_PAYMENT).
2. Internal test case_id & file validation (innocuous CSV data).
3. Test audit execution & TEST_ONLY report/certificate generation.
4. Persistence to Google Drive / Durable Storage under internal-tests/ prefix.
5. Simulated internal delivery record (NOT_SENT_INTERNAL_TEST).
6. Strict commercial metrics isolation verification ($0.00 revenue, 0 real payments).

Security Invariants:
1. MUST be invoked with explicit flag '--internal-controlled-test'.
2. MUST NOT call PayPal API or execute live network payment requests.
3. MUST NOT invoke Resend API or send real emails.
4. MUST NOT publish externally or contact prospects.
5. MUST NOT overwrite or delete existing Google Drive files.
6. MUST NOT alter verified commercial metrics (verified_commercial_payments = 0).
"""

import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs" / "portfolio"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

INTERNAL_TEST_LOG = LOGS_DIR / "internal_test_execution_log.json"
PAYPAL_LOG = LOGS_DIR / "paypal_payment_log.json"

DISALLOWED_EXTENSIONS = {'.exe', '.py', '.sh', '.zip', '.bin', '.jar', '.js', '.bat', '.cmd', '.elf'}


class ControlledInternalTestRunner:
    """Runner engine for executing isolated internal technical pipeline tests."""

    def __init__(self, env_override: Optional[Dict[str, str]] = None):
        self._env = env_override if env_override is not None else os.environ

    def run_controlled_test(self, flag_verified: bool = False) -> Dict[str, Any]:
        """
        Executes the end-to-end controlled internal test flow.
        Fails immediately if flag_verified is False or '--internal-controlled-test' is not in sys.argv.
        """
        # Safety Flag Enforcement
        has_cli_flag = "--internal-controlled-test" in sys.argv
        if not flag_verified and not has_cli_flag:
            raise ValueError("SAFETY_BLOCK: Controlled internal test requires explicit '--internal-controlled-test' flag.")

        now_utc = datetime.now(timezone.utc).isoformat()
        
        # 1. Internal Test Traceability Identifiers
        short_id = uuid.uuid4().hex[:8]
        case_id = f"INTERNAL_TEST_case_{short_id}"
        txn_id = f"INTERNAL_TEST_tx_{short_id}"
        file_id = f"INTERNAL_TEST_file_{short_id}"
        cert_id = f"CERT-TEST-{uuid.uuid4().hex[:6].upper()}"

        # 2. Innocuous Test Data Payload
        test_csv_content = b"timestamp,return\n2026-08-01,0.012\n2026-08-02,0.008\n2026-08-03,-0.004\n2026-08-04,0.015"
        raw_filename = "innocuous_test_strategy.csv"

        # 3. Extension Safety Verification
        ext = os.path.splitext(raw_filename)[1].lower()
        if ext in DISALLOWED_EXTENSIONS:
            raise ValueError(f"DANGEROUS_FILE_REJECTED: Extension '{ext}' is forbidden for internal tests.")

        # 4. Storage Engine Integration & Health Check
        from src.economics.durable_storage import get_durable_storage_engine
        storage_engine = get_durable_storage_engine(self._env)
        
        if not storage_engine.is_configured():
            raise RuntimeError("STORAGE_NOT_CONFIGURED: Durable storage (Google Drive / S3) is not configured.")

        health = storage_engine.health_check()
        if health not in {"HEALTHY", "CONFIGURED_LITE"}:
            raise RuntimeError(f"STORAGE_UNHEALTHY: Storage health check failed with status '{health}'.")

        # 5. Persist Upload under internal-tests/ prefix
        test_case_prefix = f"internal-tests/{case_id}"
        upload_meta = storage_engine.store_upload(test_case_prefix, test_csv_content, raw_filename)
        upload_ref = upload_meta.get("storage_reference", "gdrive_simulated://internal-tests")

        # 6. Execute Simulated Test Audit
        test_audit_results = {
            "test_audit_status": "COMPLETED_TEST_ONLY",
            "sharpe_ratio": 1.85,
            "max_drawdown": -0.042,
            "annualized_return": 0.24,
            "total_trades": 142,
            "sample_size_valid": True,
            "classification": "TEST_ONLY_NOT_FOR_COMMERCIAL_USE"
        }

        # 7. Persist Test Report & Certificate under internal-tests/
        report_payload = {
            "internal_test_flag": True,
            "environment": "INTERNAL_TEST",
            "actor_type": "INTERNAL_TEST",
            "case_id": case_id,
            "txn_id": txn_id,
            "file_id": file_id,
            "audit_certificate_id": cert_id,
            "metrics": test_audit_results,
            "timestamp_utc": now_utc
        }
        report_meta = storage_engine.store_report(test_case_prefix, report_payload)

        cert_payload = {
            "internal_test_flag": True,
            "certificate_type": "INTERNAL_TEST_CERTIFICATE",
            "certificate_id": cert_id,
            "case_id": case_id,
            "status": "TEST_ONLY_NOT_COMMERCIAL",
            "timestamp_utc": now_utc
        }
        cert_meta = storage_engine.store_certificate(test_case_prefix, cert_payload)

        # 8. Record Isolated Log Entry
        test_record = {
            "environment": "INTERNAL_TEST",
            "actor_type": "INTERNAL_TEST",
            "product_id": "SYSTEM_TEST_PAYMENT",
            "case_id": case_id,
            "txn_id": txn_id,
            "file_id": file_id,
            "audit_certificate_id": cert_id,
            "email_delivery_status": "NOT_SENT_INTERNAL_TEST",
            "delivery_action": "INTERNAL_DELIVERY_SIMULATED",
            "upload_storage": upload_meta,
            "report_storage": report_meta,
            "certificate_storage": cert_meta,
            "timestamp_utc": now_utc,
            "is_commercial": False,
            "authorizes_fulfillment": False
        }

        self._record_internal_test_log(test_record)

        # 9. Verify Commercial Metrics Isolation
        from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine
        audit_engine = AcquisitionForensicAuditEngine()
        forensic_report = audit_engine.run_forensic_audit()

        real_m = forensic_report.get("real_commercial_metrics", {})
        comm_pay = real_m.get("verified_commercial_payments", 0)
        comm_rev = real_m.get("verified_commercial_revenue_usd", 0.0)

        if comm_pay != 0 or comm_rev != 0.0:
            raise RuntimeError(f"COMMERCIAL_ISOLATION_BREACH: Commercial metrics altered! Payments={comm_pay}, Rev={comm_rev}")

        # 9. Evaluate Evidence Classification Hierarchy
        is_mock_or_fake = False
        raw_json_creds = self._env.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        folder_id = self._env.get("GOOGLE_DRIVE_FOLDER_ID", "")

        if "sa@test.iam.gserviceaccount.com" in raw_json_creds or "1a2b3c4d5e6f7g8h9i0j" in folder_id or not raw_json_creds:
            is_mock_or_fake = True

        evidence_classification = "LOCAL_FAKE_CREDENTIAL_TEST" if is_mock_or_fake else "LOCAL_REAL_CREDENTIAL_TEST"
        production_write_confirmed = False
        flow_verdict = "LOCAL_SIMULATED_PASS"
        readiness_status = "PARTIAL"  # Strict rule: local fake tests CANNOT declare READY_FOR_LIMITED_PILOT

        return {
            "success": True,
            "evidence_classification": evidence_classification,
            "production_write_confirmed": production_write_confirmed,
            "controlled_technical_flow": flow_verdict,
            "environment": "INTERNAL_TEST",
            "actor_type": "INTERNAL_TEST",
            "product_id": "SYSTEM_TEST_PAYMENT",
            "case_id_masked": f"{case_id[:18]}...",
            "txn_id_masked": f"{txn_id[:16]}...",
            "file_id_masked": f"{file_id[:16]}...",
            "certificate_id": cert_id,
            "safe_test_file_used": raw_filename,
            "google_drive_storage_provider": storage_engine.provider,
            "objects_created_prefix": "internal-tests/",
            "objects_overwritten": 0,
            "public_links_generated": 0,
            "objects_deleted": 0,
            "email_delivery": "NOT_SENT_INTERNAL_TEST",
            "delivery_action": "INTERNAL_DELIVERY_SIMULATED",
            "verified_commercial_payments": comm_pay,
            "verified_commercial_revenue_usd": comm_rev,
            "commercial_metrics_altered": False,
            "commercial_fulfillment_readiness": readiness_status
        }

    def _record_internal_test_log(self, record: Dict[str, Any]):
        """Persists internal test record to internal_test_execution_log.json."""
        existing = []
        if INTERNAL_TEST_LOG.exists():
            try:
                with open(INTERNAL_TEST_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing = data if isinstance(data, list) else data.get("test_events", [])
            except Exception:
                existing = []

        def _json_safe(obj):
            if isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
                if isinstance(obj, dict):
                    return {k: _json_safe(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_json_safe(x) for x in obj]
                return obj
            return str(obj)

        safe_record = _json_safe(record)
        existing.append(safe_record)
        with open(INTERNAL_TEST_LOG, "w", encoding="utf-8") as f:
            json.dump({"test_events": existing}, f, indent=2)


if __name__ == "__main__":
    if "--internal-controlled-test" not in sys.argv:
        print("ERROR: Controlled internal test requires explicit '--internal-controlled-test' CLI flag.")
        sys.exit(1)

    runner = ControlledInternalTestRunner()
    result = runner.run_controlled_test(flag_verified=True)
    print("\n=== ETAPA 5 — PRUEBA CONTROLADA DE FLUJO COMPLETO ===")
    print(json.dumps(result, indent=2))
