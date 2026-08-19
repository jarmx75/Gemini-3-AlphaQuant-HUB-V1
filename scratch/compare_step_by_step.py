"""
Step-by-step forensic comparison of Validator vs PairsTradingStatArb on BTC/ETH (2024-2026)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.factory.validator import FactoryValidator, FactoryCandidate
from src.strategies.pairs_trading_stat_arb import PairsTradingStatArb

def run_comparison():
    v = FactoryValidator()
    cand = FactoryCandidate(
        id='Pairs_Stat_Arb_Base',
        lookback_window=90,
        z_entry=2.5,
        z_exit=0.0,
        z_stop=3.5,
        max_holding_bars=24,
        eg_p_threshold=0.03,
        adf_p_threshold=0.05,
        pairs=[]
    )
    
    df_merged = v.cached_pairs['BTCUSDT/ETHUSDT']
    df_val = df_merged[(df_merged['timestamp'] >= '2024-01-01') & (df_merged['timestamp'] <= '2026-08-16')].reset_index(drop=True)
    
    # 1. Run validator simulate_series with detailed trade records
    w = cand.lookback_window
    y = df_val['close_y'].values
    x = df_val['close_x'].values
    btc_ret_30d = df_val['btc_ret_30d'].values
    corr_30d = df_val['corr_30d'].values
    ts = df_val['timestamp'].values
    n = len(y)

    val_trades = []
    in_pos = False
    pos_side = None
    entry_y = entry_x = entry_gamma = 0.0
    entry_idx = 0

    for t in range(w, n):
        y_w = y[t-w : t]
        x_w = x[t-w : t]
        
        cov = np.cov(x_w, y_w)[0, 1]
        var = np.var(x_w)
        if var == 0: continue
        gamma = cov / var
        
        spread_w = y_w - gamma * x_w
        mean_s = np.mean(spread_w)
        std_s = np.std(spread_w)
        if std_s == 0: continue
        
        curr_y = y[t]
        curr_x = x[t]
        curr_s = curr_y - gamma * curr_x
        z = (curr_s - mean_s) / std_s
        
        if not in_pos:
            if not ((cand.z_entry <= z <= cand.z_entry + 0.9) or (-(cand.z_entry + 0.9) <= z <= -cand.z_entry)):
                continue
                
            # Filtro de Régimen
            if btc_ret_30d[t] <= -0.20 or corr_30d[t] < 0.60:
                continue
                
            # ADF Check
            try:
                adf_res = adfuller(spread_w, autolag='AIC')
                if adf_res[1] >= cand.adf_p_threshold:
                    continue
            except:
                continue
                
            if cand.z_entry <= z <= cand.z_entry + 0.9:
                in_pos = True
                pos_side = 'SHORT'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
            elif -(cand.z_entry + 0.9) <= z <= -cand.z_entry:
                in_pos = True
                pos_side = 'LONG'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
        else:
            holding = t - entry_idx
            exit_flag = False
            exit_reason = None
            
            if holding >= cand.max_holding_bars:
                exit_flag = True
                exit_reason = "Time-Stop"
            elif pos_side == 'SHORT':
                if z <= cand.z_exit or z >= cand.z_stop:
                    exit_flag = True
                    exit_reason = f"Z={z:.2f}"
            elif pos_side == 'LONG':
                if z >= -cand.z_exit or z <= -cand.z_stop:
                    exit_flag = True
                    exit_reason = f"Z={z:.2f}"
                    
            if exit_flag:
                val_trades.append({
                    "entry_idx": entry_idx,
                    "entry_time": str(ts[entry_idx]),
                    "exit_idx": t,
                    "exit_time": str(ts[t]),
                    "side": pos_side,
                    "holding": holding,
                    "exit_reason": exit_reason,
                    "entry_y": entry_y,
                    "exit_y": curr_y
                })
                in_pos = False

    print(f"=== VALIDATOR BTC/ETH 2024-2026: {len(val_trades)} TRADES ===")
    print("First 5 validator trades:")
    for tr in val_trades[:5]:
        print(" ", tr)
    print("Last 5 validator trades:")
    for tr in val_trades[-5:]:
        print(" ", tr)

if __name__ == '__main__':
    run_comparison()
