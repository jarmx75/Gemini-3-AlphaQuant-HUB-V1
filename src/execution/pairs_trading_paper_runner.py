"""
Pairs Trading Autonomous Paper Runner (Hardened with RegimeFilter)
100% Paper Trading Simulation Mode:
  - Lee precios en tiempo real de Binance Futures.
  - Aplica RegimeFilter (BTC -20% en 30d y Correlación 30d < 0.60).
  - Cierra obligatoriamente a las 24h (Time-Stop).
  - Imprime alertas formateadas en consola y registra en logs/paper/bitacora_pairs_trading_paper.csv.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent.parent))
from binance.um_futures import UMFutures
from src.strategies.pairs_trading_stat_arb import PairsTradingStatArb

# Directorio de logs
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

class PairsTradingPaperRunner:
    """Ejecutor 100% Paper Trading con Protección de Régimen."""
    
    def __init__(self, initial_paper_balance: float = 5000.0):
        load_dotenv()
        self.client = UMFutures(
            key=os.getenv('BINANCE_TEST_KEY', ''),
            secret=os.getenv('BINANCE_TEST_SECRET', ''),
            base_url='https://testnet.binancefuture.com'
        )
        self.engine = PairsTradingStatArb(
            lookback_window=90,
            z_entry=2.5,
            z_exit=0.0,
            z_stop=3.5,
            max_holding_bars=24,
            adf_p_threshold=0.05
        )
        
        self.monitored_pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        
        self.paper_balance = initial_paper_balance
        self.notional_per_leg = 150.0  # $150 por pata ($300 total)
        self.fee_rate_roundtrip = 0.0016 # 0.16% total en 2 patas
        self.open_paper_positions = {}
        self.csv_log_path = Path("logs/paper/bitacora_pairs_trading_paper.csv")
        self.init_csv()

    def init_csv(self):
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write("entry_time,exit_time,pair,side,entry_y,exit_y,entry_x,exit_x,gamma,z_entry,z_exit,holding_bars,gross_pnl,fees,net_pnl,paper_balance,reason\n")

    def fetch_klines_1h(self, symbol: str, limit: int = 750) -> pd.DataFrame:
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
            return pd.DataFrame()

    def run_paper_cycle(self):
        """Ejecuta un ciclo de evaluación y emisión de alertas en consola y CSV."""
        logger.info(f"📊 [PULSO PAPER TRADING] Balance Virtual: ${self.paper_balance:.2f} USD | Posiciones Abiertas: {len(self.open_paper_positions)}")
        
        df_btc = self.fetch_klines_1h('BTCUSDT', limit=750)
        
        for sym_y, sym_x in self.monitored_pairs:
            pair_name = f"{sym_y}/{sym_x}"
            df_y = self.fetch_klines_1h(sym_y, limit=750)
            df_x = self.fetch_klines_1h(sym_x, limit=750)
            
            if df_y.empty or df_x.empty:
                continue
                
            open_pos = self.open_paper_positions.get(pair_name)
            bars_held = (int(time.time()) - open_pos['entry_timestamp']) // 3600 if open_pos else 0
            
            signal = self.engine.generate_pair_signal(df_y, df_x, pair_name, df_btc, open_pos, bars_held)
            
            if signal:
                action = signal['action']
                curr_y = df_y.iloc[-1]['close']
                curr_x = df_x.iloc[-1]['close']
                gamma = signal.get('gamma', open_pos.get('gamma', 1.0) if open_pos else 1.0)
                
                if action in ['OPEN_LONG_SPREAD', 'OPEN_SHORT_SPREAD'] and pair_name not in self.open_paper_positions:
                    self.open_paper_positions[pair_name] = {
                        'pair': pair_name,
                        'side': action.replace('OPEN_', ''),
                        'entry_y': curr_y,
                        'entry_x': curr_x,
                        'gamma': gamma,
                        'z_entry': signal['z_score'],
                        'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'entry_timestamp': int(time.time()),
                        'reason': signal['reason']
                    }
                    print("\n" + "=" * 80)
                    print(f"🚀 [ALERTA PAPER: APERTURA] {pair_name} -> {action}")
                    print(f"   • Z-Score: {signal['z_score']:.2f} | Gamma: {gamma:.4f}")
                    print(f"   • Razón:   {signal['reason']}")
                    print("=" * 80 + "\n")
                    logger.info(f"📝 [PAPER OPEN] {pair_name} | {action} | Z={signal['z_score']:.2f}")
                    
                elif action == 'CLOSE_PAIR' and pair_name in self.open_paper_positions:
                    pos = self.open_paper_positions[pair_name]
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
                    
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(self.csv_log_path, "a", encoding="utf-8") as f:
                        f.write(f"{pos['entry_time']},{now_str},{pair_name},{pos['side']},{pos['entry_y']:.4f},{curr_y:.4f},{pos['entry_x']:.4f},{curr_x:.4f},{pos['gamma']:.4f},{pos['z_entry']:.2f},{signal['z_score']:.2f},{bars_held},{gross_pnl:.2f},{fees:.2f},{net_pnl:.2f},{self.paper_balance:.2f},{signal['reason']}\n")
                        
                    print("\n" + "=" * 80)
                    print(f"🛑 [ALERTA PAPER: CIERRE] {pair_name} -> {signal['reason']}")
                    print(f"   • Net PnL: ${net_pnl:+.2f} USD (Fees: -${fees:.2f}) | Balance: ${self.paper_balance:.2f} USD")
                    print("=" * 80 + "\n")
                    logger.info(f"🏁 [PAPER CLOSE] {pair_name} | Net PnL: ${net_pnl:+.2f} USD | Razón: {signal['reason']}")
                    del self.open_paper_positions[pair_name]

if __name__ == '__main__':
    runner = PairsTradingPaperRunner()
    runner.run_paper_cycle()
