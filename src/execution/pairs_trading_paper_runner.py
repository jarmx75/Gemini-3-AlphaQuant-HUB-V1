"""
Pairs Trading Autonomous Multi-Strategy Paper Runner
100% Paper Trading Simulation Mode (Forward Live Accumulation):
  - Preflight verification via MemoryPreflight.
  - Dynamically loads all active PAPER_ACTIVE strategies from registry.json.
  - Slices independent StrategyAdapters per candidate.
  - Sincroniza y persiste estado de posiciones en open_positions_state.json.
  - Emite telemetría y heartbeat a runner_health.json.
  - Watchdog de datos frescos (>30 min desactiva nuevas entradas).
  - Registra OPEN y CLOSE en logs/paper/bitacora_pairs_trading_paper.csv.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.strategies.pairs_trading_stat_arb import PairsTradingStatArb
from src.memory.preflight import enforce_preflight

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Directories & Files
LOG_DIR = PROJECT_ROOT / "logs" / "paper"
LOG_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"
CSV_LOG_PATH = LOG_DIR / "bitacora_pairs_trading_paper.csv"
STATE_FILE_PATH = LOG_DIR / "open_positions_state.json"
HEALTH_FILE_PATH = LOG_DIR / "runner_health.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "historial_pairs_paper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StrategyAdapter:
    """Executable adapter for a specific strategy candidate."""
    def __init__(self, config: Dict[str, Any]):
        self.strategy_id = config.get("id", "UNKNOWN")
        self.family = config.get("family", "MEAN_REVERSION_1H")
        self.lookback_window = int(config.get("lookback_window", 90))
        self.z_entry = float(config.get("z_entry", 2.5))
        self.z_exit = float(config.get("z_exit", 0.0))
        self.z_stop = float(config.get("z_stop", 3.5))
        self.max_holding_bars = int(config.get("max_holding_bars", 24))
        self.adf_p_threshold = float(config.get("adf_p_threshold", 0.05))
        
        self.engine = PairsTradingStatArb(
            lookback_window=self.lookback_window,
            z_entry=self.z_entry,
            z_exit=self.z_exit,
            z_stop=self.z_stop,
            max_holding_bars=self.max_holding_bars,
            adf_p_threshold=self.adf_p_threshold
        )


class PairsTradingPaperRunner:
    """Multi-Strategy Paper Trading Forward Orchestrator."""
    
    def __init__(self, initial_paper_balance: float = 5000.0, use_binance_client: bool = True):
        load_dotenv()
        self.use_binance = use_binance_client
        self.client = None
        
        # 0. Preflight Gate Check
        self._run_preflight()

        if self.use_binance and UMFutures is not None:
            try:
                self.client = UMFutures(
                    key=os.getenv('BINANCE_TEST_KEY', ''),
                    secret=os.getenv('BINANCE_TEST_SECRET', ''),
                    base_url='https://testnet.binancefuture.com'
                )
            except Exception as e:
                logger.warning(f"Could not initialize Binance client for paper runner: {e}")

        self.monitored_pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        
        self.paper_balance = initial_paper_balance
        self.notional_per_leg = 150.0  # $150 USD por pata ($300 total)
        self.fee_rate_roundtrip = 0.0016 # 0.16% total en 2 patas
        
        self.csv_log_path = CSV_LOG_PATH
        self.state_file_path = STATE_FILE_PATH
        self.health_file_path = HEALTH_FILE_PATH
        
        # Open positions indexed by (strategy_id, pair_name)
        self.open_paper_positions: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.adapters: Dict[str, StrategyAdapter] = {}
        self.last_signal_by_strategy: Dict[str, Optional[Dict[str, Any]]] = {}
        self.trades_closed_by_strategy: Dict[str, int] = {}
        self.last_market_timestamp_str: str = "N/A"
        self.last_market_timestamp_unix: float = time.time()
        self.watchdog_status: str = "OK"
        self.last_error: Optional[str] = None
        
        self.load_active_strategy_adapters()
        self.init_csv()
        self.load_position_state()
        self.update_health()

    def _run_preflight(self):
        """Mandatory Memory Preflight verification."""
        family_name = "MEAN_REVERSION_1H"
        hypothesis = "Statistical Arbitrage & Cointegration Pairs Trading with RegimeFilter"
        if not enforce_preflight(family_name, hypothesis):
            raise PermissionError(f"🛑 PREFLIGHT BLOCKED: Family {family_name} is rejected by Automaton Memory.")

    def load_active_strategy_adapters(self):
        """Loads all active paper strategies from registry.json."""
        self.adapters.clear()
        if not REGISTRY_PATH.exists():
            logger.warning(f"Registry not found at {REGISTRY_PATH}")
            return

        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry_data = json.load(f)

        active_strats = registry_data.get("active_paper_strategies", [])
        for s in active_strats:
            strat_id = s.get("id")
            if strat_id and ("z_entry" in s or s.get("family") == "MEAN_REVERSION_1H"):
                adapter = StrategyAdapter(s)
                self.adapters[strat_id] = adapter
                self.last_signal_by_strategy[strat_id] = None
                self.trades_closed_by_strategy[strat_id] = self._count_logged_closed_trades(strat_id)
                logger.info(f"Loaded paper adapter for strategy: {strat_id} (z_entry={adapter.z_entry}, window={adapter.lookback_window})")

    def _count_logged_closed_trades(self, strategy_id: str) -> int:
        """Counts existing closed trades for a strategy in CSV."""
        if not self.csv_log_path.exists():
            return 0
        try:
            df = pd.read_csv(self.csv_log_path)
            if df.empty or 'strategy_id' not in df.columns or 'action' not in df.columns:
                return 0
            return len(df[(df['strategy_id'] == strategy_id) & (df['action'] == 'CLOSE')])
        except Exception:
            return 0

    def init_csv(self):
        """Initializes paper trades CSV log with required schema."""
        header = "timestamp,strategy_id,pair,action,entry,exit,pnl,fees,position_id,gamma,z_entry,z_exit,holding_bars,paper_balance,reason\n"
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write(header)
        else:
            with open(self.csv_log_path, "r", encoding="utf-8") as f:
                first_line = f.readline()
            if "position_id" not in first_line or "strategy_id" not in first_line:
                # Upgrade legacy format
                with open(self.csv_log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(self.csv_log_path, "w", encoding="utf-8") as f:
                    f.write(header)

    def save_position_state(self):
        """Persists open paper positions to JSON."""
        state_data = {}
        for (strat_id, pair_name), pos in self.open_paper_positions.items():
            key = f"{strat_id}::{pair_name}"
            state_data[key] = pos

        with open(self.state_file_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def load_position_state(self):
        """Reloads persisted open paper positions on startup."""
        if not self.state_file_path.exists():
            return
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            self.open_paper_positions.clear()
            for key, pos in state_data.items():
                parts = key.split("::")
                if len(parts) == 2:
                    strat_id, pair_name = parts[0], parts[1]
                    self.open_paper_positions[(strat_id, pair_name)] = pos
            logger.info(f"💾 Restored {len(self.open_paper_positions)} open paper positions from state file.")
        except Exception as e:
            logger.error(f"Error restoring position state from {self.state_file_path}: {e}")

    def update_health(self, last_error: Optional[str] = None):
        """Emits live runner heartbeat and health status to JSON."""
        if last_error:
            self.last_error = last_error

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        open_pos_summary = []
        for (strat_id, pair_name), pos in self.open_paper_positions.items():
            open_pos_summary.append({
                "strategy_id": strat_id,
                "pair": pair_name,
                "side": pos.get("side"),
                "entry_time": pos.get("entry_time"),
                "z_entry": pos.get("z_entry"),
                "position_id": pos.get("position_id")
            })

        health_data = {
            "last_heartbeat": now_utc,
            "last_market_timestamp": self.last_market_timestamp_str,
            "strategies_loaded": list(self.adapters.keys()),
            "open_positions": {
                "count": len(self.open_paper_positions),
                "details": open_pos_summary
            },
            "trades_closed_by_strategy": self.trades_closed_by_strategy,
            "last_signal_by_strategy": self.last_signal_by_strategy,
            "last_error": self.last_error,
            "runner_pid": os.getpid(),
            "status": "RUNNING_FORWARD_PAPER",
            "watchdog_status": self.watchdog_status,
            "paper_balance": round(self.paper_balance, 2)
        }

        with open(self.health_file_path, "w", encoding="utf-8") as f:
            json.dump(health_data, f, indent=2)

    def fetch_klines_1h(self, symbol: str, limit: int = 750) -> pd.DataFrame:
        """Fetches latest klines from Binance Testnet or public klines."""
        if not self.client:
            return pd.DataFrame()
        try:
            raw = self.client.klines(symbol=symbol, interval='1h', limit=limit)
            if not raw: return pd.DataFrame()
            df = pd.DataFrame(raw, columns=[
                't', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qv', 'tr', 'tb', 'tq', 'ig'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Record last market candle timestamp
            last_ts_ms = df['t'].iloc[-1]
            last_dt = datetime.fromtimestamp(last_ts_ms / 1000.0, tz=timezone.utc)
            self.last_market_timestamp_str = last_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            self.last_market_timestamp_unix = last_ts_ms / 1000.0
            
            return df
        except Exception as e:
            self.last_error = f"Fetch klines error ({symbol}): {e}"
            logger.warning(self.last_error)
            return pd.DataFrame()

    def check_market_data_freshness(self) -> bool:
        """Watchdog: Checks if latest candle is within 30 minutes threshold."""
        # For 1H candle, the candle start time is up to 60m ago. We allow up to 90 min (1 candle + 30m buffer)
        elapsed_sec = time.time() - self.last_market_timestamp_unix
        if elapsed_sec > 5400.0:  # > 90 minutes from last candle open
            self.watchdog_status = f"STALE_DATA_HALT (Latency: {elapsed_sec/60:.1f}m > 90m)"
            logger.warning(f"🛑 [WATCHDOG ALERT] {self.watchdog_status}")
            return False
        self.watchdog_status = "OK"
        return True

    def process_pair_market_data(
        self,
        strategy_id: str,
        pair_name: str,
        df_y: pd.DataFrame,
        df_x: pd.DataFrame,
        df_btc: pd.DataFrame,
        current_time_str: Optional[str] = None,
        current_timestamp: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates signals and processes position transitions for a given strategy and pair.
        """
        adapter = self.adapters.get(strategy_id)
        if not adapter:
            raise KeyError(f"Strategy adapter for {strategy_id} not registered.")

        if df_y.empty or df_x.empty:
            return None

        pos_key = (strategy_id, pair_name)
        open_pos = self.open_paper_positions.get(pos_key)
        now_ts = current_timestamp or int(time.time())
        now_str = current_time_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        bars_held = (now_ts - open_pos['entry_timestamp']) // 3600 if open_pos else 0

        signal = adapter.engine.generate_pair_signal(df_y, df_x, pair_name, df_btc, open_pos, bars_held)

        if not signal:
            return None

        action = signal.get('action')
        curr_y = float(df_y.iloc[-1]['close'])
        curr_x = float(df_x.iloc[-1]['close'])
        gamma = float(signal.get('gamma', open_pos.get('gamma', 1.0) if open_pos else 1.0))
        z_score = float(signal.get('z_score', 0.0))
        reason = str(signal.get('reason', 'N/A'))

        self.last_signal_by_strategy[strategy_id] = {
            "pair": pair_name,
            "action": action,
            "z_score": round(z_score, 2),
            "timestamp": now_str,
            "reason": reason
        }

        # 1. Position Entry (Guarded by Watchdog)
        if action in ['OPEN_LONG_SPREAD', 'OPEN_SHORT_SPREAD'] and pos_key not in self.open_paper_positions:
            if not self.check_market_data_freshness():
                logger.warning(f"🛑 [WATCHDOG BLOCKED ENTRY] Skipping entry for {pair_name} due to stale market data.")
                return None

            pos_id = f"pos_{strategy_id[:6]}_{pair_name.replace('/', '_')}_{now_ts}"
            entry_fee = self.notional_per_leg * 2 * 0.0004

            self.open_paper_positions[pos_key] = {
                'position_id': pos_id,
                'strategy_id': strategy_id,
                'pair': pair_name,
                'side': action.replace('OPEN_', ''),
                'entry_y': curr_y,
                'entry_x': curr_x,
                'gamma': gamma,
                'z_entry': z_score,
                'entry_time': now_str,
                'entry_timestamp': now_ts,
                'entry_fee': entry_fee,
                'reason': reason
            }
            self.save_position_state()

            # Log OPEN Event to CSV
            with open(self.csv_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{now_str},{strategy_id},{pair_name},{action},{curr_y:.4f},{curr_x:.4f},"
                    f"0.00,{entry_fee:.2f},{pos_id},{gamma:.4f},{z_score:.2f},0.00,0,{self.paper_balance:.2f},{reason}\n"
                )

            logger.info(f"🚀 [PAPER OPEN] [{strategy_id}] {pair_name} -> {action} | Z={z_score:.2f} | Gamma={gamma:.4f}")
            self.update_health()
            return {"type": "OPEN", "strategy_id": strategy_id, "pair": pair_name, "signal": signal}

        # 2. Position Exit
        elif action == 'CLOSE_PAIR' and pos_key in self.open_paper_positions:
            pos = self.open_paper_positions[pos_key]
            pos_id = pos.get('position_id', f"pos_{strategy_id}_{now_ts}")
            qty_y = self.notional_per_leg / pos['entry_y']
            qty_x = (self.notional_per_leg * pos['gamma']) / pos['entry_x']

            if pos['side'] == 'SHORT_SPREAD':
                pnl_y = (pos['entry_y'] - curr_y) * qty_y
                pnl_x = (curr_x - pos['entry_x']) * qty_x
            else:
                pnl_y = (curr_y - pos['entry_y']) * qty_y
                pnl_x = (pos['entry_x'] - curr_x) * qty_x

            gross_pnl = pnl_y + pnl_x
            total_notional = (self.notional_per_leg + self.notional_per_leg * pos['gamma']) * 2
            fees = total_notional * 0.0004
            net_pnl = gross_pnl - fees
            self.paper_balance += net_pnl

            # Log CLOSE Event to CSV
            with open(self.csv_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{now_str},{strategy_id},{pair_name},CLOSE,{pos['entry_y']:.4f},{curr_y:.4f},"
                    f"{net_pnl:.2f},{fees:.2f},{pos_id},{pos['gamma']:.4f},{pos['z_entry']:.2f},{z_score:.2f},{bars_held},{self.paper_balance:.2f},{reason}\n"
                )

            logger.info(f"🏁 [PAPER CLOSE] [{strategy_id}] {pair_name} | Net PnL: ${net_pnl:+.2f} USD | Reason: {reason}")
            del self.open_paper_positions[pos_key]
            self.trades_closed_by_strategy[strategy_id] = self.trades_closed_by_strategy.get(strategy_id, 0) + 1
            self.save_position_state()
            self.update_health()
            return {
                "type": "CLOSE",
                "strategy_id": strategy_id,
                "pair": pair_name,
                "net_pnl": net_pnl,
                "reason": reason
            }

        return None

    def run_paper_cycle(self):
        """Runs a single live pulse across all loaded strategies and monitored pairs."""
        logger.info(f"📊 [PULSO PAPER MULTI-STRATEGY] Balance: ${self.paper_balance:.2f} USD | Posiciones: {len(self.open_paper_positions)} | Estrategias: {len(self.adapters)}")
        
        df_btc = self.fetch_klines_1h('BTCUSDT', limit=750)
        
        for strat_id in self.adapters.keys():
            for sym_y, sym_x in self.monitored_pairs:
                pair_name = f"{sym_y}/{sym_x}"
                df_y = self.fetch_klines_1h(sym_y, limit=750)
                df_x = self.fetch_klines_1h(sym_x, limit=750)
                
                if df_y.empty or df_x.empty:
                    continue
                
                self.process_pair_market_data(strat_id, pair_name, df_y, df_x, df_btc)

        self.update_health()

    def run_continuous(self, poll_interval_sec: int = 60, max_iterations: Optional[int] = None):
        """Runs continuous forward paper loop."""
        logger.info(f"🚀 [FORWARD PAPER RUNNER DAEMON START] PID={os.getpid()} | Polling every {poll_interval_sec}s")
        iterations = 0
        while True:
            try:
                self.run_paper_cycle()
                iterations += 1
                if max_iterations and iterations >= max_iterations:
                    logger.info(f"Target iterations ({max_iterations}) completed. Exiting loop.")
                    break
                time.sleep(poll_interval_sec)
            except KeyboardInterrupt:
                logger.info("Runner stopped by user.")
                break
            except Exception as e:
                self.last_error = f"Runner loop exception: {e}"
                logger.error(self.last_error)
                self.update_health(self.last_error)
                time.sleep(10)


if __name__ == '__main__':
    runner = PairsTradingPaperRunner()
    runner.run_continuous(poll_interval_sec=60)
