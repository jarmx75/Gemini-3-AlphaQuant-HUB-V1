"""
Demo Dry-Run / Execution Rehearsal Module
Orchestrates the entire local execution pipeline without network requests:
Signal -> Pre-Trade Risk -> OrderManager -> DryRunBroker -> Fill -> PositionManager -> Reconciliation -> Close -> PnL -> Isolated Logs.

STRICT SECURITY INVARIANTS:
- APPROVED = false
- DEMO_ORDERS = 0
- REAL_ORDERS = 0
- Zero external HTTP network calls.
- Never writes to bitacora_pairs_trading_paper.csv or affects Paper Gate metrics.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.execution.execution_config import ExecutionConfig, ExecutionMode
from src.execution.dry_run_broker import DryRunBroker
from src.execution.order_manager import OrderManager, OrderStatus
from src.execution.position_manager import PositionManager, StrategyPosition
from src.execution.risk_manager import RiskManager
from src.execution.reconciliation import ReconciliationEngine, ReconciliationReport
from src.execution.kill_switch import KillSwitch, KillReason

logger = logging.getLogger(__name__)

DRY_RUN_LOG_DIR = PROJECT_ROOT / "logs" / "execution" / "dry_run"


class DemoDryRunRehearsal:
    """
    Executes an end-to-end dry-run rehearsal of the entire order management and risk stack.
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        initial_balance: float = 5000.0,
        notional_per_leg: float = 150.0
    ):
        self.log_dir = Path(log_dir or DRY_RUN_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.notional_per_leg = notional_per_leg
        self.initial_balance = initial_balance

        # 1. Config (strictly DRY_RUN)
        self.config = ExecutionConfig(
            env=ExecutionMode.DRY_RUN,
            api_key="DRY_RUN_LOCAL_KEY",
            api_secret="DRY_RUN_LOCAL_SECRET",
            real_trading_enabled=False,
            kill_switch_active=False,
            max_position_per_strategy=300.0,
            max_total_exposure=1000.0,
            max_daily_loss=50.0,
            max_strategy_drawdown_pct=10.0,
            max_concurrent_positions=3,
            stale_data_timeout_sec=30.0
        )

        # 2. Local Mock Broker
        self.broker = DryRunBroker(initial_balance_usdt=initial_balance)

        # 3. Execution Managers
        self.order_mgr = OrderManager(client=self.broker, config=self.config)
        self.position_mgr = PositionManager(max_concurrent_positions=3, notional_per_leg=notional_per_leg)
        self.risk_mgr = RiskManager(config=self.config, position_mgr=self.position_mgr)
        self.reconciliation = ReconciliationEngine(
            client=self.broker,
            position_mgr=self.position_mgr,
            order_mgr=self.order_mgr
        )
        self.kill_switch = KillSwitch(
            config=self.config,
            client=self.broker,
            order_mgr=self.order_mgr
        )

    def _append_jsonl(self, filename: str, data: Dict[str, Any]):
        """Writes structured event to dedicated dry-run log file."""
        fpath = self.log_dir / filename
        data_copy = data.copy()
        data_copy["_logged_at"] = datetime.now(timezone.utc).isoformat()
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data_copy) + "\n")

    def execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a paired entry signal through the entire pipeline:
        Signal -> Risk Check -> 2-Leg Orders -> Broker Fill -> Position Open -> Reconciliation.
        """
        strategy_id = signal.get("strategy_id", "Pairs_Stat_Arb_Base")
        pair_name = signal.get("pair", "BTCUSDT/ETHUSDT")
        action = signal.get("action", "")
        gamma = float(signal.get("gamma", 1.0))
        z_score = float(signal.get("z_score", 0.0))
        price_y = float(signal.get("price_y", self.broker.fetch_mark_price("BTCUSDT")))
        price_x = float(signal.get("price_x", self.broker.fetch_mark_price("ETHUSDT")))
        sym_y, sym_x = pair_name.split("/")

        # Determine leg sides based on action
        if action == "OPEN_SHORT_SPREAD":
            side_y, side_x = "SELL", "BUY"
            spread_side = "SHORT_SPREAD"
        elif action == "OPEN_LONG_SPREAD":
            side_y, side_x = "BUY", "SELL"
            spread_side = "LONG_SPREAD"
        else:
            return {"status": "REJECTED", "reason": f"Invalid action: {action}"}

        # Quantity calculations:
        # Leg Y notional = 150.0 -> qty_y = 150 / price_y
        # Leg X quantity = qty_y * gamma -> notional_x = qty_x * price_x
        qty_y = round(self.notional_per_leg / price_y, 6)
        qty_x = round(qty_y * gamma, 6)
        notional_y = qty_y * price_y
        notional_x = qty_x * price_x
        total_notional = notional_y + notional_x

        # 1. Pre-Trade Risk Validation
        is_allowed, risk_reason = self.risk_mgr.validate_pre_trade_risk(
            strategy_id=strategy_id,
            pair_name=pair_name,
            order_notional=total_notional,
            is_reducing=False
        )
        if not is_allowed:
            self._append_jsonl("risk_events.jsonl", {
                "event": "PRE_TRADE_RISK_REJECTED",
                "strategy_id": strategy_id,
                "pair": pair_name,
                "reason": risk_reason
            })
            return {"status": "RISK_REJECTED", "reason": risk_reason}

        # 2. Generate deterministic ClientOrderIDs
        cid_y = self.order_mgr.generate_client_order_id(strategy_id, sym_y, side_y)
        cid_x = self.order_mgr.generate_client_order_id(strategy_id, sym_x, side_x)

        # 3. Submit Leg Y
        order_y = self.order_mgr.submit_order_idempotent(
            strategy_id=strategy_id,
            symbol=sym_y,
            side=side_y,
            quantity=qty_y,
            price=price_y,
            client_order_id=cid_y
        )
        self._append_jsonl("orders.jsonl", {
            "client_order_id": order_y.client_order_id,
            "symbol": sym_y,
            "side": side_y,
            "status": order_y.status.value,
            "executed_qty": order_y.executed_qty
        })

        if order_y.status != OrderStatus.FILLED:
            # Rollback if leg Y fails
            logger.error(f"🛑 [DRY RUN] Leg Y ({sym_y}) failed with status {order_y.status.value}. Aborting spread entry.")
            return {"status": "LEG_Y_FAILED", "order_y": order_y.status.value}

        self._append_jsonl("fills.jsonl", {
            "client_order_id": order_y.client_order_id,
            "symbol": sym_y,
            "qty": order_y.executed_qty,
            "price": order_y.avg_price
        })

        # 4. Submit Leg X
        order_x = self.order_mgr.submit_order_idempotent(
            strategy_id=strategy_id,
            symbol=sym_x,
            side=side_x,
            quantity=qty_x,
            price=price_x,
            client_order_id=cid_x
        )
        self._append_jsonl("orders.jsonl", {
            "client_order_id": order_x.client_order_id,
            "symbol": sym_x,
            "side": side_x,
            "status": order_x.status.value,
            "executed_qty": order_x.executed_qty
        })

        if order_x.status != OrderStatus.FILLED:
            logger.critical(f"🚨 [DRY RUN LEGS MISMATCH] Leg Y filled but Leg X failed ({order_x.status.value}). Triggering emergency rollback.")
            # Emergency close of leg Y
            self.order_mgr.submit_order_idempotent(
                strategy_id=strategy_id,
                symbol=sym_y,
                side="SELL" if side_y == "BUY" else "BUY",
                quantity=qty_y,
                reduce_only=True
            )
            return {"status": "LEG_X_FAILED_ROLLED_BACK", "order_x": order_x.status.value}

        self._append_jsonl("fills.jsonl", {
            "client_order_id": order_x.client_order_id,
            "symbol": sym_x,
            "qty": order_x.executed_qty,
            "price": order_x.avg_price
        })

        # 5. Open Position locally
        pos = self.position_mgr.open_pair_position(
            strategy_id=strategy_id,
            pair_name=pair_name,
            side=spread_side,
            sym_y=sym_y,
            side_y=side_y,
            qty_y=order_y.executed_qty,
            price_y=order_y.avg_price,
            sym_x=sym_x,
            side_x=side_x,
            qty_x=order_x.executed_qty,
            price_x=order_x.avg_price,
            gamma=gamma,
            entry_time_str=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        )
        self._append_jsonl("positions.jsonl", {
            "action": "OPEN",
            "position_id": pos.position_id,
            "pair": pair_name,
            "side": spread_side,
            "gamma": gamma
        })

        # 6. Immediate Reconciliation Audit
        recon_report = self.reconciliation.run_full_reconciliation()
        self._append_jsonl("reconciliation.jsonl", {
            "timestamp": recon_report.timestamp,
            "is_synchronized": recon_report.is_synchronized,
            "halt_required": recon_report.halt_required,
            "mismatches": recon_report.position_mismatches
        })

        if recon_report.halt_required:
            self.kill_switch.trigger(KillReason.POSITION_MISMATCH, details="Mismatched state after entry.")
            self._append_jsonl("kill_switch.jsonl", {
                "reason": "POSITION_MISMATCH",
                "details": recon_report.position_mismatches
            })

        return {
            "status": "SUCCESS",
            "position_id": pos.position_id,
            "pair": pair_name,
            "side": spread_side,
            "leg_y_fill": order_y.executed_qty,
            "leg_x_fill": order_x.executed_qty,
            "reconciliation_ok": recon_report.is_synchronized
        }

    def close_position(
        self,
        pair_name: str,
        exit_price_y: Optional[float] = None,
        exit_price_x: Optional[float] = None,
        reason: str = "Target Mean-Reverted"
    ) -> Dict[str, Any]:
        """
        Executes position exit and PnL calculation:
        Close Signal -> 2-Leg Reducing Orders -> Local Position Close -> PnL Record -> Reconciliation.
        """
        if pair_name not in self.position_mgr.open_positions:
            return {"status": "ERROR", "reason": f"No open position found for {pair_name}"}

        pos = self.position_mgr.open_positions[pair_name]
        sym_y = pos.leg_y.symbol
        sym_x = pos.leg_x.symbol

        p_exit_y = exit_price_y or self.broker.fetch_mark_price(sym_y)
        p_exit_x = exit_price_x or self.broker.fetch_mark_price(sym_x)

        close_side_y = "SELL" if pos.leg_y.side == "BUY" else "BUY"
        close_side_x = "SELL" if pos.leg_x.side == "BUY" else "BUY"

        # Submit reducing orders
        ord_y = self.order_mgr.submit_order_idempotent(
            strategy_id=pos.strategy_id,
            symbol=sym_y,
            side=close_side_y,
            quantity=pos.leg_y.quantity,
            price=p_exit_y,
            reduce_only=True
        )
        ord_x = self.order_mgr.submit_order_idempotent(
            strategy_id=pos.strategy_id,
            symbol=sym_x,
            side=close_side_x,
            quantity=pos.leg_x.quantity,
            price=p_exit_x,
            reduce_only=True
        )

        total_fees = (ord_y.quantity * p_exit_y * 0.0004) + (ord_x.quantity * p_exit_x * 0.0004)

        closed_pos = self.position_mgr.close_pair_position(
            pair_name=pair_name,
            exit_price_y=p_exit_y,
            exit_price_x=p_exit_x,
            close_time_str=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            close_reason=reason,
            fees=total_fees
        )

        if closed_pos:
            self.risk_mgr.record_pnl(closed_pos.strategy_id, closed_pos.realized_pnl)
            self._append_jsonl("positions.jsonl", {
                "action": "CLOSE",
                "position_id": closed_pos.position_id,
                "pair": pair_name,
                "realized_pnl": closed_pos.realized_pnl,
                "reason": reason
            })

        recon_report = self.reconciliation.run_full_reconciliation()
        self._append_jsonl("reconciliation.jsonl", {
            "timestamp": recon_report.timestamp,
            "is_synchronized": recon_report.is_synchronized,
            "halt_required": recon_report.halt_required
        })

        return {
            "status": "SUCCESS",
            "pair": pair_name,
            "realized_pnl": closed_pos.realized_pnl if closed_pos else 0.0,
            "close_reason": reason,
            "reconciliation_ok": recon_report.is_synchronized
        }

    def run_rehearsal_batch(self, signals_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs a complete test batch of rehearsal signals."""
        results = []
        for sig in signals_list:
            res = self.execute_signal(sig)
            results.append(res)

        return {
            "executed_signals": len(signals_list),
            "results": results,
            "open_positions": len(self.position_mgr.open_positions),
            "closed_positions": len(self.position_mgr.closed_positions),
            "broker_balance": self.broker.balance_usdt
        }


if __name__ == '__main__':
    rehearsal = DemoDryRunRehearsal()
    test_signal = {
        "strategy_id": "Pairs_Stat_Arb_Base",
        "pair": "BTCUSDT/ETHUSDT",
        "action": "OPEN_SHORT_SPREAD",
        "gamma": 20.0,
        "z_score": 2.85,
        "price_y": 60000.0,
        "price_x": 3000.0
    }
    open_res = rehearsal.execute_signal(test_signal)
    print("Dry-Run Entry Result:", open_res)

    close_res = rehearsal.close_position("BTCUSDT/ETHUSDT", exit_price_y=59500.0, exit_price_x=3000.0, reason="Target Mean-Reverted")
    print("Dry-Run Close Result:", close_res)
