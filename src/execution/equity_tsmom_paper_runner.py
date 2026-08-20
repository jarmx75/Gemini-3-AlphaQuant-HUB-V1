"""
Equity TSMOM Paper Runner (Alpaca Paper Trading)
Forward paper execution engine for US Equity ETF Time Series Momentum strategies (M1 & M2).

STRICT SECURITY INVARIANTS:
1. ENVIRONMENT == 'ALPACA_PAPER' strictly enforced.
2. Alpaca Paper REST endpoint (https://paper-api.alpaca.markets) strictly enforced.
3. Any live endpoint (https://api.alpaca.markets) raises SecurityViolationError and terminates immediately.
4. APPROVED=false, DEMO_ORDERS=0, REAL_ORDERS=0, ALPACA_LIVE_ORDERS=0 preserved.
5. Real forward paper trades logged to logs/paper/bitacora_equity_tsmom_paper.csv.
6. Independent paper gate = 100 closed trades per strategy.
"""

import os
import sys
import time
import json
import uuid
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from src.memory.preflight import enforce_preflight
from src.execution.broker_adapters.alpaca_paper import (
    AlpacaPaperBroker,
    ALPACA_PAPER_BASE_URL,
    FORBIDDEN_LIVE_URL,
    SecurityViolationError
)
from src.strategies.equity_tsmom_adapter import EquityTSMOMAdapter, DEFAULT_UNIVERSE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"
DATA_DIR = PROJECT_ROOT / "data" / "historical_equities"
LOGS_PAPER_DIR = PROJECT_ROOT / "logs" / "paper"
LOGS_EXEC_DIR = PROJECT_ROOT / "logs" / "execution"
LOGS_PAPER_DIR.mkdir(parents=True, exist_ok=True)
LOGS_EXEC_DIR.mkdir(parents=True, exist_ok=True)

EQUITY_CSV_LOG = LOGS_PAPER_DIR / "bitacora_equity_tsmom_paper.csv"
EQUITY_POSITIONS_FILE = LOGS_EXEC_DIR / "paper_positions_equity.json"
EQUITY_HEALTH_FILE = LOGS_PAPER_DIR / "equity_runner_health.json"


