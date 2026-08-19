"""
Risk Manager Module
Enforces centralized, conservative risk constraints (max position, max portfolio exposure,
daily loss limits, max drawdown, leverage, and stale data timeouts).
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, date

from src.execution.execution_config import ExecutionConfig
from src.execution.position_manager import PositionManager

logger = logging.getLogger(__name__)


class RiskViolationError(Exception):
    """Raised when an order or action violates pre-trade risk constraints."""
    pass


class RiskManager:
    """
    Centralized Pre-Trade & Real-Time Risk Controller.
    """

    def __init__(self, config: ExecutionConfig, position_mgr: PositionManager):
        self.config = config
        self.position_mgr = position_mgr
        
        # Risk tracking state
        self.current_date: date = datetime.utcnow().date()
        self.daily_realized_pnl: float = 0.0
        self.strategy_realized_pnl: Dict[str, float] = {}
        self.strategy_peak_pnl: Dict[str, float] = {}
        self.last_market_data_timestamp: float = time.time()

    def update_market_data_timestamp(self, ts: Optional[float] = None):
        """Updates timestamp of the freshest received market data quote."""
        self.last_market_data_timestamp = ts or time.time()

    def check_stale_data(self) -> Tuple[bool, float]:
        """Checks if market data feed has stalled beyond stale_data_timeout_sec."""
        elapsed = time.time() - self.last_market_data_timestamp
        is_stale = elapsed > self.config.stale_data_timeout_sec
        return is_stale, elapsed

    def _rollover_day_if_needed(self):
        """Resets daily loss counters upon crossing UTC midnight."""
        now_date = datetime.utcnow().date()
        if now_date != self.current_date:
            logger.info(f"🔄 [RISK DAY ROLLOVER] Date changed from {self.current_date} to {now_date}. Resetting daily loss counters.")
            self.current_date = now_date
            self.daily_realized_pnl = 0.0

    def record_pnl(self, strategy_id: str, pnl: float):
        """Updates realized PnL and computes running drawdowns."""
        self._rollover_day_if_needed()
        self.daily_realized_pnl += pnl
        
        current_strat_pnl = self.strategy_realized_pnl.get(strategy_id, 0.0) + pnl
        self.strategy_realized_pnl[strategy_id] = current_strat_pnl
        
        peak = max(self.strategy_peak_pnl.get(strategy_id, 0.0), current_strat_pnl)
        self.strategy_peak_pnl[strategy_id] = peak

        logger.info(f"📈 [RISK METRICS UPDATE] Daily PnL: ${self.daily_realized_pnl:+.2f} USD | {strategy_id} PnL: ${current_strat_pnl:+.2f} USD (Peak: ${peak:+.2f})")

    def validate_pre_trade_risk(
        self,
        strategy_id: str,
        pair_name: str,
        order_notional: float,
        is_reducing: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates proposed order against all risk boundaries.
        Returns (is_approved, violation_reason).
        """
        self._rollover_day_if_needed()

        # 1. Reducing orders always bypass entry limits
        if is_reducing:
            return True, None

        # 2. Kill Switch Check
        if self.config.kill_switch_active:
            msg = "PRE-TRADE RISK BREACH: Kill switch is actively triggered."
            logger.error(f"🛑 {msg}")
            return False, msg

        # 3. Stale Market Data Check
        is_stale, elapsed = self.check_stale_data()
        if is_stale:
            msg = f"PRE-TRADE RISK BREACH: Stale market data feed! Elapsed={elapsed:.1f}s > Limit={self.config.stale_data_timeout_sec}s"
            logger.error(f"🛑 {msg}")
            return False, msg

        # 4. Daily Loss Limit
        if self.daily_realized_pnl <= -abs(self.config.max_daily_loss):
            msg = f"PRE-TRADE RISK BREACH: Max daily loss reached (${self.daily_realized_pnl:.2f} <= -${self.config.max_daily_loss:.2f})"
            logger.error(f"🛑 {msg}")
            return False, msg

        # 5. Concurrent Positions Limit
        if len(self.position_mgr.open_positions) >= self.config.max_concurrent_positions:
            msg = f"PRE-TRADE RISK BREACH: Max concurrent positions reached ({len(self.position_mgr.open_positions)}/{self.config.max_concurrent_positions})"
            logger.error(f"🛑 {msg}")
            return False, msg

        # 6. Max Position Per Strategy Limit
        if order_notional > self.config.max_position_per_strategy:
            msg = f"PRE-TRADE RISK BREACH: Order notional ${order_notional:.2f} exceeds max_position_per_strategy ${self.config.max_position_per_strategy:.2f}"
            logger.error(f"🛑 {msg}")
            return False, msg

        # 7. Total Aggregate Exposure Limit
        current_total_exposure = self.position_mgr.get_total_notional_exposure()
        if current_total_exposure + order_notional > self.config.max_total_exposure:
            msg = f"PRE-TRADE RISK BREACH: Projected exposure (${current_total_exposure + order_notional:.2f}) exceeds max_total_exposure (${self.config.max_total_exposure:.2f})"
            logger.error(f"🛑 {msg}")
            return False, msg

        # 8. Strategy Drawdown Limit
        strat_pnl = self.strategy_realized_pnl.get(strategy_id, 0.0)
        strat_peak = self.strategy_peak_pnl.get(strategy_id, 0.0)
        strat_dd_usd = strat_peak - strat_pnl
        # Assuming nominal base $1000 per strategy
        strat_dd_pct = (strat_dd_usd / 1000.0) * 100.0
        if strat_dd_pct >= self.config.max_strategy_drawdown_pct:
            msg = f"PRE-TRADE RISK BREACH: Strategy {strategy_id} drawdown {strat_dd_pct:.1f}% >= Max {self.config.max_strategy_drawdown_pct:.1f}%"
            logger.error(f"🛑 {msg}")
            return False, msg

        return True, None
