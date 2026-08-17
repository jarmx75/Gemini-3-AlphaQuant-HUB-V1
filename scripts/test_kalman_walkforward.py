"""
Walk-Forward Evaluation of Kalman Filter Dynamic Stat-Arb
Compara el desempeño del Filtro de Kalman contra la versión Rolling OLS tradicional.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from binance.um_futures import UMFutures
from src.strategies.kalman_stat_arb import KalmanStatArb

load_dotenv()

def run_kalman_simulation(df_y: pd.DataFrame, df_x: pd.DataFrame, notional_per_leg: float = 150.0) -> list:
    y = df_y['close'].values
    x = df_x['close'].values
    n = len(y)
    
    kalman = KalmanStatArb(delta=1e-4, ve=1e-3, z_entry=1.8, z_exit=0.2, z_stop=3.2, half_life_max=35)
    betas, residuals, z_scores = kalman.run_kalman_filter(y, x)
    
    trades = []
    in_pos = False
    pos_side = None
    entry_y = 0.0
    entry_x = 0.0
    entry_beta = 1.0
    entry_idx = 0
    
    for t in range(50, n):
        z = z_scores[t]
        curr_y = y[t]
        curr_x = x[t]
        curr_beta = betas[t]
        
        if not in_pos:
            if 1.8 <= z <= 3.0:
                in_pos = True
                pos_side = 'SHORT_SPREAD'
                entry_y, entry_x, entry_beta = curr_y, curr_x, curr_beta
                entry_idx = t
            elif -3.0 <= z <= -1.8:
                in_pos = True
                pos_side = 'LONG_SPREAD'
                entry_y, entry_x, entry_beta = curr_y, curr_x, curr_beta
                entry_idx = t
        else:
            holding_periods = t - entry_idx
            exit_signal = False
            exit_reason = ""
            
            if pos_side == 'SHORT_SPREAD':
                if z <= 0.2:
                    exit_signal = True
                    exit_reason = "Mean-Reverted (Target)"
                elif z >= 3.2:
                    exit_signal = True
                    exit_reason = "Stop-Loss (Divergence)"
            elif pos_side == 'LONG_SPREAD':
                if z >= -0.2:
                    exit_signal = True
                    exit_reason = "Mean-Reverted (Target)"
                elif z <= -3.2:
                    exit_signal = True
                    exit_reason = "Stop-Loss (Divergence)"
                    
            if holding_periods >= 50:
                exit_signal = True
                exit_reason = "Time-Stop"
                
            if exit_signal:
                qty_y = notional_per_leg / entry_y
                qty_x = (notional_per_leg * entry_beta) / entry_x
                
                if pos_side == 'SHORT_SPREAD':
                    pnl_y = (entry_y - curr_y) * qty_y
                    pnl_x = (curr_x - entry_x) * qty_x
                else:
                    pnl_y = (curr_y - entry_y) * qty_y
                    pnl_x = (entry_x - curr_x) * qty_x
                    
                gross_pnl = pnl_y + pnl_x
                total_notional = (notional_per_leg + notional_per_leg * entry_beta) * 2
                fees = total_notional * 0.0004 # 0.04% por trade Taker
                net_pnl = gross_pnl - fees
                
                trades.append({
                    'side': pos_side,
                    'entry_idx': entry_idx,
                    'exit_idx': t,
                    'holding': holding_periods,
                    'gross_pnl': gross_pnl,
                    'fees': fees,
                    'net_pnl': net_pnl,
                    'reason': exit_reason
                })
                in_pos = False
                
    return trades

def main():
    print("=" * 85)
    print("🔬 TEST WALK-FORWARD: FILTRO DE KALMAN DINÁMICO (STATE-SPACE STAT-ARB)")
    print("=" * 85)
    
    api_key = os.getenv('BINANCE_TEST_KEY')
    secret_key = os.getenv('BINANCE_TEST_SECRET')
    client = UMFutures(key=api_key, secret=secret_key, base_url='https://testnet.binancefuture.com')
    
    pairs = [
        ('BTCUSDT', 'ETHUSDT'),
        ('AVAXUSDT', 'SOLUSDT'),
        ('SUIUSDT', 'APTUSDT'),
        ('LINKUSDT', 'DOTUSDT')
    ]
    
    all_trades = []
    for sym_y, sym_x in pairs:
        raw_y = client.klines(symbol=sym_y, interval='15m', limit=1000)
        raw_x = client.klines(symbol=sym_x, interval='15m', limit=1000)
        df_y = pd.DataFrame(raw_y, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qv', 'tr', 'tb', 'tq', 'ig'])
        df_x = pd.DataFrame(raw_x, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qv', 'tr', 'tb', 'tq', 'ig'])
        df_y['close'] = df_y['close'].astype(float)
        df_x['close'] = df_x['close'].astype(float)
        
        trades = run_kalman_simulation(df_y, df_x)
        all_trades.extend(trades)
        print(f"Par {sym_y}/{sym_x}: {len(trades)} trades generados")
        
    df = pd.DataFrame(all_trades)
    if not df.empty:
        wins = df[df['net_pnl'] > 0]
        losses = df[df['net_pnl'] <= 0]
        wr = len(wins) / len(df) * 100.0
        gross_w = wins['net_pnl'].sum() if not wins.empty else 0.0
        gross_l = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
        pf = gross_w / gross_l
        net_pnl = df['net_pnl'].sum()
        expectancy = df['net_pnl'].mean()
        
        # Max Drawdown
        equity = df['net_pnl'].cumsum()
        dd = (equity.cummax() - equity).max()
        dd_pct = (dd / 4000.0) * 100.0
        
        print("\n" + "=" * 85)
        print("🏆 RESULTADOS GLOBALES FILTRO DE KALMAN (CON COMISIONES 0.16% DEDUCIDAS):")
        print(f"   • Total Trades:     {len(df)}")
        print(f"   • Win Rate:         {wr:.1f}% ({len(wins)} W / {len(losses)} L)")
        print(f"   • Profit Factor:    {pf:.2f}")
        print(f"   • PnL Neto Total:   ${net_pnl:+.2f} USDT")
        print(f"   • Expectancy/Trade: ${expectancy:+.2f} USDT")
        print(f"   • Max Drawdown:     {dd_pct:.2f}% (${dd:.2f} USD)")
        print("=" * 85)

if __name__ == '__main__':
    main()
