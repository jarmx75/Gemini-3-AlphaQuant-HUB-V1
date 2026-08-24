"""
First Customer Conversion Experiment Engine (Sprint #25)

Target: First Real External Customer ($49 USD Revenue)
Monitors retained experiment: gotibhai/quant-backtest-platform #18
"""

import json
import logging
import os
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
EXPERIMENT_LOG = LOGS_PORTFOLIO_DIR / "first_customer_conversion_experiment.json"
ANALYTICS_LOG = LOGS_PORTFOLIO_DIR / "landing_analytics.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class CustomerConversionExperimentEngine:
    """
    Monitors single retained acquisition experiment, classifies human intent,
    and tracks first-party landing analytics & conversion pipeline.
    """

    def __init__(self):
        self.env_file = PROJECT_ROOT / ".env"
        self._load_env()
        self.github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    def _load_env(self):
        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'").strip('"')

    def check_retained_issue_replies(self) -> Dict[str, Any]:
        """Polls retained GitHub issue gotibhai/quant-backtest-platform #18 for human replies."""
        if not self.github_token:
            return {"human_replies_count": 0, "replies": []}

        issue_url = "https://api.github.com/repos/gotibhai/quant-backtest-platform/issues/18/comments"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "User-Agent": "AutomatonQuantAudit/1.0",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            req = urllib.request.Request(issue_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                comments = json.loads(resp.read().decode())
                human_replies = []
                for c in comments:
                    user = c.get("user", {}).get("login")
                    if user != "jarmx75":
                        human_replies.append({
                            "user": user,
                            "body": c.get("body", ""),
                            "url": c.get("html_url"),
                            "created_at": c.get("created_at")
                        })
                return {
                    "total_comments": len(comments),
                    "human_replies_count": len(human_replies),
                    "replies": human_replies
                }
        except Exception as e:
            logger.warning(f"Error checking retained issue: {e}")
            return {"human_replies_count": 0, "replies": []}

    def classify_human_intent(self, text: str) -> str:
        """Classifies human reply intent into HOT, WARM, NURTURE, or NO_ACTION."""
        t = text.lower()
        if "how to audit" in t or "where to upload" in t or "how much" in t or "verify my backtest" in t:
            return "HOT"
        elif "overfitting" in t or "pbo" in t or "friction" in t or "lookahead" in t or "sharpe" in t:
            return "WARM"
        elif "thanks" in t or "good point" in t or "interesting" in t:
            return "NURTURE"
        return "NO_ACTION"

    def read_landing_analytics(self) -> Dict[str, int]:
        """Reads first-party analytics event counts."""
        summary = {
            "PAGE_VIEW": 0,
            "QUIZ_STARTED": 0,
            "QUIZ_COMPLETED": 0,
            "EMAIL_CAPTURED": 0,
            "CHECKOUT_CLICK": 0,
            "PAYMENT_CONFIRMED": 0
        }

        if ANALYTICS_LOG.exists():
            try:
                with open(ANALYTICS_LOG, "r", encoding="utf-8") as f:
                    events = json.load(f)
                    for e in events:
                        evt_type = e.get("event_type")
                        if evt_type in summary:
                            summary[evt_type] += 1
            except Exception:
                pass

        return summary

    def run_conversion_experiment(self) -> Dict[str, Any]:
        """Executes monitoring, intent classification, analytics tracking, and experiment reporting."""
        timestamp = datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()

        # Check retained discussion
        poll_res = self.check_retained_issue_replies()
        human_replies = poll_res.get("human_replies_count", 0)
        human_interest = "NONE"

        if human_replies > 0:
            for r in poll_res.get("replies", []):
                intent = self.classify_human_intent(r["body"])
                if intent in ["HOT", "WARM"]:
                    human_interest = intent
                    break

        analytics = self.read_landing_analytics()

        experiment_data = {
            "experiment_id": "EXP_GH_GOTIBHAI_18_V1",
            "timestamp": timestamp,
            "source_channel": "GitHub Discussions",
            "source_url": "https://github.com/gotibhai/quant-backtest-platform/issues/18",
            "publication_id": "5399292251",
            "human_replies": human_replies,
            "human_interest": human_interest,
            "landing_visits": analytics["PAGE_VIEW"],
            "quiz_starts": analytics["QUIZ_STARTED"],
            "emails": analytics["EMAIL_CAPTURED"],
            "checkout_starts": analytics["CHECKOUT_CLICK"],
            "payments": analytics["PAYMENT_CONFIRMED"],
            "revenue_usd": 0.0,
            "audit_completed": 0,
            "certificate_delivered": 0,
            "customer_feedback": "Awaiting first organic response on retained GitHub issue",
            "failure_reason": "NO_HUMAN_REPLY_YET (Organic audience exposure in progress)",
            "next_action": "Monitorear diariamente respuestas en gotibhai/quant-backtest-platform #18 y tráfico en landing",
            "FIRST_REAL_INTEREST": human_replies > 0,
            "FIRST_REVENUE_ACHIEVED": False
        }

        with open(EXPERIMENT_LOG, "w", encoding="utf-8") as f:
            json.dump(experiment_data, f, indent=2)

        return experiment_data


def main():
    engine = CustomerConversionExperimentEngine()
    exp = engine.run_conversion_experiment()
    print("=== FIRST CUSTOMER CONVERSION EXPERIMENT REPORT ===")
    print(json.dumps(exp, indent=2))


if __name__ == "__main__":
    main()