class EquityTSMOMPaperRunner:
    """
    Production-grade Paper Runner executing daily TSMOM rebalancing across US Equity ETFs.
    """

    def __init__(
        self,
        broker: Optional[AlpacaPaperBroker] = None,
        mock_mode: bool = True,
        initial_capital: float = 100000.0,
        registry_path: Optional[Path] = None,
        csv_log_path: Optional[Path] = None,
        positions_file: Optional[Path] = None,
        health_file: Optional[Path] = None
    ):
        self.mock_mode = mock_mode
        self.initial_capital = initial_capital
        self.registry_path = Path(registry_path or REGISTRY_PATH)
        self.csv_log_path = Path(csv_log_path or EQUITY_CSV_LOG)
        self.positions_file = Path(positions_file or EQUITY_POSITIONS_FILE)
        self.health_file = Path(health_file or EQUITY_HEALTH_FILE)
        
        # 1. Preflight Enforce
        self._preflight_check()

        # 2. Broker Initialization & Security Enforcement
        if broker:
            self.broker = broker
        else:
            self.broker = AlpacaPaperBroker(
                base_url=ALPACA_PAPER_BASE_URL,
                environment="ALPACA_PAPER",
                mock_mode=mock_mode,
                initial_cash=initial_capital
            )

        # 3. State structures
        self.adapters: Dict[str, EquityTSMOMAdapter] = {}
        self.open_positions: Dict[str, Dict[str, Any]] = {} # position_id -> dict
        self.processed_order_ids: set = set()
        self.last_market_date: Optional[str] = None
        self.last_error: Optional[str] = None
        self.watchdog_status: str = "HEALTHY"
        self.reconciliation_status: str = "IN_SYNC"

        # 4. Initialization
        self._init_csv()
        self._load_active_strategies()
        self._restore_positions()

    def _preflight_check(self):
        """Preflight memory check."""
        family_name = "CROSS_ASSET_TSMOM_1D"
        hypothesis = "Time-series momentum daily cross-asset trend following with inverse volatility scaling"
        if not enforce_preflight(family_name, hypothesis):
            raise PermissionError(f"🛑 PREFLIGHT BLOCKED: Family {family_name} is rejected by Automaton Memory.")

    def _init_csv(self):
        """Initializes bitacora_equity_tsmom_paper.csv with required schema."""
        header = "timestamp,strategy_id,symbol,side,qty,entry,exit,pnl,fees,position_id,order_id\n"
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write(header)

    def _load_active_strategies(self):
        """Loads all active TSMOM strategies from registry.json."""
        self.adapters.clear()
        if not self.registry_path.exists():
            logger.warning(f"Registry file not found at {self.registry_path}")
            return

        with open(self.registry_path, "r", encoding="utf-8") as f:
            reg_data = json.load(f)

        candidates = reg_data.get("active_equity_paper_strategies", []) + reg_data.get("active_paper_strategies", [])
        for s in candidates:
            if s.get("family") == "CROSS_ASSET_TSMOM_1D" and s.get("status") == "PAPER_ACTIVE":
                strat_id = s["id"]
                if strat_id not in self.adapters:
                    adapter = EquityTSMOMAdapter(
                        strategy_id=strat_id,
                        lookback_window=s.get("lookback_window", 21),
                        vol_window=s.get("vol_window", 20),
                        max_weight_cap=s.get("max_weight_cap", 0.25),
                        universe=s.get("universe", DEFAULT_UNIVERSE)
                    )
                    self.adapters[strat_id] = adapter
                    logger.info(f"Loaded equity paper adapter: {strat_id} (lookback={adapter.lookback_window}d)")

    def _restore_positions(self):
        """Restores local open positions from JSON state file."""
        if self.positions_file.exists():
            try:
                with open(self.positions_file, "r", encoding="utf-8") as f:
                    self.open_positions = json.load(f)
                logger.info(f"💾 Restored {len(self.open_positions)} open equity positions from {self.positions_file}")
            except Exception as e:
                logger.error(f"Failed to restore equity positions: {e}")
                self.open_positions = {}

    def _persist_positions(self):
        """Saves current open positions to JSON state file."""
        try:
            with open(self.positions_file, "w", encoding="utf-8") as f:
                json.dump(self.open_positions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist equity positions: {e}")

    def load_market_data(self, n_bars: int = 100) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """Loads and aligns daily close prices for universe ETFs."""
        close_dict = {}
        for sym in DEFAULT_UNIVERSE:
            fpath = DATA_DIR / f"{sym}_1d_2022_2026.csv"
            if not fpath.exists():
                self.watchdog_status = f"HALTED_MISSING_DATA_{sym}"
                raise FileNotFoundError(f"Market data file not found: {fpath}")
            df = pd.read_csv(fpath)
            df['date'] = pd.to_datetime(df['date'])
            close_dict[sym] = df.set_index('date')['close']

        df_close = pd.DataFrame(close_dict).sort_index().dropna()
        if len(df_close) < 65:
            self.watchdog_status = "HALTED_INSUFFICIENT_BARS"
            raise ValueError(f"Insufficient historical bars: {len(df_close)}")

        self.watchdog_status = "HEALTHY"
        latest_prices = df_close.iloc[-1].to_dict()
        self.last_market_date = df_close.index[-1].strftime("%Y-%m-%d")
        return df_close.iloc[-n_bars:], latest_prices

    def reconcile_positions(self) -> bool:
        """Reconciles local position records against Alpaca Paper broker."""
        broker_positions = self.broker.get_positions()
        broker_pos_map = {p['symbol']: float(p['qty']) for p in broker_positions}

        local_pos_map = {}
        for pos in self.open_positions.values():
            sym = pos['symbol']
            local_pos_map[sym] = local_pos_map.get(sym, 0.0) + float(pos['qty'])

        all_symbols = set(broker_pos_map.keys()).union(set(local_pos_map.keys()))
        for sym in all_symbols:
            b_qty = broker_pos_map.get(sym, 0.0)
            l_qty = local_pos_map.get(sym, 0.0)
            if abs(b_qty - l_qty) > 1e-3:
                logger.error(f"🛑 [RECONCILIATION MISMATCH] {sym}: Broker has {b_qty} shares, Local state has {l_qty} shares!")
                self.reconciliation_status = f"MISMATCH_{sym}"
                return False

        self.reconciliation_status = "IN_SYNC"
        return True

    def process_session(self) -> Dict[str, Any]:
        """
        Executes one daily session cycle for all active TSMOM strategies:
        Market Data -> Signals -> Target Weights -> Rebalance Orders -> Execution -> Position Update -> Reconciliation
        """
        t0 = time.time()
        logger.info(f"=== PROCESSING EQUITY PAPER SESSION CYCLE [{datetime.now(timezone.utc).isoformat()}] ===")

        # 1. Load Data
        df_close, current_prices = self.load_market_data(n_bars=100)
        self.broker.set_mock_prices(current_prices)
        logger.info(f"Market Date: {self.last_market_date} | Universe Prices: {current_prices}")

        # 2. Reconcile Pre-Execution
        if not self.reconcile_positions():
            logger.error("🛑 Session halted due to pre-execution position mismatch.")
            self._update_health()
            return {"status": "HALTED", "reason": self.reconciliation_status}

        account = self.broker.get_account()
        total_equity = float(account['portfolio_value'])
        session_fills = []

        # 3. Process Each Strategy
        for strat_id, adapter in self.adapters.items():
            logger.info(f"\n--- Strategy: {strat_id} ---")
            target_weights = adapter.compute_target_weights(df_close)
            logger.info(f"Target Weights: {target_weights}")

            strat_curr_pos = {}
            for pos_id, pos in list(self.open_positions.items()):
                if pos['strategy_id'] == strat_id:
                    strat_curr_pos[pos['symbol']] = pos['qty']

            orders = adapter.generate_rebalance_orders(
                current_positions=strat_curr_pos,
                target_weights=target_weights,
                total_equity=total_equity / len(self.adapters),
                current_prices=current_prices
            )

            logger.info(f"Generated {len(orders)} rebalancing orders.")

            for ord_req in orders:
                sym = ord_req['symbol']
                side = ord_req['side']
                qty = ord_req['qty']
                cid = f"eq_{strat_id}_{self.last_market_date}_{sym}_{side}"

                if cid in self.processed_order_ids:
                    logger.warning(f"⚠️ [IDEMPOTENT SKIP] Order {cid} already processed this session.")
                    continue

                res = self.broker.submit_order(
                    symbol=sym,
                    qty=qty,
                    side=side,
                    order_type="market",
                    client_order_id=cid
                )
                self.processed_order_ids.add(cid)
                session_fills.append(res)

                self._update_position_and_log_trades(strat_id, sym, side, qty, float(res.get('filled_avg_price', ord_req['price'])), cid)

        # 4. Post-Execution Reconciliation & State Persist
        self.reconcile_positions()
        self._persist_positions()
        self._update_health()

        logger.info(f"=== SESSION COMPLETED: {len(session_fills)} orders filled in {time.time()-t0:.2f}s ===")
        return {
            "status": "COMPLETED",
            "market_date": self.last_market_date,
            "orders_filled": len(session_fills),
            "open_positions": len(self.open_positions),
            "portfolio_value": float(self.broker.get_account()['portfolio_value'])
        }

    def _update_position_and_log_trades(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        order_id: str
    ):
        """Updates local positions and logs closed trades to bitacora_equity_tsmom_paper.csv."""
        pos_id = f"{strategy_id}_{symbol}"
        ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if side.upper() == "BUY":
            if pos_id in self.open_positions:
                curr = self.open_positions[pos_id]
                tot_qty = curr['qty'] + qty
                avg_entry = ((curr['qty'] * curr['entry_price']) + (qty * price)) / tot_qty
                self.open_positions[pos_id]['qty'] = round(tot_qty, 4)
                self.open_positions[pos_id]['entry_price'] = round(avg_entry, 2)
            else:
                self.open_positions[pos_id] = {
                    "position_id": pos_id,
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "qty": round(qty, 4),
                    "entry_price": round(price, 2),
                    "entry_time": ts_now
                }
        else: # SELL
            if pos_id in self.open_positions:
                curr = self.open_positions[pos_id]
                close_qty = min(curr['qty'], qty)
                entry_p = curr['entry_price']
                exit_p = price
                pnl = round((exit_p - entry_p) * close_qty, 2)
                fees = round((entry_p + exit_p) * close_qty * 0.0008, 2)

                row = f"{ts_now},{strategy_id},{symbol},SELL,{close_qty:.4f},{entry_p:.2f},{exit_p:.2f},{pnl:.2f},{fees:.2f},{pos_id},{order_id}\n"
                with open(self.csv_log_path, "a", encoding="utf-8") as f:
                    f.write(row)
                logger.info(f"🏁 [EQUITY PAPER CLOSE] [{strategy_id}] {symbol} x {close_qty:.4f} | PnL: ${pnl:.2f} USD | Fees: ${fees:.2f}")

                rem_qty = curr['qty'] - close_qty
                if rem_qty <= 1e-4:
                    del self.open_positions[pos_id]
                else:
                    self.open_positions[pos_id]['qty'] = round(rem_qty, 4)

    def count_closed_paper_trades(self, strategy_id: str) -> int:
        """Counts total verified closed paper trades for strategy in CSV log."""
        if not self.csv_log_path.exists():
            return 0
        try:
            df = pd.read_csv(self.csv_log_path)
            if df.empty or 'strategy_id' not in df.columns:
                return 0
            return len(df[df['strategy_id'] == strategy_id])
        except Exception:
            return 0

    def _update_health(self):
        """Writes health status JSON."""
        health = {
            "heartbeat": datetime.now(timezone.utc).isoformat(),
            "environment": "ALPACA_PAPER",
            "base_url": ALPACA_PAPER_BASE_URL,
            "last_market_date": self.last_market_date,
            "strategies_loaded": list(self.adapters.keys()),
            "open_positions_count": len(self.open_positions),
            "closed_trades_by_strategy": {s: self.count_closed_paper_trades(s) for s in self.adapters},
            "reconciliation_status": self.reconciliation_status,
            "watchdog_status": self.watchdog_status,
            "last_error": self.last_error,
            "security_invariants": {
                "APPROVED": False,
                "DEMO_ORDERS": 0,
                "REAL_ORDERS": 0,
                "ALPACA_LIVE_ORDERS": 0
            }
        }
        with open(self.health_file, "w", encoding="utf-8") as f:
            json.dump(health, f, indent=2)

    def run_continuous(self, poll_interval_sec: int = 3600, max_iterations: Optional[int] = None):
        """Runs continuous forward paper loop for equities."""
        logger.info(f"🚀 [EQUITY PAPER RUNNER DAEMON START] PID={os.getpid()} | Polling every {poll_interval_sec}s")
        iterations = 0
        while True:
            try:
                self.process_session()
                iterations += 1
                if max_iterations and iterations >= max_iterations:
                    logger.info(f"Target iterations ({max_iterations}) completed. Exiting loop.")
                    break
                time.sleep(poll_interval_sec)
            except KeyboardInterrupt:
                logger.info("Equity runner stopped by user.")
                break
            except Exception as e:
                self.last_error = f"Runner loop exception: {e}"
                logger.error(self.last_error)
                self._update_health()
                time.sleep(60)


def main():
    logger.info("Starting Equity TSMOM Paper Runner (Alpaca Paper)...")
    runner = EquityTSMOMPaperRunner(mock_mode=True)
    runner.run_continuous(poll_interval_sec=3600)


if __name__ == '__main__':
    main()

