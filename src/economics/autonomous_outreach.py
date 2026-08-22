"""
Autonomous Outreach Loop Module (Phase 2 Economic Redesign - Track B Outreach Engine)

Calculates RevenueScore:
(fit * pain * reachable * willingness_to_pay * automation) / outreach_cost

Detects API token credentials (GITHUB_TOKEN, RESEND_API_KEY) and logs clean blockers if credentials are missing.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
GITHUB_BLOCKER_FILE = LOGS_PORTFOLIO_DIR / "github_outreach_blocker.json"
EMAIL_BLOCKER_FILE = LOGS_PORTFOLIO_DIR / "email_outreach_blocker.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class AutonomousOutreachEngine:
    """
    Autonomous Outreach Loop Manager.
    """

    def compute_revenue_score(self, prospect: Dict[str, Any]) -> float:
        """
        RevenueScore = (fit * pain * reachable * willingness_to_pay * automation) / outreach_cost
        """
        fit = float(prospect.get("fit", 8.0))
        pain = float(prospect.get("pain", 9.0))
        reachable = float(prospect.get("reachable", 7.0))
        willingness = float(prospect.get("willingness_to_pay", 8.0))
        automation = float(prospect.get("automation", 9.0))
        cost = max(1.0, float(prospect.get("outreach_cost", 1.0)))

        score = (fit * pain * reachable * willingness * automation) / cost
        return round(float(score), 2)

    def check_and_audit_blockers(self) -> Dict[str, Any]:
        gh_token = os.getenv("GITHUB_TOKEN", "").strip()
        email_key = os.getenv("RESEND_API_KEY", "").strip() or os.getenv("SENDGRID_API_KEY", "").strip()

        gh_blocked = len(gh_token) < 10 or gh_token.startswith("your_")
        email_blocked = len(email_key) < 10 or email_key.startswith("your_")

        if gh_blocked:
            with open(GITHUB_BLOCKER_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "credential_missing": "GITHUB_TOKEN",
                    "required_permission": "public_repo / discussions:write",
                    "exact_next_auth_action": "Opcional: Si deseas que Automaton publique automáticamente en GitHub Discussions, agrega GITHUB_TOKEN en config/.env. De lo contrario, DRAFT_02 está listo para publicación manual.",
                    "status": "PAUSED_AWAITING_TOKEN"
                }, f, indent=2)

        if email_blocked:
            with open(EMAIL_BLOCKER_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "credential_missing": "RESEND_API_KEY o SENDGRID_API_KEY",
                    "required_permission": "email:send",
                    "exact_next_auth_action": "Opcional: Si deseas que Automaton envíe emails autónomamente a prospectos, agrega RESEND_API_KEY en config/.env. De lo contrario, DRAFT_01 está listo para envío manual.",
                    "status": "PAUSED_AWAITING_TOKEN"
                }, f, indent=2)

        return {
            "github_outreach_autonomous": not gh_blocked,
            "email_outreach_autonomous": not email_blocked
        }
