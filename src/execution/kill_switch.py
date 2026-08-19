"""
Kill Switch & Circuit Breaker Module
Implements manual and automated emergency halt protocols.
Cancels open orders, blocks new submissions, and preserves telemetry logging.
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.execution.execution_config import ExecutionConfig
from src.execution.binance_client import BinanceFuturesClient
from src.execution.order_manager import OrderManager
from src.execution.reconciliation import ReconciliationReport

logger = logging.getLogger(__name__)


class KillReason(str, Enum):
    MANUAL_TRIGGER = "MANUAL_TRIGGER"
    POSITION_MISMATCH = "POSITION_MISMATCH"
    UNEXPECTED_FILL = "UNEXPECTED_FILL"
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    REPEATED_API_FAILURES = "REPEATED_API_FAILURES"
    DAILY_LOSS_BREACH = "DAILY_LOSS_BREACH"
    STRATEGY_DD_BREACH = "STRATEGY_DD_BREACH"
    TIMESTAMP_DRIFT_ERROR = "TIMESTAMP_DRIFT_ERROR"
    SECURITY_INTEGRITY_BREACH = "SECURITY_INTEGRITY_BREACH"


@dataclass
class KillEvent:
    timestamp: float
    reason: KillReason
    details: str
    orders_canceled: int


class KillSwitch:
    """
    Emergency Circuit Breaker for Automaton Execution.
    """

    def __init__(
        self,
        config: ExecutionConfig,
        client: Optional[BinanceFuturesClient] = None,
        order_mgr: Optional[OrderManager] = None
    ):
        self.config = config
        self.client = client
        self.order_mgr = order_mgr
        self.kill_history: List[KillEvent] = []
        self.active_reason: Optional[KillReason] = None
        self.active_details: Optional[str] = None

    @property
    def is_triggered(self) -> bool:
        return self.config.kill_switch_active

    def trigger(self, reason: KillReason, details: str = "") -> KillEvent:
        """
        Activates Kill Switch:
        1. Sets kill_switch_active = True
        2. Cancels all pending orders across open symbols
        3. Records event for audit
        """
        self.config.kill_switch_active = True
        self.active_reason = reason
        self.active_details = details
        
        canceled_count = 0
        logger.critical(f"🚨🚨🚨 [KILL SWITCH ACTIVATED] Reason: {reason.value} | Details: {details} 🚨🚨🚨")

        # Emergency cancellation of all open orders
        if self.order_mgr:
            open_orders = self.order_mgr.get_open_orders()
            for o in open_orders:
                try:
                    if self.order_mgr.cancel_order(o.client_order_id):
                        canceled_count += 1
                except Exception as e:
                    logger.error(f"Failed to emergency cancel order {o.client_order_id}: {e}")

        event = KillEvent(
            timestamp=time.time(),
            reason=reason,
            details=details,
            orders_canceled=canceled_count
        )
        self.kill_history.append(event)
        return event

    def check_auto_kill_conditions(
        self,
        reconciliation_report: Optional[ReconciliationReport] = None,
        is_data_stale: bool = False,
        consecutive_api_errors: int = 0,
        daily_pnl: float = 0.0,
        max_strat_dd_pct: float = 0.0,
        clock_drift_ms: float = 0.0
    ) -> Optional[KillEvent]:
        """
        Evaluates auto-kill criteria and triggers switch if any breach is observed.
        """
        if self.is_triggered:
            return None

        # 1. Position Mismatch Breach
        if reconciliation_report and reconciliation_report.halt_required:
            details = "; ".join(reconciliation_report.position_mismatches + reconciliation_report.order_mismatches)
            return self.trigger(KillReason.POSITION_MISMATCH, details=f"Reconciliation failure: {details}")

        # 2. Stale Market Data Breach
        if is_data_stale:
            return self.trigger(KillReason.STALE_MARKET_DATA, details="Market data feed exceeded timeout threshold.")

        # 3. Repeated API Failures (>= 3 consecutive)
        if consecutive_api_errors >= 3:
            return self.trigger(KillReason.REPEATED_API_FAILURES, details=f"Exceeded 3 consecutive API failures ({consecutive_api_errors}).")

        # 4. Daily Loss Breach
        if daily_pnl <= -abs(self.config.max_daily_loss):
            return self.trigger(KillReason.DAILY_LOSS_BREACH, details=f"Daily loss ${daily_pnl:.2f} breached limit of -${self.config.max_daily_loss:.2f}")

        # 5. Strategy Drawdown Breach
        if max_strat_dd_pct >= self.config.max_strategy_drawdown_pct:
            return self.trigger(KillReason.STRATEGY_DD_BREACH, details=f"Strategy DD {max_strat_dd_pct:.1f}% breached limit of {self.config.max_strategy_drawdown_pct:.1f}%")

        # 6. Clock Drift Breach (> 1500 ms)
        if abs(clock_drift_ms) > 1500.0:
            return self.trigger(KillReason.TIMESTAMP_DRIFT_ERROR, details=f"Local/Server clock drift of {clock_drift_ms:.1f}ms exceeds 1500ms tolerance.")

        return None

    def reset_manual(self, confirm_token: str) -> bool:
        """Manual reset requires explicit security confirmation token."""
        if confirm_token != "AUTHORIZE_KILL_SWITCH_RESET":
            logger.error("🛑 Kill switch reset failed: Invalid authorization token.")
            return False
        
        self.config.kill_switch_active = False
        self.active_reason = None
        self.active_details = None
        logger.warning("⚠️ [KILL SWITCH RESET] System returned to operational readiness.")
        return True
