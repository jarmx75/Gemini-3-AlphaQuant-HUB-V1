"""
Pairs Trading Autonomous Multi-Strategy Paper Runner (Hardened with RegimeFilter)
100% Paper Trading Simulation Mode:
  - Reads all active PAPER_ACTIVE strategies from registry.json / live_candidates.
  - Instantiates individual strategy engine adapters for each strategy.
  - Evaluates real-time / test klines for all monitored pairs.
  - Tracks open paper positions separately per (strategy_id, pair_name).
  - Logs completed paper trades with strategy_id to logs/paper/bitacora_pairs_trading_paper.csv.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.strategies.pairs_trading_stat_arb import PairsTradingStatArb

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Logging Directory
log_dir = Path("logs/paper")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/paper/historial_pairs_paper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"
LIVE_CANDIDATES_DIR = PROJECT_ROOT / "src" / "strategies" / "live_candidates"
CSV_LOG_PATH = log_dir / "bitacora_pairs_trading_paper.csv"


class StrategyAdapter:
    """Executable adapter for a specific strategy candidate."""
    def __init__(self, config: Dict[str, Any]):
        self.strategy_id = config.get("id", "UNKNOWN")
        self.family = config.get("family", "MEAN_REVERSION_1H")
        self.lookback_window = config.get("lookback_window", 90)
        self.z_entry = config.get("z_entry", 2.5)
        self.z_exit = config.get("z_exit", 0.0)
        self.z_stop = config.get("z_stop", 3.5)
        self.max_holding_bars = config.get("max_holding_bars", 24)
        self.adf_p_threshold = config.get("adf_p_threshold", 0.05)
        
        self.engine = PairsTradingStatArb(
            lookback_window=self.lookback_window,
            z_entry=self.z_entry,
            z_exit=self.z_exit,
            z_stop=self.z_stop,
            max_holding_bars=self.max_holding_bars,
            adf_p_threshold=self.adf_p_threshold
        )


class PairsTradingPaperRunner:
    """Multi-Strategy Paper Trading Orchestrator."""
    
    def __init__(self, initial_paper_balance: float = 5000.0, use_binance_client: bool = True):
        load_dotenv()
        self.use_binance = use_binance_client
        self.client = None
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
        
        # Open positions indexed by (strategy_id, pair_name)
        self.open_paper_positions: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.csv_log_path = CSV_LOG_PATH
        
        # Load and instantiate adapters for all active strategies
        self.adapters: Dict[str, StrategyAdapter] = {}
        self.load_active_strategy_adapters()
        self.init_csv()

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
            if strat_id:
                adapter = StrategyAdapter(s)
                self.adapters[strat_id] = adapter
                logger.info(f"Loaded paper adapter for strategy: {strat_id} (z_entry={adapter.z_entry}, window={adapter.lookback_window})")

    def init_csv(self):
        """Initializes paper trades CSV log with strategy_id column."""
        header = "strategy_id,entry_time,exit_time,pair,side,entry_y,exit_y,entry_x,exit_x,gamma,z_entry,z_exit,holding_bars,gross_pnl,fees,net_pnl,paper_balance,reason\n"
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write(header)
        else:
            # Check if header has strategy_id
            with open(self.csv_log_path, "r", encoding="utf-8") as f:
                first_line = f.readline()
            if "strategy_id" not in first_line:
                # Upgrade legacy format
                with open(self.csv_log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(self.csv_log_path, "w", encoding="utf-8") as f:
                    f.write(header)
                    # Re-write existing rows with default strategy id if any
                    lines = content.strip().split("\n")[1:]
                    for line in lines:
                        if line.strip():
                            f.write(f"Pairs_Stat_Arb_Base,{line}\n")

    def fetch_klines_1h(self, symbol: str, limit: int = 750) -> pd.DataFrame:
        """Fetches klines from Binance Testnet."""
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
            return df
        except Exception as e:
            logger.warning(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()

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
        Processes market data for a given strategy and pair.
        Returns signal dict if generated, or executed trade dict if closed.
        """
        adapter = self.adapters.get(strategy_id)
        if not adapter:
            raise KeyError(f"Strategy adapter for {strategy_id} not registered.")

        if df_y.empty or df_x.empty:
            return None

        pos_key = (strategy_id, pair_name)
        open_pos = self.open_paper_positions.get(pos_key)
        now_ts = current_timestamp or int(time.time())
        now_str = current_time_str or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        bars_held = (now_ts - open_pos['entry_timestamp']) // 3600 if open_pos else 0

        signal = adapter.engine.generate_pair_signal(df_y, df_x, pair_name, df_btc, open_pos, bars_held)

        if not signal:
            return None

        action = signal.get('action')
        curr_y = float(df_y.iloc[-1]['close'])
        curr_x = float(df_x.iloc[-1]['close'])
        gamma = float(signal.get('gamma', open_pos.get('gamma', 1.0) if open_pos else 1.0))

        # 1. Position Entry
        if action in ['OPEN_LONG_SPREAD', 'OPEN_SHORT_SPREAD'] and pos_key not in self.open_paper_positions:
            self.open_paper_positions[pos_key] = {
                'strategy_id': strategy_id,
                'pair': pair_name,
                'side': action.replace('OPEN_', ''),
                'entry_y': curr_y,
                'entry_x': curr_x,
                'gamma': gamma,
                'z_entry': signal['z_score'],
                'entry_time': now_str,
                'entry_timestamp': now_ts,
                'reason': signal['reason']
            }
            logger.info(f"🚀 [PAPER OPEN] [{strategy_id}] {pair_name} -> {action} | Z={signal['z_score']:.2f} | Gamma={gamma:.4f}")
            return {"type": "OPEN", "strategy_id": strategy_id, "pair": pair_name, "signal": signal}

        # 2. Position Exit
        elif action == 'CLOSE_PAIR' and pos_key in self.open_paper_positions:
            pos = self.open_paper_positions[pos_key]
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

            # Log to CSV
            with open(self.csv_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"{strategy_id},{pos['entry_time']},{now_str},{pair_name},{pos['side']},"
                    f"{pos['entry_y']:.4f},{curr_y:.4f},{pos['entry_x']:.4f},{curr_x:.4f},"
                    f"{pos['gamma']:.4f},{pos['z_entry']:.2f},{signal['z_score']:.2f},{bars_held},"
                    f"{gross_pnl:.2f},{fees:.2f},{net_pnl:.2f},{self.paper_balance:.2f},{signal['reason']}\n"
                )

            logger.info(f"🏁 [PAPER CLOSE] [{strategy_id}] {pair_name} | Net PnL: ${net_pnl:+.2f} USD | Reason: {signal['reason']}")
            del self.open_paper_positions[pos_key]
            return {
                "type": "CLOSE",
                "strategy_id": strategy_id,
                "pair": pair_name,
                "net_pnl": net_pnl,
                "reason": signal['reason']
            }

        return None

    def run_paper_cycle(self):
        """Runs a complete live pulse across all strategies and pairs."""
        logger.info(f"📊 [PULSO PAPER MULTI-STRATEGY] Balance: ${self.paper_balance:.2f} USD | Posiciones Abiertas: {len(self.open_paper_positions)} | Estrategias: {len(self.adapters)}")
        
        df_btc = self.fetch_klines_1h('BTCUSDT', limit=750)
        
        for strat_id in self.adapters.keys():
            for sym_y, sym_x in self.monitored_pairs:
                pair_name = f"{sym_y}/{sym_x}"
                df_y = self.fetch_klines_1h(sym_y, limit=750)
                df_x = self.fetch_klines_1h(sym_x, limit=750)
                
                if df_y.empty or df_x.empty:
                    continue
                
                self.process_pair_market_data(strat_id, pair_name, df_y, df_x, df_btc)


if __name__ == '__main__':
    runner = PairsTradingPaperRunner()
    runner.run_paper_cycle()
