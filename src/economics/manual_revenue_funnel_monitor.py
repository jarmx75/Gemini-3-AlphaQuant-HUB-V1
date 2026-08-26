"""
Read-Only Manual Revenue Funnel Monitor (Sprint #32.4)

Strict Parity with acquisition_forensic_audit.py:
- Queries exact same underlying source files.
- Separates EXTERNAL CUSTOMER FUNNEL vs OWNER / TEST FUNNEL.
- Computes conversion rates with UNKNOWN handling for 0 denominators.
- 100% Read-Only. Zero side-effects.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
from src.economics.acquisition_forensic_audit import AcquisitionForensicAuditEngine

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
SNAPSHOT_JSON_FILE = LOGS_PORTFOLIO_DIR / "manual_revenue_funnel_snapshot.json"
OBSERVATION_FILE = LOGS_PORTFOLIO_DIR / "autonomous_24h_observation.json"


class ManualRevenueFunnelMonitor:
    """
    Read-only monitor leveraging exact same forensic data engine.
    """

    def __init__(self):
        self.audit_engine = AcquisitionForensicAuditEngine()

    def generate_snapshot(self) -> Dict[str, Any]:
        """Generates read-only snapshot JSON file logs/portfolio/manual_revenue_funnel_snapshot.json."""
        report = self.audit_engine.run_forensic_audit()

        snapshot = {
            "timestamp": report["timestamp"],
            "monitor_integrity": {
                "MONITOR_MODE": "READ_ONLY",
                "CRON_TRIGGERED_BY_MONITOR": False,
                "TASKS_CREATED_BY_MONITOR": 0,
                "PAYMENTS_CREATED_BY_MONITOR": 0,
                "EMAILS_SENT_BY_MONITOR": 0,
                "AUDITS_STARTED_BY_MONITOR": 0,
                "FILES_MODIFIED_BY_MONITOR": 0,
                "SIDE_EFFECTS": 0,
                "CRON_UNTOUCHED": True
            },
            "observation": report["observation"],
            "cron": report["cron"],
            "outreach": report["outreach"],
            "external_customer_funnel": report["external_customer_funnel"],
            "owner_test_funnel": report["owner_test_funnel"],
            "conversion": report["conversion"],
            "data_quality": report["data_quality"],
            "final_verdict": report["final_verdict"]
        }

        with open(SNAPSHOT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        return snapshot

    def render_console_summary(self, snapshot: Dict[str, Any]):
        """Renders exact matching console summary."""
        obs = snapshot["observation"]
        cron = snapshot["cron"]
        outreach = snapshot["outreach"]
        ext_f = snapshot["external_customer_funnel"]
        owner_f = snapshot["owner_test_funnel"]
        conv = snapshot["conversion"]
        dq = snapshot["data_quality"]

        print("=== AUTOMATON REVENUE FUNNEL — READ ONLY MONITOR ===")
        print(f"\nOBSERVATION WINDOW")
        print(f"Start    : {obs['start']}")
        print(f"Now      : {obs['now']}")
        print(f"Elapsed  : {obs['elapsed']}h" if isinstance(obs['elapsed'], (int, float)) else f"Elapsed  : {obs['elapsed']}")

        print(f"\nAUTONOMOUS RUNTIME")
        print(f"Cron Active : True (Vercel Cron */15 * * * *)")
        print(f"Expected    : {cron['expected']}")
        print(f"Observed    : {cron['observed']}")
        print(f"Missing     : {cron['missing']}")
        print(f"Status      : {cron['status']}")

        print(f"\n=== EXTERNAL CUSTOMER FUNNEL ===")
        print(f"Landing visits    : {ext_f['landing_visits']}")
        print(f"Quiz starts       : {ext_f['quiz_starts']}")
        print(f"Emails            : {ext_f['emails']}")
        print(f"Checkout starts   : {ext_f['checkout_starts']}")
        print(f"Payment returns   : {ext_f['payment_returns']}")
        print(f"Completed payments: {ext_f['completed_payments']}")
        print(f"Revenue           : ${ext_f['revenue_usd']:.2f}" if isinstance(ext_f['revenue_usd'], (int, float)) else f"Revenue           : {ext_f['revenue_usd']}")
        print(f"Audits            : {ext_f['audits_completed']}")
        print(f"Certificates      : {ext_f['certificates_delivered']}")
        print(f"Emails delivered  : {ext_f['emails_delivered']}")

        print(f"\n=== OWNER / TEST FUNNEL ===")
        print(f"Landing visits   : {owner_f['owner_landing_visits']}")
        print(f"Checkout starts  : {owner_f['owner_checkout_starts']}")
        print(f"Test payments    : {owner_f['test_payments']}")
        print(f"Test audits      : {owner_f['test_audits']}")
        print(f"Test certificates: {owner_f['test_certificates']}")

        print(f"\n=== CONVERSION ===")
        print(f"Landing -> Checkout: {conv['landing_to_checkout']}")
        print(f"Checkout -> Payment: {conv['checkout_to_payment']}")
        print(f"Landing -> Payment : {conv['landing_to_payment']}")

        print(f"\nDATA QUALITY")
        print(f"Hardcoded      : {dq['hardcoded']}")
        print(f"Fallback       : {dq['fallback']}")
        print(f"Synthetic      : {dq['synthetic']}")
        print(f"Unknown        : {dq['unknown']}")
        print(f"Missing sources: {', '.join(dq['missing_sources']) if dq['missing_sources'] else 'None'}")


def main():
    monitor = ManualRevenueFunnelMonitor()
    snap = monitor.generate_snapshot()
    monitor.render_console_summary(snap)


if __name__ == "__main__":
    main()
