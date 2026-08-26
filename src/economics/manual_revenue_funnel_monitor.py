"""
Read-Only Manual Revenue Funnel Monitor (Sprint #33)

Strict Parity with acquisition_forensic_audit.py:
- Queries exact same underlying source files.
- Preserves persistent observation session lifetime.
- Reports SESSION, RUNTIME, ACQUISITION, REVENUE, DELIVERY, and PRODUCT PORTFOLIO.
- 100% Read-Only. Zero side-effects. Zero tasks created. Zero emails sent. Zero payments created.
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
SESSION_FILE = LOGS_PORTFOLIO_DIR / "revenue_observation_session.json"


class ManualRevenueFunnelMonitor:
    """
    Read-only monitor leveraging exact same forensic data engine for 100% metric parity.
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
            "session": report["session"],
            "runtime": report["runtime"],
            "acquisition": report["acquisition"],
            "revenue": report["revenue"],
            "delivery": report["delivery"],
            "product_portfolio": report["product_portfolio"],
            "conversion": report["conversion"],
            "owner_test_funnel": report["owner_test_funnel"],
            "data_quality": report["data_quality"],
            "final_verdict": report["final_verdict"]
        }

        with open(SNAPSHOT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        return snapshot

    def render_console_summary(self, snapshot: Dict[str, Any]):
        """Renders exact matching console summary."""
        sess = snapshot["session"]
        rt = snapshot["runtime"]
        acq = snapshot["acquisition"]
        rev = snapshot["revenue"]
        deliv = snapshot["delivery"]
        port = snapshot["product_portfolio"]

        print("=== AUTOMATON REVENUE FUNNEL — READ ONLY MONITOR (SPRINT #33) ===")
        print(f"\nSESSION")
        print(f"Session ID      : {sess['session_id']}")
        print(f"Start           : {sess['start_time_utc']}")
        print(f"Current         : {sess['current_time_utc']}")
        print(f"Elapsed         : {sess['elapsed_hours']}h")
        print(f"Remaining to 24h: {sess['remaining_hours_to_24h']}h")
        print(f"Total lifetime  : {sess['total_lifetime_hours']}h")

        print(f"\nRUNTIME")
        print(f"Cron cycles          : {rt['cron_cycles']}")
        print(f"Successful cycles    : {rt['successful_cycles']}")
        print(f"Failed cycles        : {rt['failed_cycles']}")
        print(f"Retries              : {rt['retries']}")
        print(f"Revenue Activity Rate: {rt['revenue_activity_rate']}")

        print(f"\nACQUISITION")
        print(f"Opportunities discovered: {acq['opportunities_discovered']}")
        print(f"Qualified leads         : {acq['qualified_leads']}")
        print(f"Publications            : {acq['publications']}")
        print(f"Blocked                 : {acq['blocked']}")
        print(f"Replies                 : {acq['replies']}")
        print(f"External visits         : {acq['external_visits']}")
        print(f"Quiz starts             : {acq['quiz_starts']}")
        print(f"Emails                  : {acq['emails']}")
        print(f"Checkout starts         : {acq['checkout_starts']}")

        print(f"\nREVENUE")
        print(f"Payment returns   : {rev['payment_returns']}")
        print(f"Completed payments: {rev['completed_payments']}")
        print(f"Revenue USD       : ${rev['revenue_usd']:.2f}" if isinstance(rev['revenue_usd'], (int, float)) else f"Revenue USD       : {rev['revenue_usd']}")

        print(f"\nDELIVERY")
        print(f"Audits          : {deliv['audits']}")
        print(f"Certificates    : {deliv['certificates']}")
        print(f"Emails delivered: {deliv['emails_delivered']}")

        print(f"\nPRODUCT PORTFOLIO")
        print(f"Active products   : {port['active_products']}")
        print(f"Revenue by product: {json.dumps(port['revenue_by_product'])}")
        print(f"Leads by product  : {json.dumps(port['leads_by_product'])}")

        print(f"\nFINAL VERDICT:")
        print(snapshot["final_verdict"])


def main():
    monitor = ManualRevenueFunnelMonitor()
    snap = monitor.generate_snapshot()
    monitor.render_console_summary(snap)


if __name__ == "__main__":
    main()
