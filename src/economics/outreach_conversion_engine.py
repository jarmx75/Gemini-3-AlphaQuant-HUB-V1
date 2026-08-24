"""
Outreach Conversion & Funnel Engine (Sprint #23)

State Machine:
DISCOVERED -> QUALIFIED -> CONTENT_GENERATED -> SUBMITTED -> PUBLISHED -> ENGAGED -> CLICKED -> LANDING_VISIT -> QUIZ_STARTED -> EMAIL_CAPTURED -> CHECKOUT_STARTED -> PAID -> AUDIT_STARTED -> AUDIT_COMPLETED -> CERTIFICATE_DELIVERED

Expected Revenue = P(PAYMENT | LEAD) * qualified_leads * $49 USD
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
FUNNEL_FILE = LOGS_PORTFOLIO_DIR / "customer_conversion_funnel.json"
ANALYTICS_FILE = LOGS_PORTFOLIO_DIR / "landing_analytics.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class OutreachConversionEngine:
    """
    Tracks lead conversion state machine, generates contextual educational contributions,
    and calculates empirical funnel metrics.
    """

    def __init__(self):
        self._init_funnel()

    def _init_funnel(self):
        if not FUNNEL_FILE.exists():
            initial_funnel = {
                "timestamp": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
                "leads": [],
                "conversion_summary": {
                    "DISCOVERED": 0,
                    "QUALIFIED": 0,
                    "CONTENT_GENERATED": 0,
                    "SUBMITTED": 0,
                    "PUBLISHED": 0,
                    "ENGAGED": 0,
                    "CLICKED": 0,
                    "LANDING_VISIT": 0,
                    "QUIZ_STARTED": 0,
                    "EMAIL_CAPTURED": 0,
                    "CHECKOUT_STARTED": 0,
                    "PAID": 0,
                    "AUDIT_COMPLETED": 0,
                    "CERTIFICATE_DELIVERED": 0
                },
                "FIRST_REVENUE_ACHIEVED": False
            }
            with open(FUNNEL_FILE, "w", encoding="utf-8") as f:
                json.dump(initial_funnel, f, indent=2)

    def load_funnel(self) -> Dict[str, Any]:
        if FUNNEL_FILE.exists():
            try:
                with open(FUNNEL_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def register_lead_state(self, lead_id: str, source: str, title: str, status: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Registers or advances a lead in the conversion state machine."""
        funnel = self.load_funnel()
        timestamp = datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()

        existing_lead = None
        for l in funnel.get("leads", []):
            if l["lead_id"] == lead_id:
                existing_lead = l
                break

        if not existing_lead:
            existing_lead = {
                "lead_id": lead_id,
                "source": source,
                "title": title,
                "status": status,
                "history": [],
                "created_at": timestamp,
                "updated_at": timestamp,
                "evidence": evidence
            }
            funnel["leads"].append(existing_lead)
        else:
            existing_lead["status"] = status
            existing_lead["updated_at"] = timestamp
            existing_lead["evidence"].update(evidence)

        existing_lead["history"].append({
            "status": status,
            "timestamp": timestamp,
            "evidence": evidence
        })

        # Recalculate summary
        summary = {st: 0 for st in [
            "DISCOVERED", "QUALIFIED", "CONTENT_GENERATED", "SUBMITTED", "PUBLISHED",
            "ENGAGED", "CLICKED", "LANDING_VISIT", "QUIZ_STARTED", "EMAIL_CAPTURED",
            "CHECKOUT_STARTED", "PAID", "AUDIT_COMPLETED", "CERTIFICATE_DELIVERED"
        ]}

        for l in funnel.get("leads", []):
            st = l.get("status")
            if st in summary:
                summary[st] += 1

        funnel["conversion_summary"] = summary

        with open(FUNNEL_FILE, "w", encoding="utf-8") as f:
            json.dump(funnel, f, indent=2)

        return existing_lead

    def prepare_contextual_contribution(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Prepares a technical contribution tailored to a specific lead's query."""
        source = lead.get("source", "r/algotrading")
        title = lead.get("title", "")

        contribution = {
            "lead_id": lead.get("lead_id"),
            "channel": source,
            "status": "DRAFT",
            "timestamp": datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
            "headline": f"Technical Analysis: {title[:60]}...",
            "body": """
Interesting quantitative question. One critical aspect worth verifying before committing real capital to a high Sharpe backtest is whether the return distribution survives:

1. Timestamp Alignment Check: Ensuring signals on bar t strictly execute on bar t+1 open.
2. Friction Stress Testing: Deducting institutional spread & fee schedules (16 bps roundtrip for crypto futures, 9 bps for equities).
3. Probability of Backtest Overfitting (PBO): Applying 1,000-block bootstrap resampling to evaluate out-of-sample drawdown decay.

We built an independent quantitative audit workflow for this exact evaluation:
https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/
            """.strip(),
            "landing_url": "https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/",
            "price": "$49 USD"
        }

        # Advance state to CONTENT_GENERATED
        self.register_lead_state(
            lead_id=lead.get("lead_id"),
            source=source,
            title=title,
            status="CONTENT_GENERATED",
            evidence={"draft_contribution": contribution}
        )

        return contribution

    def calculate_expected_revenue(self) -> Dict[str, Any]:
        """Calculates Expected Revenue = P(PAYMENT | LEAD) * qualified_leads * $49 USD."""
        funnel = self.load_funnel()
        summary = funnel.get("conversion_summary", {})

        qualified_leads = summary.get("QUALIFIED", 0) + summary.get("CONTENT_GENERATED", 0)
        paid_count = summary.get("PAID", 0)

        # Baseline empirical probability or 2.5% conservative model
        p_payment_given_lead = (paid_count / qualified_leads) if qualified_leads > 0 and paid_count > 0 else 0.025
        expected_revenue = p_payment_given_lead * qualified_leads * 49.0

        return {
            "qualified_leads": qualified_leads,
            "p_payment_given_lead": round(p_payment_given_lead, 4),
            "expected_revenue_usd": round(expected_revenue, 2),
            "actual_revenue_usd": paid_count * 49.0,
            "FIRST_REVENUE_ACHIEVED": paid_count > 0
        }


def main():
    engine = OutreachConversionEngine()

    # Process qualified leads from acquisition pool
    leads = [
        {"lead_id": "lead_reddit_quant_01", "source": "r/algotrading", "title": "My StatArb strategy has 2.4 Sharpe over 3 years, how do I know if it's overfitted?"},
        {"lead_id": "lead_github_issue_02", "source": "GitHub Discussions (backtrader)", "title": "Looking for independent 3rd party backtest audit tools before live trading"},
        {"lead_id": "lead_quantconnect_03", "source": "QuantConnect Forum", "title": "Difference between backtest Sharpe vs live execution friction"}
    ]

    for ld in leads:
        engine.register_lead_state(ld["lead_id"], ld["source"], ld["title"], "QUALIFIED", {"score": 90})
        engine.prepare_contextual_contribution(ld)

    revenue_stats = engine.calculate_expected_revenue()
    print("=== OUTREACH CONVERSION ENGINE REPORT ===")
    print(json.dumps(revenue_stats, indent=2))


if __name__ == "__main__":
    main()
