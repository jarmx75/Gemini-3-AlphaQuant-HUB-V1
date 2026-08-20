"""
Cross-Asset Time Series Momentum (TSMOM 1D) Strategy Adapter
Implements signal generation and target weight allocation for M1 (N=21) and M2 (N=63).

Universe: SPY, QQQ, IWM, XLF, XLK, XLE, GLD, TLT
Mechanics:
- Momentum Feature: R_N = Close_t / Close_{t-N} - 1
- Long if R_N > 0, Cash if R_N <= 0
- Volatility Scaling: Inverse 20-day realized volatility
- Position Cap: 25% max per asset
- Zero Look-Ahead: Signals at day t close yield rebalance targets executed at t+1
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "GLD", "TLT"]


class EquityTSMOMAdapter:
    """
    Adapter generating daily portfolio weights and rebalancing orders for TSMOM strategies.
    """

    def __init__(
        self,
        strategy_id: str,
        lookback_window: int = 21,
        vol_window: int = 20,
        max_weight_cap: float = 0.25,
        universe: Optional[List[str]] = None
    ):
        self.strategy_id = strategy_id
        self.lookback_window = lookback_window
        self.vol_window = vol_window
        self.max_weight_cap = max_weight_cap
        self.universe = universe or list(DEFAULT_UNIVERSE)
        self.market = "US_EQUITY_ETF"
        self.timeframe = "1D"
        self.broker = "ALPACA"

    def compute_target_weights(self, df_close: pd.DataFrame) -> Dict[str, float]:
        """
        Computes portfolio target weights based on latest available historical close prices.
        df_close must contain columns for each symbol in self.universe, ordered chronologically.
        """
        if len(df_close) < max(self.lookback_window, self.vol_window) + 1:
            logger.warning(f"[{self.strategy_id}] Insufficient historical bars ({len(df_close)}) for lookback {self.lookback_window}.")
            return {sym: 0.0 for sym in self.universe}

        # Ensure all universe symbols are present
        missing = [s for s in self.universe if s not in df_close.columns]
        if missing:
            raise ValueError(f"[{self.strategy_id}] Missing universe columns in price data: {missing}")

        df_sub = df_close[self.universe].copy()
        
        # 1. Momentum: R_N = Close_t / Close_{t-N} - 1
        curr_prices = df_sub.iloc[-1].values
        past_prices = df_sub.iloc[-1 - self.lookback_window].values
        mom = (curr_prices / past_prices) - 1.0

        # 2. 20-day realized volatility: std(daily returns) * sqrt(252)
        returns_20d = df_sub.iloc[-1 - self.vol_window:].pct_change().dropna()
        vol_20d = returns_20d.std().values * np.sqrt(252)
        vol_20d = np.where(vol_20d > 1e-4, vol_20d, 0.15) # Default 15% floor

        # 3. Active Long Signals (R_N > 0)
        active_mask = mom > 0.0
        
        if not np.any(active_mask):
            # 100% Cash allocation
            return {sym: 0.0 for sym in self.universe}

        # 4. Volatility Scaling: Inverse Volatility
        inv_vol = np.where(active_mask, 1.0 / vol_20d, 0.0)
        sum_inv_vol = np.sum(inv_vol)
        if sum_inv_vol <= 0:
            return {sym: 0.0 for sym in self.universe}

        raw_w = inv_vol / sum_inv_vol
        
        # 5. Apply 25% Cap and Re-normalize
        capped_w = np.minimum(raw_w, self.max_weight_cap)
        if np.sum(capped_w) > 0:
            final_w = capped_w / max(1.0, np.sum(capped_w))
        else:
            final_w = capped_w

        target_weights = {self.universe[i]: round(float(final_w[i]), 4) for i in range(len(self.universe))}
        return target_weights

    def generate_rebalance_orders(
        self,
        current_positions: Dict[str, float],
        target_weights: Dict[str, float],
        total_equity: float,
        current_prices: Dict[str, float],
        min_trade_notional: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Generates list of rebalancing orders required to move current portfolio to target weights.
        """
        orders = []
        
        for sym in self.universe:
            curr_qty = current_positions.get(sym, 0.0)
            price = current_prices.get(sym, 0.0)
            if price <= 0.0:
                logger.error(f"Invalid price for {sym}: {price}")
                continue

            target_w = target_weights.get(sym, 0.0)
            target_notional = total_equity * target_w
            curr_notional = curr_qty * price
            delta_notional = target_notional - curr_notional

            if abs(delta_notional) >= min_trade_notional:
                side = "BUY" if delta_notional > 0 else "SELL"
                delta_qty = round(abs(delta_notional) / price, 4)
                
                if delta_qty > 0:
                    orders.append({
                        "strategy_id": self.strategy_id,
                        "symbol": sym,
                        "side": side,
                        "qty": delta_qty,
                        "price": price,
                        "delta_notional": round(delta_notional, 2),
                        "target_weight": target_w,
                        "current_weight": round(curr_notional / total_equity, 4) if total_equity > 0 else 0.0
                    })

        # Process SELL orders first to free up cash, then BUY orders
        orders.sort(key=lambda o: 0 if o["side"] == "SELL" else 1)
        return orders
