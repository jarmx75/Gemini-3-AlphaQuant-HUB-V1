"""
Local Dry-Run Broker Module
High-fidelity local exchange simulator for Binance Futures dry-run execution rehearsal.
Supports order submission, partial fills, cancellations, position tracking, fees, slippage,
latency, idempotency, and explicit failure injection (timeouts, rejections, position mismatches).

STRICT SECURITY INVARIANT:
- Absolutely ZERO external network calls or HTTP requests.
- Runs 100% in-memory.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from src.execution.binance_client import BinanceClientError

logger = logging.getLogger(__name__)


class DryRunBroker:
    """
    Local simulation broker mimicking Binance UM Futures API behavior.
    """

    def __init__(
        self,
        initial_balance_usdt: float = 5000.0,
        taker_fee_rate: float = 0.0004,  # 0.04%
        maker_fee_rate: float = 0.0002,  # 0.02%
        default_slippage_bps: float = 1.0,  # 1 bp default
        simulated_latency_ms: float = 15.0
    ):
        self.initial_balance = initial_balance_usdt
        self.balance_usdt = initial_balance_usdt
        self.taker_fee_rate = taker_fee_rate
        self.maker_fee_rate = maker_fee_rate
        self.default_slippage_bps = default_slippage_bps
        self.simulated_latency_ms = simulated_latency_ms

        # In-memory broker state
        self.orders: Dict[str, Dict[str, Any]] = {}  # Indexed by client_order_id
        self.orders_by_id: Dict[int, Dict[str, Any]] = {}  # Indexed by exchange orderId
        self.open_positions: Dict[str, Dict[str, Any]] = {}  # symbol -> position dict
        self.fills_log: List[Dict[str, Any]] = []

        # Mark prices for simulation
        self.mark_prices: Dict[str, float] = {
            "BTCUSDT": 60000.0,
            "ETHUSDT": 3000.0,
            "AVAXUSDT": 30.0,
            "SOLUSDT": 150.0,
            "LINKUSDT": 15.0,
            "DOTUSDT": 5.0
        }

        # Failure injection flags
        self.force_timeout: bool = False
        self.force_rejection: bool = False
        self.force_partial_fill: bool = False
        self.partial_fill_ratio: float = 0.5
        self.order_counter: int = 100000

    def update_mark_price(self, symbol: str, price: float):
        """Sets simulated mark price for a symbol."""
        self.mark_prices[symbol] = price

    def set_mark_prices(self, prices: Dict[str, float]):
        """Sets multiple mark prices."""
        self.mark_prices.update(prices)

    # ==================== Failure Injection Hooks ====================

    def inject_timeout(self, enable: bool = True):
        """Simulates API network timeouts on order operations."""
        self.force_timeout = enable
        logger.info(f"🧪 [FAILURE INJECTION] Timeout injection set to: {enable}")

    def inject_rejection(self, enable: bool = True):
        """Simulates exchange order rejection."""
        self.force_rejection = enable
        logger.info(f"🧪 [FAILURE INJECTION] Rejection injection set to: {enable}")

    def inject_partial_fill(self, enable: bool = True, ratio: float = 0.5):
        """Simulates partial fill on subsequent orders."""
        self.force_partial_fill = enable
        self.partial_fill_ratio = ratio
        logger.info(f"🧪 [FAILURE INJECTION] Partial fill set to: {enable} (ratio={ratio})")

    def inject_position_mismatch(self, symbol: str, corrupt_qty: float):
        """Directly alters broker position to trigger reconciliation failure."""
        if symbol not in self.open_positions:
            self.open_positions[symbol] = {
                "symbol": symbol,
                "positionAmt": corrupt_qty,
                "entryPrice": self.mark_prices.get(symbol, 100.0),
                "unrealizedProfit": 0.0,
                "leverage": 10
            }
        else:
            self.open_positions[symbol]["positionAmt"] += corrupt_qty
        logger.warning(f"🧪 [FAILURE INJECTION] Injected position mismatch on {symbol}: new broker amt={self.open_positions[symbol]['positionAmt']}")

    def inject_unexpected_fill(self, symbol: str, quantity: float, price: Optional[float] = None):
        """Injects an unrequested fill on the broker."""
        p = price or self.mark_prices.get(symbol, 100.0)
        self.open_positions[symbol] = {
            "symbol": symbol,
            "positionAmt": quantity,
            "entryPrice": p,
            "unrealizedProfit": 0.0,
            "leverage": 10
        }
        logger.warning(f"🧪 [FAILURE INJECTION] Injected unexpected fill: {quantity} {symbol} @ {p}")

    def reset_injections(self):
        """Clears all failure injection controls."""
        self.force_timeout = False
        self.force_rejection = False
        self.force_partial_fill = False
        self.partial_fill_ratio = 0.5
        logger.info("🧪 [FAILURE INJECTION] All fault injections reset to normal.")

    # ==================== Binance Client Mock Interface ====================

    def ping(self) -> bool:
        return True

    def get_server_time(self) -> int:
        return int(time.time() * 1000)

    def fetch_mark_price(self, symbol: str) -> float:
        return self.mark_prices.get(symbol, 100.0)

    def get_account_balance(self) -> List[Dict[str, Any]]:
        return [{
            "asset": "USDT",
            "balance": f"{self.balance_usdt:.2f}",
            "availableBalance": f"{self.balance_usdt:.2f}"
        }]

    def get_positions(self) -> List[Dict[str, Any]]:
        """Returns list of active broker positions."""
        result = []
        for sym, pos in self.open_positions.items():
            amt = float(pos.get("positionAmt", 0.0))
            if abs(amt) > 1e-6:
                result.append({
                    "symbol": sym,
                    "positionAmt": f"{amt:.6f}",
                    "entryPrice": f"{pos.get('entryPrice', 0.0):.4f}",
                    "unRealizedProfit": f"{pos.get('unrealizedProfit', 0.0):.4f}",
                    "leverage": str(pos.get("leverage", 10))
                })
        return result

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of open/pending orders."""
        active_statuses = {"PENDING", "SUBMITTED", "PARTIALLY_FILLED"}
        orders = [
            o for o in self.orders.values()
            if o["status"] in active_statuses and (symbol is None or o["symbol"] == symbol)
        ]
        return orders

    def get_order_status(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches status of a specific order."""
        if client_order_id and client_order_id in self.orders:
            return self.orders[client_order_id]
        if order_id and order_id in self.orders_by_id:
            return self.orders_by_id[order_id]
        raise BinanceClientError(f"Order not found on dry-run broker (clientOrderId={client_order_id}, orderId={order_id})")

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: float = 0.0,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Simulates idempotent order execution with fees, slippage, and latency.
        """
        # 1. Fault Injection: Timeout
        if self.force_timeout:
            logger.error("🛑 [SIMULATED TIMEOUT] DryRunBroker dropped request.")
            raise BinanceClientError("Simulated API connection timeout (Read timed out).")

        # 2. Fault Injection: Rejection
        if self.force_rejection:
            logger.error(f"🛑 [SIMULATED REJECTION] Order {client_order_id} rejected by exchange.")
            raise BinanceClientError("Order rejected by simulated exchange rules (code -2010).")

        # 3. Idempotency Check: if client_order_id already exists, return existing order without duplicating
        if client_order_id and client_order_id in self.orders:
            existing = self.orders[client_order_id]
            logger.warning(f"⚠️ [IDEMPOTENT RETRY] Order {client_order_id} already executed. Returning existing status {existing['status']}.")
            return existing

        self.order_counter += 1
        order_id = self.order_counter
        cid = client_order_id or f"dry_{uuid.uuid4().hex[:12]}"
        side_norm = side.upper()
        base_price = price or self.mark_prices.get(symbol, 100.0)

        # 4. Calculate simulated slippage
        # Buy slippage adds bps, sell slippage subtracts bps
        slip_mult = 1.0 + ((self.default_slippage_bps / 10000.0) * (1.0 if side_norm == "BUY" else -1.0))
        exec_price = round(base_price * slip_mult, 4)

        # 5. Determine execution quantity (full or partial)
        if self.force_partial_fill:
            exec_qty = round(quantity * self.partial_fill_ratio, 6)
            status = "PARTIALLY_FILLED"
        else:
            exec_qty = quantity
            status = "FILLED"

        # 6. Calculate fees
        notional = exec_qty * exec_price
        fee = round(notional * self.taker_fee_rate, 4)
        self.balance_usdt -= fee

        # 7. Update broker position state
        current_pos = self.open_positions.get(symbol, {
            "symbol": symbol,
            "positionAmt": 0.0,
            "entryPrice": exec_price,
            "unrealizedProfit": 0.0,
            "leverage": 10
        })
        signed_qty = exec_qty if side_norm == "BUY" else -exec_qty
        new_amt = round(current_pos["positionAmt"] + signed_qty, 6)

        if abs(new_amt) < 1e-6:
            # Position closed completely
            self.open_positions.pop(symbol, None)
        else:
            # Update weighted entry price if increasing position
            if (current_pos["positionAmt"] >= 0 and signed_qty > 0) or (current_pos["positionAmt"] <= 0 and signed_qty < 0):
                total_qty = abs(current_pos["positionAmt"]) + exec_qty
                avg_entry = ((abs(current_pos["positionAmt"]) * current_pos["entryPrice"]) + (exec_qty * exec_price)) / total_qty
            else:
                avg_entry = current_pos["entryPrice"]

            self.open_positions[symbol] = {
                "symbol": symbol,
                "positionAmt": new_amt,
                "entryPrice": round(avg_entry, 4),
                "unrealizedProfit": 0.0,
                "leverage": 10
            }

        order_record = {
            "symbol": symbol,
            "orderId": order_id,
            "clientOrderId": cid,
            "status": status,
            "cumQty": str(exec_qty),
            "executedQty": str(exec_qty),
            "origQty": str(quantity),
            "avgPrice": str(exec_price),
            "side": side_norm,
            "type": order_type.upper(),
            "fee": fee,
            "latency_ms": self.simulated_latency_ms,
            "timestamp": int(time.time() * 1000)
        }

        self.orders[cid] = order_record
        self.orders_by_id[order_id] = order_record
        self.fills_log.append(order_record)

        logger.info(f"⚡ [DRY-RUN FILL] {side_norm} {exec_qty}/{quantity} {symbol} @ {exec_price} USD (Fee: ${fee:.4f}, Latency: {self.simulated_latency_ms}ms)")
        return order_record

    def cancel_order(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancels an order in dry run broker."""
        target = None
        if client_order_id and client_order_id in self.orders:
            target = self.orders[client_order_id]
        elif order_id and order_id in self.orders_by_id:
            target = self.orders_by_id[order_id]

        if not target:
            raise BinanceClientError(f"Cannot cancel unknown order (clientOrderId={client_order_id}, orderId={order_id})")

        target["status"] = "CANCELED"
        logger.info(f"🛑 [DRY-RUN CANCELED] Order {target['clientOrderId']} marked CANCELED.")
        return {"symbol": symbol, "orderId": target["orderId"], "status": "CANCELED"}

    def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """Cancels all open orders for symbol."""
        count = 0
        for o in self.get_open_orders(symbol):
            o["status"] = "CANCELED"
            count += 1
        return {"code": 200, "msg": f"Canceled {count} orders on {symbol}"}

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        return {"symbol": symbol, "leverage": leverage}

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> Dict[str, Any]:
        return {"symbol": symbol, "marginType": margin_type}
