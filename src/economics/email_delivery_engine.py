"""
Email Delivery Engine (Sprint #17 Phase 8)

Handles transactional email events:
- PAYMENT_CONFIRMED
- DATA_RECEIVED
- AUDIT_STARTED
- AUDIT_COMPLETED
- CERTIFICATE_GENERATED
- CERTIFICATE_DELIVERED
"""

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
EMAIL_DELIVERY_LOG = LOGS_PORTFOLIO_DIR / "email_delivery.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class EmailDeliveryEngine:
    """
    Transactional email delivery engine with fallback logger for customer audit reports.
    """

    def __init__(self):
        self.provider = os.getenv("EMAIL_PROVIDER", "RESEND_SMTP_LOGGER")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.resend.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "resend")
        self.smtp_pass = os.getenv("SMTP_PASSWORD", "")

    def send_event_notification(self, event_type: str, recipient: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sends or logs a transactional email event."""
        timestamp = datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()
        
        subject_map = {
            "PAYMENT_CONFIRMED": "Payment Confirmed: Automaton Quant Audit ($49 USD)",
            "DATA_RECEIVED": "Strategy Data Received: Audit Processing Started",
            "AUDIT_STARTED": "Quant Audit Engine Execution Initiated",
            "AUDIT_COMPLETED": "Quant Audit Engine Execution Completed",
            "CERTIFICATE_GENERATED": "Your Quant Audit Certificate Has Been Generated",
            "CERTIFICATE_DELIVERED": "Automaton Quant Audit Certificate Delivery"
        }

        subject = subject_map.get(event_type, f"Automaton Audit Alert: {event_type}")

        body = f"""
Automaton Quant Audit Transactional Alert
-----------------------------------------
Event: {event_type}
Timestamp: {timestamp}
Recipient: {recipient}
Details:
{json.dumps(data, indent=2)}

MODELLED / NOT GUARANTEED
Automaton Quantitative Autonomous Systems
        """

        sent_status = "LOGGED_LOCAL"

        if self.smtp_pass and len(self.smtp_pass) > 5:
            try:
                msg = MIMEMultipart()
                msg['From'] = 'audits@automatonquant.com'
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
                    sent_status = "SENT_SMTP_LIVE"
            except Exception as e:
                logger.warning(f"SMTP send failed, falling back to audit log: {e}")
                sent_status = f"FALLBACK_LOGGED ({e})"

        record = {
            "event_type": event_type,
            "recipient": recipient,
            "subject": subject,
            "status": sent_status,
            "timestamp": timestamp,
            "payload": data
        }

        # Log delivery
        existing = []
        if EMAIL_DELIVERY_LOG.exists():
            try:
                with open(EMAIL_DELIVERY_LOG, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        existing.append(record)
        with open(EMAIL_DELIVERY_LOG, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        return record


def main():
    engine = EmailDeliveryEngine()
    res = engine.send_event_notification("PAYMENT_CONFIRMED", "test_buyer@quant.com", {"order_id": "TEST_ORDER_99", "amount": "49.00 USD"})
    print("=== EMAIL DELIVERY ENGINE RECORD ===")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
