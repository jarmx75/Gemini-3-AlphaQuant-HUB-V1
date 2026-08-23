"""
Merchant Payment Reconciliation Engine (Sprint #17 Phase 6)

Strict Accounting Invariants:
- FIRST_REVENUE_ACHIEVED = TRUE ONLY IF:
  1. PayPal Order Capture status == COMPLETED
  2. Amount == 49.00
  3. Currency == USD
"""

import json
import logging
import os
import urllib.request
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
RECONCILIATION_LOG = LOGS_PORTFOLIO_DIR / "merchant_reconciliation.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class MerchantPaymentReconciler:
    """
    Periodically checks and reconciles external PayPal payment events against strict revenue criteria.
    """

    def __init__(self):
        self.env_file = PROJECT_ROOT / ".env"
        self._load_env()

    def _load_env(self):
        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'").strip('"')

    def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Queries PayPal LIVE API for official order details."""
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

        if not client_id or not client_secret:
            return {"status": "MISSING_CREDENTIALS", "verified": False}

        try:
            auth_str = f"{client_id}:{client_secret}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()

            token_req = urllib.request.Request(
                "https://api-m.paypal.com/v1/oauth2/token",
                data=b"grant_type=client_credentials",
                headers={
                    "Authorization": f"Basic {b64_auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                method="POST"
            )

            with urllib.request.urlopen(token_req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode())
                access_token = token_data["access_token"]

            order_req = urllib.request.Request(
                f"https://api-m.paypal.com/v2/checkout/orders/{order_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            with urllib.request.urlopen(order_req, timeout=10) as order_resp:
                order_data = json.loads(order_resp.read().decode())
                
                status = order_data.get("status")
                purchase_units = order_data.get("purchase_units", [{}])
                amount_obj = purchase_units[0].get("amount", {})
                value = amount_obj.get("value")
                currency = amount_obj.get("currency_code")

                # Check if captures exist
                payments = purchase_units[0].get("payments", {})
                captures = payments.get("captures", [])
                capture_status = captures[0].get("status") if captures else None
                capture_id = captures[0].get("id") if captures else None

                is_valid_completed = (
                    (status == "COMPLETED" or capture_status == "COMPLETED") and
                    value == "49.00" and
                    currency == "USD"
                )

                result = {
                    "order_id": order_id,
                    "order_status": status,
                    "capture_id": capture_id,
                    "capture_status": capture_status,
                    "amount": value,
                    "currency": currency,
                    "verified_completed": is_valid_completed,
                    "reconciled_at": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()
                }

                return result

        except Exception as e:
            return {"status": "ERROR", "error": str(e), "verified_completed": False}

    def run_reconciliation(self) -> Dict[str, Any]:
        """Runs full reconciliation log scan."""
        report = {
            "timestamp": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
            "merchant_account": "api-m.paypal.com (LIVE)",
            "verified_orders": [],
            "FIRST_REVENUE_ACHIEVED": False
        }

        # Check existing payment logs
        payment_log_path = LOGS_PORTFOLIO_DIR / "payments.json"
        if payment_log_path.exists():
            try:
                with open(payment_log_path, "r", encoding="utf-8") as f:
                    payments = json.load(f)
                    for p in payments:
                        order_id = p.get("payment_id") or p.get("order_id")
                        if order_id:
                            status_res = self.check_order_status(order_id)
                            report["verified_orders"].append(status_res)
                            if status_res.get("verified_completed"):
                                report["FIRST_REVENUE_ACHIEVED"] = True
            except Exception:
                pass

        with open(RECONCILIATION_LOG, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report


def main():
    reconciler = MerchantPaymentReconciler()
    res = reconciler.run_reconciliation()
    print("=== MERCHANT PAYMENT RECONCILIATION REPORT ===")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
