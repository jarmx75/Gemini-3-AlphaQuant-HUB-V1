"""
Landing Analytics Vercel Serverless Endpoint (Sprint #32.3)

POST /api/analytics
Accepts landing events (PAGE_VISIT, QUIZ_START, EMAIL_SUBMIT, CHECKOUT_CLICK, PAYMENT_RETURN, UPLOAD_SUBMIT)
Appends events to logs/portfolio/landing_analytics.jsonl
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
ANALYTICS_JSONL = LOGS_PORTFOLIO_DIR / "landing_analytics.jsonl"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EVENT_TYPES = {
    "PAGE_VISIT",
    "QUIZ_START",
    "EMAIL_SUBMIT",
    "CHECKOUT_CLICK",
    "PAYMENT_RETURN",
    "UPLOAD_SUBMIT"
}


def process_analytics_event(body_dict: dict) -> dict:
    """Processes, validates, and appends landing analytics event."""
    raw_event_type = body_dict.get("event_type", "").upper()
    if raw_event_type not in ALLOWED_EVENT_TYPES:
        return {"status": "error", "message": f"Invalid event_type: {raw_event_type}"}

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    environment = body_dict.get("environment", "REAL").upper()
    if environment not in {"REAL", "TEST", "SANDBOX"}:
        environment = "REAL"

    event_entry = {
        "event_id": event_id,
        "timestamp_utc": now_iso,
        "environment": environment,
        "session_id": body_dict.get("session_id", f"sess_{uuid.uuid4().hex[:8]}"),
        "event_type": raw_event_type,
        "source": body_dict.get("source", "landing_direct"),
        "referrer": body_dict.get("referrer", "direct"),
        "user_agent_hash": body_dict.get("user_agent_hash", "anon")
    }

    try:
        with open(ANALYTICS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to landing_analytics.jsonl: {e}")
        return {"status": "error", "message": "Failed to persist analytics event"}

    return {"status": "success", "event_id": event_id, "recorded_at": now_iso}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            body_dict = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

            res = process_analytics_event(body_dict)
            status_code = 200 if res.get("status") == "success" else 400

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
