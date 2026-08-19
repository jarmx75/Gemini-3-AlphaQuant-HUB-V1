"""
Unified Binance Futures Client
Single client for REST/WSS communication supporting PAPER, DEMO (Testnet), and REAL (strictly gated).
Fails closed and scrubs all credentials from logs and exception messages.
"""

import time
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import requests

from src.execution.execution_config import (
    ExecutionConfig,
    ExecutionMode,
    DEMO_REST_URL,
    MAINNET_REST_URL,
    mask_secret,
    sanitize_log_message
)

logger = logging.getLogger(__name__)


class BinanceClientError(Exception):
    """Base exception for Binance Client errors with sanitized messages."""
    pass


class BinanceSecurityBreachError(BinanceClientError):
    """Raised when security boundaries (e.g. mainnet in demo) are violated."""
    pass


class BinanceFuturesClient:
    """
    Centralized Client for Binance UM Futures API.
    Enforces environment isolation and safe parameter execution.
    """

    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._validate_security_invariants()
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Automaton-Trading-Engine/2.0",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        if self.config.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.config.api_key})

        logger.info(f"🌐 BinanceFuturesClient initialized: mode={self.config.env.value}, endpoint={self.config.base_url}, key={mask_secret(self.config.api_key)}")

    def _validate_security_invariants(self):
        """Strict fail-closed safety check."""
        if self.config.env == ExecutionMode.DEMO:
            if "testnet.binancefuture.com" not in self.config.base_url:
                raise BinanceSecurityBreachError(
                    f"CRITICAL: DEMO mode must strictly use testnet endpoint! Found: {self.config.base_url}"
                )
        elif self.config.env == ExecutionMode.REAL:
            if not self.config.real_trading_enabled:
                raise BinanceSecurityBreachError("CRITICAL: REAL mode is not enabled. Execution blocked.")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generates HMAC-SHA256 signature for authenticated requests."""
        if not self.config.api_secret:
            raise BinanceClientError("API secret is missing for authenticated request.")
        query_string = urlencode(params)
        return hmac.new(
            self.config.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Any:
        """Centralized HTTP request handler with retry and timeout."""
        url = f"{self.config.base_url}{endpoint}"
        params = params.copy() if params else {}

        if signed:
            # Rejection in PAPER mode for signed write/account endpoints if unconfigured
            if self.config.env == ExecutionMode.PAPER and not self.config.api_key:
                logger.debug(f"[PAPER] Simulated authenticated call to {endpoint}")
                return {}

            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            params['signature'] = self._generate_signature(params)

        for attempt in range(1, self.config.max_retries + 1):
            try:
                if method.upper() == "GET":
                    resp = self.session.get(url, params=params, timeout=self.config.request_timeout)
                elif method.upper() == "POST":
                    resp = self.session.post(url, data=params, timeout=self.config.request_timeout)
                elif method.upper() == "DELETE":
                    resp = self.session.delete(url, params=params, timeout=self.config.request_timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check HTTP status
                if resp.status_code == 200:
                    return resp.json()
                
                # Handle error responses
                err_data = resp.json() if resp.text else {}
                err_code = err_data.get('code', resp.status_code)
                err_msg = err_data.get('msg', resp.text)
                
                # Sanitize error message to prevent secret exposure
                sanitized_msg = sanitize_log_message(
                    f"Binance API Error {err_code}: {err_msg}",
                    [self.config.api_key, self.config.api_secret]
                )
                logger.warning(f"HTTP {resp.status_code} on {endpoint} (attempt {attempt}/{self.config.max_retries}): {sanitized_msg}")
                
                # Non-retriable error codes (e.g. invalid permissions, bad syntax)
                if err_code in [-1002, -1013, -1100, -2010, -2011, -2015]:
                    raise BinanceClientError(sanitized_msg)

            except requests.exceptions.RequestException as e:
                sanitized_e = sanitize_log_message(str(e), [self.config.api_key, self.config.api_secret])
                logger.warning(f"Network error on {endpoint} (attempt {attempt}/{self.config.max_retries}): {sanitized_e}")
                if attempt == self.config.max_retries:
                    raise BinanceClientError(f"Max retries reached on {endpoint}: {sanitized_e}")
                time.sleep(self.config.retry_backoff_sec * attempt)

        raise BinanceClientError(f"Failed to execute request to {endpoint}")

    # ==================== Public Market Data ====================

    def ping(self) -> bool:
        """Tests connectivity to the endpoint."""
        try:
            res = self._request("GET", "/fapi/v1/ping")
            return res == {}
        except Exception:
            return False

    def get_server_time(self) -> int:
        """Fetches server timestamp in milliseconds."""
        res = self._request("GET", "/fapi/v1/time")
        return res.get("serverTime", int(time.time() * 1000))

    def fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 500) -> List[List[Any]]:
        """Fetches historical Klines (OHLCV) without authentication."""
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        return self._request("GET", "/fapi/v1/klines", params=params, signed=False)

    def fetch_mark_price(self, symbol: str) -> float:
        """Fetches latest mark price for a symbol."""
        params = {"symbol": symbol}
        res = self._request("GET", "/fapi/v1/premiumIndex", params=params, signed=False)
        return float(res.get("markPrice", 0.0))

    # ==================== Account & Position Endpoints ====================

    def get_account_balance(self) -> List[Dict[str, Any]]:
        """Fetches margin account balances."""
        if self.config.env == ExecutionMode.PAPER:
            return [{"asset": "USDT", "balance": "5000.00", "availableBalance": "5000.00"}]
        return self._request("GET", "/fapi/v2/balance", signed=True)

    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetches current open positions on the exchange."""
        if self.config.env == ExecutionMode.PAPER:
            return []
        res = self._request("GET", "/fapi/v2/positionRisk", signed=True)
        # Filter active positions
        return [p for p in res if float(p.get("positionAmt", 0.0)) != 0.0]

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches open active orders."""
        if self.config.env == ExecutionMode.PAPER:
            return []
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def get_order_status(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches detailed status of a specific order."""
        if self.config.env == ExecutionMode.PAPER:
            return {"status": "FILLED", "origQty": "0", "executedQty": "0"}
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    # ==================== Order Execution Endpoints ====================

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
        Submits a new order to Binance Futures.
        Fails closed in PAPER mode (simulation only) and validates limits.
        """
        if self.config.kill_switch_active:
            raise BinanceSecurityBreachError("ORDER REJECTED: Kill Switch is ACTIVE. No new orders allowed.")

        if self.config.env == ExecutionMode.PAPER:
            logger.info(f"📝 [PAPER SIMULATED ORDER] {side} {quantity} {symbol} @ {order_type} (clientOrderId={client_order_id})")
            return {
                "symbol": symbol,
                "orderId": int(time.time() * 1000),
                "clientOrderId": client_order_id or f"paper_{int(time.time()*1000)}",
                "status": "FILLED",
                "cumQty": str(quantity),
                "executedQty": str(quantity),
                "avgPrice": str(price or self.fetch_mark_price(symbol)),
                "side": side,
                "type": order_type
            }

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": f"{quantity:.6f}".rstrip('0').rstrip('.'),
        }
        if client_order_id:
            params["newClientOrderId"] = client_order_id
        if reduce_only:
            params["reduceOnly"] = "true"
        if order_type.upper() == "LIMIT" and price is not None:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"

        logger.info(f"🚀 [BINANCE ORDER SUBMIT] {side} {quantity} {symbol} ({self.config.env.value}) clientOrderId={client_order_id}")
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancels an existing open order."""
        if self.config.env == ExecutionMode.PAPER:
            return {"status": "CANCELED"}
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """Cancels all open orders for a symbol."""
        if self.config.env == ExecutionMode.PAPER:
            return {"code": 200, "msg": "all canceled (paper)"}
        params = {"symbol": symbol}
        return self._request("DELETE", "/fapi/v1/allOpenOrders", params=params, signed=True)

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Sets initial leverage for a symbol (constrained by max_leverage)."""
        leverage = min(leverage, self.config.max_leverage)
        if self.config.env == ExecutionMode.PAPER:
            return {"leverage": leverage, "symbol": symbol}
        params = {"symbol": symbol, "leverage": leverage}
        return self._request("POST", "/fapi/v1/leverage", params=params, signed=True)

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> Dict[str, Any]:
        """Sets margin type (ISOLATED or CROSSED)."""
        if self.config.env == ExecutionMode.PAPER:
            return {"code": 200, "msg": "success (paper)"}
        params = {"symbol": symbol, "marginType": margin_type.upper()}
        try:
            return self._request("POST", "/fapi/v1/marginType", params=params, signed=True)
        except BinanceClientError as e:
            # Code -4046: "No need to change margin type" is expected if already set
            if "No need to change" in str(e):
                return {"code": 200, "msg": "already set"}
            raise
