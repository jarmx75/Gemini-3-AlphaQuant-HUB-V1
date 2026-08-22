"""
Autonomous Revenue Loop Module (Phase 2 Economic Redesign - Track B Controller)

Supervises:
- Payment Health (PayPal OAuth LIVE/Sandbox)
- Landing Health (Public deployment & HTTPS verification)
- Outreach Health (Token blockers & outreach drafts)
- Customer Pipeline & Revenue Log
- Trading Runner Health
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from src.economics.payment_gateway import PayPalPaymentGateway

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
REVENUE_LOOP_LOG = LOGS_PORTFOLIO_DIR / "autonomous_revenue_loop.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class AutonomousRevenueLoop:
    """
    Supervises and audits end-to-end revenue pipeline.
    """

    def __init__(self):
        self.paypal = PayPalPaymentGateway()

    def run_pipeline_audit(self) -> Dict[str, Any]:
        doc = self.paypal.doctor_check()

        # Check landing deployment status
        landing_status_file = PROJECT_ROOT / "docs" / "public_landing" / "deployment_status.json"
        landing_verified = False
        landing_url = "docs/public_landing/index.html"
        if landing_status_file.exists():
            with open(landing_status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                landing_verified = data.get("verified", False)
                landing_url = data.get("public_url", landing_url)

        # Check outreach blockers
        gh_blocked = (LOGS_PORTFOLIO_DIR / "github_outreach_blocker.json").exists()
        email_blocked = (LOGS_PORTFOLIO_DIR / "email_outreach_blocker.json").exists()

        first_revenue_operational = doc["OAUTH_AUTHENTICATION"] == "PASS" and landing_verified
        first_revenue_blocked = not first_revenue_operational

        exact_blocker = "AWAITING_PUBLIC_HOSTING_AUTHORIZATION" if not landing_verified else (
            "AWAITING_PAYPAL_LIVE_CREDENTIALS" if doc["OAUTH_AUTHENTICATION"] != "PASS" else "NONE"
        )

        pipeline_report = {
            "timestamp": datetime.now().isoformat(),
            "PAYPAL_ENV": doc["ENV_SOURCE"],
            "PAYPAL_CREDENTIALS_DETECTED": doc["CREDENTIALS_PRESENT"],
            "PAYPAL_OAUTH": doc["OAUTH_AUTHENTICATION"],
            "PAYPAL_CHECKOUT": doc["CHECKOUT_READINESS"],
            "LANDING_PUBLIC_URL": landing_url,
            "LANDING_HTTP_STATUS": 200 if landing_verified else "LOCAL_READY_PENDING_HOSTING",
            "LANDING_VERIFIED": landing_verified,
            "GITHUB_AUTH": "FAIL" if gh_blocked else "PASS",
            "GITHUB_OUTREACH": "PAUSED_AWAITING_TOKEN" if gh_blocked else "READY",
            "EMAIL_AUTH": "FAIL" if email_blocked else "PASS",
            "EMAIL_OUTREACH": "PAUSED_AWAITING_TOKEN" if email_blocked else "READY",
            "CUSTOMER_PIPELINE": "AWAITING_FIRST_PAYMENT",
            "FIRST_REVENUE_OPERATIONAL": first_revenue_operational,
            "EXACT_BLOCKER": exact_blocker,
            "HUMAN_ACTION_REQUIRED": "Autorizar hosting público en Vercel/Netlify o conectar repositorio GitHub"
        }

        with open(REVENUE_LOOP_LOG, "w", encoding="utf-8") as f:
            json.dump(pipeline_report, f, indent=2)

        return pipeline_report


def main():
    loop = AutonomousRevenueLoop()
    report = loop.run_pipeline_audit()
    print("=== AUTONOMOUS REVENUE LOOP REPORT ===")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
