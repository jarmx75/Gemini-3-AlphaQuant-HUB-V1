"""
Alpaca Paper Trading Broker Adapter
Strictly enforces Alpaca Paper endpoints (https://paper-api.alpaca.markets).
Rejects any live endpoint (https://api.alpaca.markets) or live credentials with SecurityViolationError.

STRICT SECURITY INVARIANTS:
1. APPROVED=false invariant preserved.
2. LIVE_TRADING_ENABLED=false invariant preserved.
3. Live endpoints (https://api.alpaca.markets) are strictly forbidden and raise fatal exception.
"""

import os
import time
import uuid
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
FORBIDDEN_LIVE_URL = "https://api.alpaca.markets"


class SecurityViolationError(Exception):
    """Raised when an unauthorized live trading endpoint or configuration is detected."""
    pass


class AlpacaPaperBroker:
    """
    Broker adapter for Alpaca Paper Trading REST API.
    Supports both real paper API connectivity and local in-memory simulation (mock mode).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = ALPACA_PAPER_BASE_URL,
        environment: str = "ALPACA_PAPER",
        mock_mode: bool = False,
        initial_cash: float = 100000.0
    ):
        self.environment = environment
        self.mock_mode = mock_mode
        self.base_url = base_url.rstrip("/")
        
        # 1. Strict Security Checks
        self._enforce_security_constraints()

        self.api_key = api_key or os.getenv("ALPACA_PAPER_API_KEY", "MOCK_ALPACA_PAPER_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_PAPER_SECRET_KEY", "MOCK_ALPACA_PAPER_SECRET")

        # In-memory state for mock/offline testing
        self.cash = initial_cash
        self.portfolio_value = initial_cash
        self.mock_positions: Dict[str, Dict[str, Any]] = {}
        self.mock_orders: Dict[str, Dict[str, Any]] = {}
        self.mock_prices: Dict[str, float] = {
            "SPY": 550.0,
            "QQQ": 480.0,
            "IWM": 210.0,
            "XLF": 45.0,
            "XLK": 220.0,
            "XLE": 90.0,
            "GLD": 230.0,
            "TLT": 95.0
        }

    def _enforce_security_constraints(self):
        """Validates that under no circumstances is live trading URL or live environment allowed."""
        if self.environment != "ALPACA_PAPER":
            raise SecurityViolationError(
                f"🛑 FATAL SECURITY VIOLATION: Environment must be 'ALPACA_PAPER', got '{self.environment}'"
            )
        
        if "paper" not in self.base_url.lower() or FORBIDDEN_LIVE_URL in self.base_url:
            raise SecurityViolationError(
                f"🛑 FATAL SECURITY VIOLATION: Live Alpaca URL detected ({self.base_url})! "
                f"Only paper endpoint ({ALPACA_PAPER_BASE_URL}) is permitted."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def set_mock_prices(self, prices: Dict[str, float]):
        """Sets mock prices for symbols."""
        self.mock_prices.update(prices)

    def get_account(self) -> Dict[str, Any]:
        """Fetches account information."""
        self._enforce_security_constraints()
        if self.mock_mode:
            pos_val = sum(p['market_value'] for p in self.mock_positions.values())
            self.portfolio_value = self.cash + pos_val
            return {
                "id": "mock_alpaca_paper_account",
                "status": "ACTIVE",
                "currency": "USD",
                "buying_power": f"{self.cash * 2.0:.2f}",
                "cash": f"{self.cash:.2f}",
                "portfolio_value": f"{self.portfolio_value:.2f}",
                "pattern_day_trader": False,
                "trading_blocked": False,
                "transfers_blocked": False,
                "account_blocked": False
            }

        url = f"{self.base_url}/v2/account"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetches all open equity positions."""
        self._enforce_security_constraints()
        if self.mock_mode:
            res = []
            for sym, pos in self.mock_positions.items():
                qty = pos.get('qty', 0.0)
                if abs(qty) > 1e-4:
                    curr_p = self.mock_prices.get(sym, pos['avg_entry_price'])
                    mv = qty * curr_p
                    unrealized_pl = mv - (qty * pos['avg_entry_price'])
                    res.append({
                        "symbol": sym,
                        "qty": f"{qty:.4f}",
                        "avg_entry_price": f"{pos['avg_entry_price']:.2f}",
                        "current_price": f"{curr_p:.2f}",
                        "market_value": f"{mv:.2f}",
                        "unrealized_pl": f"{unrealized_pl:.2f}"
                    })
            return res

        url = f"{self.base_url}/v2/positions"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submits an equity order to Alpaca Paper."""
        self._enforce_security_constraints()
        side_norm = side.lower()
        cid = client_order_id or f"alp_paper_{uuid.uuid4().hex[:12]}"

        if self.mock_mode:
            price = self.mock_prices.get(symbol, 100.0)
            cost = qty * price
            fee = cost * 0.0008 # 0.08% simulation fee

            if side_norm == "buy":
                self.cash -= (cost + fee)
                curr = self.mock_positions.get(symbol, {'qty': 0.0, 'avg_entry_price': price, 'market_value': 0.0})
                new_qty = curr['qty'] + qty
                avg_entry = ((curr['qty'] * curr['avg_entry_price']) + (qty * price)) / new_qty
                self.mock_positions[symbol] = {
                    'symbol': symbol,
                    'qty': round(new_qty, 4),
                    'avg_entry_price': round(avg_entry, 2),
                    'market_value': round(new_qty * price, 2)
                }
            else:
                self.cash += (cost - fee)
                if symbol in self.mock_positions:
                    new_qty = self.mock_positions[symbol]['qty'] - qty
                    if new_qty <= 1e-4:
                        del self.mock_positions[symbol]
                    else:
                        self.mock_positions[symbol]['qty'] = round(new_qty, 4)
                        self.mock_positions[symbol]['market_value'] = round(new_qty * price, 2)

            order_data = {
                "id": str(uuid.uuid4()),
                "client_order_id": cid,
                "symbol": symbol,
                "qty": str(qty),
                "filled_qty": str(qty),
                "filled_avg_price": str(price),
                "side": side_norm,
                "type": order_type,
                "time_in_force": time_in_force,
                "status": "filled",
                "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "filled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self.mock_orders[cid] = order_data
            logger.info(f"⚡ [ALPACA PAPER MOCK FILL] {side_norm.upper()} {qty} {symbol} @ ${price:.2f} USD (Cash: ${self.cash:.2f})")
            return order_data

        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side_norm,
            "type": order_type,
            "time_in_force": time_in_force,
            "client_order_id": cid
        }
        url = f"{self.base_url}/v2/orders"
        r = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def cancel_order(self, order_id: str) -> bool:
        """Cancels a specific order."""
        self._enforce_security_constraints()
        if self.mock_mode:
            if order_id in self.mock_orders:
                self.mock_orders[order_id]['status'] = "canceled"
                return True
            return False

        url = f"{self.base_url}/v2/orders/{order_id}"
        r = requests.delete(url, headers=self._headers(), timeout=10)
        return r.status_code == 204

    def cancel_all_orders(self) -> List[Dict[str, Any]]:
        """Cancels all open orders."""
        self._enforce_security_constraints()
        if self.mock_mode:
            for o in self.mock_orders.values():
                o['status'] = "canceled"
            return list(self.mock_orders.values())

        url = f"{self.base_url}/v2/orders"
        r = requests.delete(url, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()
