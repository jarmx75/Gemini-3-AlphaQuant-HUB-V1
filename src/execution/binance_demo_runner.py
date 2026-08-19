"""
Binance Futures Demo/Testnet Runner
Unified multi-strategy runner with Paper Gate enforcement, automated state reconciliation,
and integrated Kill Switch protection.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.execution.execution_config import ExecutionConfig, ExecutionMode, load_execution_config_from_env
from src.execution.binance_client import BinanceFuturesClient, BinanceClientError
from src.execution.order_manager import OrderManager
from src.execution.position_manager import PositionManager
from src.execution.reconciliation import ReconciliationEngine
from src.execution.risk_manager import RiskManager
from src.execution.kill_switch import KillSwitch, KillReason
from src.execution.demo_readiness import audit_paper_readiness

logger = logging.getLogger(__name__)


class BinanceDemoRunner:
    """
    Main Orchestrator for Binance Futures Demo Execution.
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or load_execution_config_from_env()
        
        # 1. Enforce fail-closed mode
        if self.config.env not in [ExecutionMode.PAPER, ExecutionMode.DEMO]:
            raise PermissionError(f"CRITICAL SECURITY: BinanceDemoRunner can only run in PAPER or DEMO mode! Got: {self.config.env}")

        self.client = BinanceFuturesClient(self.config)
        self.position_mgr = PositionManager(
            max_concurrent_positions=self.config.max_concurrent_positions,
            notional_per_leg=self.config.max_position_per_strategy / 2.0
        )
        self.order_mgr = OrderManager(self.client, self.config)
        self.reconciliation_engine = ReconciliationEngine(self.client, self.position_mgr, self.order_mgr)
        self.risk_mgr = RiskManager(self.config, self.position_mgr)
        self.kill_switch = KillSwitch(self.config, self.client, self.order_mgr)

        self.consecutive_api_errors = 0
        self.monitored_pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        logger.info("🚀 [BINANCE DEMO RUNNER] Initialized successfully with unified execution engine.")

    def preflight_paper_gate_check(self) -> bool:
        """
        Audits paper trades before allowing live Demo trade dispatching.
        Requires paper_trades >= 100 per strategy.
        """
        audit_rep = audit_paper_readiness()
        if not audit_rep["overall_demo_gate_passed"]:
            logger.warning("🛑 [DEMO PREFLIGHT BLOCKED] Paper Gate is PENDING. No strategy has >= 100 paper trades.")
            return False
        return True

    def run_pulse(self) -> Dict[str, Any]:
        """
        Executes a single monitoring and reconciliation pulse.
        """
        pulse_start = time.time()
        logger.info(f"⚡ [DEMO PULSE START] Mode: {self.config.env.value} | Kill Switch: {self.kill_switch.is_triggered}")

        # 1. Check Paper Gate
        gate_passed = self.preflight_paper_gate_check()
        if not gate_passed:
            return {
                "status": "PAPER_GATE_PENDING",
                "message": "Demo orders blocked: insufficient paper trades (<100).",
                "gate_passed": False
            }

        # 2. Run Full State Reconciliation
        try:
            recon_report = self.reconciliation_engine.run_full_reconciliation()
            self.consecutive_api_errors = 0
        except Exception as e:
            self.consecutive_api_errors += 1
            recon_report = None
            logger.error(f"Reconciliation error (streak: {self.consecutive_api_errors}): {e}")

        # 3. Check Clock Drift
        clock_drift_ms = 0.0
        try:
            server_ts = self.client.get_server_time()
            clock_drift_ms = abs((time.time() * 1000) - server_ts)
        except Exception as e:
            logger.warning(f"Failed to fetch server time: {e}")

        # 4. Check Auto-Kill Conditions
        is_stale, _ = self.risk_mgr.check_stale_data()
        kill_event = self.kill_switch.check_auto_kill_conditions(
            reconciliation_report=recon_report,
            is_data_stale=is_stale,
            consecutive_api_errors=self.consecutive_api_errors,
            daily_pnl=self.risk_mgr.daily_realized_pnl,
            max_strat_dd_pct=0.0,
            clock_drift_ms=clock_drift_ms
        )

        if self.kill_switch.is_triggered:
            return {
                "status": "KILL_SWITCH_ACTIVE",
                "reason": self.kill_switch.active_reason.value if self.kill_switch.active_reason else "UNKNOWN",
                "details": self.kill_switch.active_details
            }

        return {
            "status": "OPERATIONAL",
            "mode": self.config.env.value,
            "reconciliation_synced": recon_report.is_synchronized if recon_report else False,
            "open_positions": len(self.position_mgr.open_positions),
            "clock_drift_ms": round(clock_drift_ms, 2),
            "pulse_duration_sec": round(time.time() - pulse_start, 3)
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    runner = BinanceDemoRunner()
    res = runner.run_pulse()
    print(json.dumps(res, indent=2))
