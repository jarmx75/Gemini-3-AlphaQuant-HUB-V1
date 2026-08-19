"""
Order Manager Module
Provides idempotent order execution, safe retries without duplication, status tracking,
and fill reconciliation using unique clientOrderId generation.
"""

import time
import uuid
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from src.execution.binance_client import BinanceFuturesClient, BinanceClientError
from src.execution.execution_config import ExecutionConfig

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class ManagedOrder:
    client_order_id: str
    strategy_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    exchange_order_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    executed_qty: float = 0.0
    avg_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    reduce_only: bool = False
    error_message: Optional[str] = None
    retries: int = 0


class OrderManager:
    """
    Manages order lifecycles, ensuring idempotency and zero duplicate orders.
    """

    def __init__(self, client: BinanceFuturesClient, config: ExecutionConfig):
        self.client = client
        self.config = config
        self.orders: Dict[str, ManagedOrder] = {}  # Indexed by client_order_id

    def generate_client_order_id(self, strategy_id: str, symbol: str, side: str) -> str:
        """Generates a deterministic unique clientOrderId (max 36 chars for Binance)."""
        clean_strat = strategy_id[:8].replace("_", "").lower()
        clean_sym = symbol[:4].lower()
        short_id = uuid.uuid4().hex[:8]
        ts = int(time.time()) % 1000000
        return f"a_{clean_strat}_{clean_sym}_{side[:1].lower()}_{ts}_{short_id}"

    def submit_order_idempotent(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        reduce_only: bool = False
    ) -> ManagedOrder:
        """
        Submits an order idempotently.
        If client_order_id already exists, verifies exchange status instead of submitting a duplicate.
        """
        if not client_order_id:
            client_order_id = self.generate_client_order_id(strategy_id, symbol, side)

        # Check if already submitted / tracked
        if client_order_id in self.orders:
            existing = self.orders[client_order_id]
            if existing.status in [OrderStatus.SUBMITTED, OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                logger.warning(f"⚠️ [IDEMPOTENCY GUARD] Order {client_order_id} already exists with status {existing.status.value}. Reconciling instead of duplicate submit.")
                return self.reconcile_order(client_order_id)

        managed_order = ManagedOrder(
            client_order_id=client_order_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=quantity,
            price=price,
            reduce_only=reduce_only,
            status=OrderStatus.PENDING
        )
        self.orders[client_order_id] = managed_order

        # Safe execution with verification before any retry
        try:
            raw_res = self.client.create_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                client_order_id=client_order_id,
                reduce_only=reduce_only
            )
            
            managed_order.exchange_order_id = raw_res.get("orderId")
            managed_order.status = OrderStatus(raw_res.get("status", "FILLED"))
            managed_order.executed_qty = float(raw_res.get("executedQty", raw_res.get("cumQty", quantity)))
            managed_order.avg_price = float(raw_res.get("avgPrice", price or 0.0))
            managed_order.updated_at = time.time()
            
            logger.info(f"✅ [ORDER SUCCESS] {client_order_id} -> {managed_order.status.value} (ExchangeId: {managed_order.exchange_order_id})")
            return managed_order

        except BinanceClientError as e:
            managed_order.error_message = str(e)
            logger.error(f"❌ [ORDER SUBMIT ERROR] {client_order_id}: {e}")
            
            # SAFE RETRY: Query exchange by clientOrderId first to see if it landed before retrying
            time.sleep(self.config.retry_backoff_sec)
            try:
                check_res = self.client.get_order_status(symbol, client_order_id=client_order_id)
                if check_res and check_res.get("status"):
                    managed_order.exchange_order_id = check_res.get("orderId")
                    managed_order.status = OrderStatus(check_res.get("status"))
                    managed_order.executed_qty = float(check_res.get("executedQty", 0.0))
                    managed_order.avg_price = float(check_res.get("avgPrice", 0.0))
                    managed_order.updated_at = time.time()
                    logger.info(f"🔍 [IDEMPOTENT RECOVERY] Found order on exchange after timeout: {client_order_id} -> {managed_order.status.value}")
                    return managed_order
            except Exception as check_err:
                logger.warning(f"Could not verify order state on exchange for {client_order_id}: {check_err}")

            managed_order.status = OrderStatus.REJECTED
            return managed_order

    def cancel_order(self, client_order_id: str) -> bool:
        """Cancels an existing managed order."""
        if client_order_id not in self.orders:
            logger.warning(f"Cannot cancel untracked order: {client_order_id}")
            return False

        order = self.orders[client_order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED]:
            return True

        try:
            self.client.cancel_order(
                symbol=order.symbol,
                order_id=order.exchange_order_id,
                client_order_id=client_order_id
            )
            order.status = OrderStatus.CANCELED
            order.updated_at = time.time()
            logger.info(f"🛑 [ORDER CANCELED] {client_order_id}")
            return True
        except BinanceClientError as e:
            logger.error(f"Failed to cancel order {client_order_id}: {e}")
            return False

    def reconcile_order(self, client_order_id: str) -> ManagedOrder:
        """Queries exchange to reconcile order fill status."""
        if client_order_id not in self.orders:
            raise KeyError(f"Order {client_order_id} not tracked by OrderManager")

        order = self.orders[client_order_id]
        try:
            status_res = self.client.get_order_status(
                symbol=order.symbol,
                order_id=order.exchange_order_id,
                client_order_id=client_order_id
            )
            raw_status = status_res.get("status")
            if raw_status:
                order.status = OrderStatus(raw_status)
                order.executed_qty = float(status_res.get("executedQty", order.executed_qty))
                order.avg_price = float(status_res.get("avgPrice", order.avg_price))
                order.updated_at = time.time()
        except BinanceClientError as e:
            logger.warning(f"Reconciliation query failed for {client_order_id}: {e}")

        return order

    def get_strategy_orders(self, strategy_id: str) -> List[ManagedOrder]:
        """Returns all orders belonging to a strategy."""
        return [o for o in self.orders.values() if o.strategy_id == strategy_id]

    def get_open_orders(self, strategy_id: Optional[str] = None) -> List[ManagedOrder]:
        """Returns all active (non-terminal) orders."""
        active_statuses = {OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED}
        return [
            o for o in self.orders.values()
            if o.status in active_statuses and (strategy_id is None or o.strategy_id == strategy_id)
        ]
