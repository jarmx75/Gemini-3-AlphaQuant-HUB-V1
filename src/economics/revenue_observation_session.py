"""
Persistent Revenue Observation Session Manager (Sprint #33)

Features:
- Maintains logs/portfolio/revenue_observation_session.json
- First run initializes session_id and start_time_utc
- Subsequent runs preserve start_time_utc (never overwrites start_time)
- Resets session ONLY if force_new_session=True or --new-session is explicitly passed
- Calculates elapsed_hours, remaining_hours_to_24h, and total_lifetime_hours
"""

import json
import logging
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
SESSION_FILE = LOGS_PORTFOLIO_DIR / "revenue_observation_session.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)


class RevenueObservationSession:
    """
    Manages persistent 24-hour observation session metadata.
    """

    def __init__(self, force_new_session: bool = False):
        self.session_file = SESSION_FILE
        if "--new-session" in sys.argv:
            force_new_session = True
        self._ensure_session(force_new_session=force_new_session)

    def _ensure_session(self, force_new_session: bool = False) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        if self.session_file.exists() and not force_new_session:
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "start_time_utc" in data and "session_id" in data:
                    return data
            except Exception as e:
                logger.warning(f"Error reading session file, re-initializing: {e}")

        new_session = {
            "session_id": f"sess_{now_utc.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
            "start_time_utc": now_iso,
            "created_at_utc": now_iso,
            "observation_goal_hours": 24.0
        }

        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(new_session, f, indent=2)

        return new_session

    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        session_mgr = RevenueObservationSession()
        return session_mgr.get_session_data()

    def get_session_data(self) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception:
            raw_data = self._ensure_session(force_new_session=True)

        start_iso = raw_data.get("start_time_utc", now_iso)
        try:
            start_dt = datetime.fromisoformat(start_iso)
            elapsed = round((now_utc - start_dt).total_seconds() / 3600.0, 4)
        except Exception:
            start_iso = now_iso
            elapsed = 0.0

        remaining = max(0.0, round(24.0 - elapsed, 4)) if isinstance(elapsed, (int, float)) else "UNKNOWN"

        return {
            "session_id": raw_data.get("session_id", "sess_unknown"),
            "start_time_utc": start_iso,
            "current_time_utc": now_iso,
            "elapsed_hours": elapsed,
            "remaining_hours_to_24h": remaining,
            "total_lifetime_hours": elapsed
        }


def main():
    force_new = "--new-session" in sys.argv
    session = RevenueObservationSession(force_new_session=force_new)
    info = session.get_session_data()
    print("=== REVENUE OBSERVATION SESSION ===")
    print(f"Session ID: {info['session_id']}")
    print(f"Start UTC : {info['start_time_utc']}")
    print(f"Current   : {info['current_time_utc']}")
    print(f"Elapsed   : {info['elapsed_hours']}h")
    print(f"Remaining : {info['remaining_hours_to_24h']}h")


if __name__ == "__main__":
    main()
