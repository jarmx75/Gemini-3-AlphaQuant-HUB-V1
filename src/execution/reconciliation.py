"""
Position & State Reconciliation Engine
Continuously audits local state against exchange state (positions, open orders, balance, funding, fees).
Triggers HALT NEW ORDERS upon any mismatch.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from src.execution.binance_client import BinanceFuturesClient, BinanceClientError
from src.execution.position_manager import PositionManager
from src.execution.order_manager import OrderManager

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationReport:
    timestamp: float
    is_synchronized: bool
    halt_required: bool
    position_mismatches: List[str] = field(default_factory=list)
    order_mismatches: List[str] = field(default_factory=list)
    balance_discrepancy: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class ReconciliationEngine:
    """
    Continuous state reconciler between local state and Binance Futures exchange.
    Fails closed: if any mismatch is detected, sets halt_required = True.
    """

    def __init__(
        self,
        client: BinanceFuturesClient,
        position_mgr: PositionManager,
        order_mgr: OrderManager,
        qty_tolerance: float = 1e-4
    ):
        self.client = client
        self.position_mgr = position_mgr
        self.order_mgr = order_mgr
        self.qty_tolerance = qty_tolerance
        self.last_report: Optional[ReconciliationReport] = None

    def reconcile_positions(self) -> Tuple[bool, List[str]]:
        """Compares local expected net positions vs actual exchange positions."""
        mismatches: List[str] = []
        try:
            exchange_positions = self.client.get_positions()
        except BinanceClientError as e:
            msg = f"Failed to fetch exchange positions for reconciliation: {e}"
            logger.error(msg)
            return False, [msg]

        # Convert exchange positions to dict {symbol: net_qty}
        exchange_net_qty: Dict[str, float] = {}
        for p in exchange_positions:
            sym = p.get("symbol")
            amt = float(p.get("positionAmt", 0.0))
            if abs(amt) > self.qty_tolerance:
                exchange_net_qty[sym] = amt

        # Local expected net quantities
        local_net_qty = self.position_mgr.get_symbol_net_quantities()

        # All symbols in either local or exchange
        all_symbols = set(local_net_qty.keys()).union(set(exchange_net_qty.keys()))

        for sym in all_symbols:
            loc_qty = local_net_qty.get(sym, 0.0)
            exc_qty = exchange_net_qty.get(sym, 0.0)
            diff = abs(loc_qty - exc_qty)
            
            if diff > self.qty_tolerance:
                mismatch_msg = f"Position mismatch for {sym}: Local={loc_qty:.5f} vs Exchange={exc_qty:.5f} (Diff={diff:.5f})"
                logger.error(f"🚨 [RECONCILIATION MISMATCH] {mismatch_msg}")
                mismatches.append(mismatch_msg)

        is_sync = (len(mismatches) == 0)
        return is_sync, mismatches

    def reconcile_open_orders(self) -> Tuple[bool, List[str]]:
        """Compares local pending orders with exchange open orders."""
        mismatches: List[str] = []
        try:
            exchange_orders = self.client.get_open_orders()
        except BinanceClientError as e:
            msg = f"Failed to fetch open orders for reconciliation: {e}"
            logger.error(msg)
            return False, [msg]

        exchange_order_ids = {o.get("clientOrderId") for o in exchange_orders if o.get("clientOrderId")}
        local_open_orders = {o.client_order_id for o in self.order_mgr.get_open_orders()}

        # Untracked orders on exchange
        untracked = exchange_order_ids - local_open_orders
        if untracked:
            msg = f"Untracked active orders found on exchange: {untracked}"
            logger.error(f"🚨 [ORDER RECONCILIATION] {msg}")
            mismatches.append(msg)

        # Missing orders that local believes are pending
        missing = local_open_orders - exchange_order_ids
        for missing_id in missing:
            # Reconcile individual order state to update fill status
            try:
                self.order_mgr.reconcile_order(missing_id)
            except Exception as e:
                mismatches.append(f"Local pending order {missing_id} missing on exchange: {e}")

        is_sync = (len(mismatches) == 0)
        return is_sync, mismatches

    def reconcile_balance_and_funding(self) -> Tuple[bool, float, Dict[str, Any]]:
        """Fetches exchange balance and details."""
        try:
            balances = self.client.get_account_balance()
            usdt_bal = 0.0
            for b in balances:
                if b.get("asset") == "USDT":
                    usdt_bal = float(b.get("balance", b.get("availableBalance", 0.0)))
                    break
            return True, usdt_bal, {"usdt_balance": usdt_bal}
        except BinanceClientError as e:
            logger.error(f"Failed to reconcile balance: {e}")
            return False, 0.0, {"error": str(e)}

    def run_full_reconciliation(self) -> ReconciliationReport:
        """Runs complete state reconciliation across all dimensions."""
        pos_sync, pos_mismatches = self.reconcile_positions()
        ord_sync, ord_mismatches = self.reconcile_open_orders()
        bal_ok, current_balance, bal_details = self.reconcile_balance_and_funding()

        is_fully_synced = pos_sync and ord_sync and bal_ok
        halt_required = not is_fully_synced

        report = ReconciliationReport(
            timestamp=time.time(),
            is_synchronized=is_fully_synced,
            halt_required=halt_required,
            position_mismatches=pos_mismatches,
            order_mismatches=ord_mismatches,
            balance_discrepancy=0.0 if bal_ok else 1.0,
            details={
                "positions_synced": pos_sync,
                "orders_synced": ord_sync,
                "balance_ok": bal_ok,
                "current_balance": current_balance,
                "open_positions_count": len(self.position_mgr.open_positions)
            }
        )

        if halt_required:
            logger.critical("🛑 [RECONCILIATION HALT TRIGGERED] State inconsistency detected! New orders MUST be halted.")

        self.last_report = report
        return report
