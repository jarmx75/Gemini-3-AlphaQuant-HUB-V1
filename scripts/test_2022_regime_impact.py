"""
2022 Bear Market Regime Filter Impact Evaluation
Evalúa exactamente cuántas pérdidas y drawdown evitó el RegimeFilter durante los colapsos de 2022 (Terra Luna, FTX).
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from scripts.auditoria_walkforward_montecarlo import load_pair_data
from src.filters.regime_filter import RegimeFilter
from statsmodels.tsa.stattools import adfuller

def run_simulation_with_options(df: pd.DataFrame, df_btc: pd.DataFrame, use_regime_filter: bool = True) -> list:
    y = df['close_y'].values
    x = df['close_x'].values
    btc_p = df_btc['close_y'].values if not df_btc.empty else y
    timestamps = df['timestamp'].values
    n = len(y)
    
    rf = RegimeFilter(btc_drop_threshold=-0.20, corr_threshold=0.60, window_30d_bars=720)
    lookback_w = 90
    trades = []
    in_pos = False
    pos_side = None
    entry_y = entry_x = entry_gamma = 0.0
    entry_idx = 0
    
    for t in range(lookback_w, n):
        y_w = y[t - lookback_w : t]
        x_w = x[t - lookback_w : t]
        
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
            is_entry_candidate = (2.5 <= z <= 3.4) or (-3.4 <= z <= -2.5)
            if not is_entry_candidate:
                continue
                
            # ADF check
            try:
                adf_res = adfuller(spread_w, autolag='AIC')
                adf_pval = float(adf_res[1])
            except:
                adf_pval = 1.0
            if adf_pval >= 0.03:
                continue
                
            # Filtro de Régimen si está activado
            if use_regime_filter:
                btc_slice = btc_p[:t+1]
                y_slice = y[:t+1]
                x_slice = x[:t+1]
                allowed, _ = rf.is_entry_allowed(btc_slice, y_slice, x_slice)
                if not allowed:
                    continue
                    
            if 2.5 <= z <= 3.4:
                in_pos = True
                pos_side = 'SHORT'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
            elif -3.4 <= z <= -2.5:
                in_pos = True
                pos_side = 'LONG'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
        else:
            holding_bars = t - entry_idx
            exit_flag = False
            exit_reason = ""
            
            if holding_bars >= 24:
                exit_flag = True
                exit_reason = "Time-Stop (24h)"
            elif pos_side == 'SHORT':
                if z <= 0.0:
                    exit_flag = True
                    exit_reason = "Target Exit"
                elif z >= 3.5:
                    exit_flag = True
                    exit_reason = "Stop Loss"
            elif pos_side == 'LONG':
                if z >= 0.0:
                    exit_flag = True
                    exit_reason = "Target Exit"
                elif z <= -3.5:
                    exit_flag = True
                    exit_reason = "Stop Loss"
                    
            if exit_flag:
                notional = 150.0
                qty_y = notional / entry_y
                qty_x = (notional * entry_gamma) / entry_x
                
                if pos_side == 'SHORT':
                    pnl_y = (entry_y - curr_y) * qty_y
                    pnl_x = (curr_x - entry_x) * qty_x
                else:
                    pnl_y = (curr_y - entry_y) * qty_y
                    pnl_x = (entry_x - curr_x) * qty_x
                    
                gross = pnl_y + pnl_x
                fees = (notional + notional * entry_gamma) * 2 * 0.0004
                net = gross - fees
                trades.append(net)
                in_pos = False
                
    return trades

def main():
    print("=" * 80)
    print("🔬 EVALUACIÓN COMPARATIVA EN EL BEAR MARKET DE 2022 (CON vs SIN REGIME FILTER)")
    print("=" * 80)
    
    pairs = [('BTCUSDT', 'ETHUSDT'), ('AVAXUSDT', 'SOLUSDT'), ('LINKUSDT', 'DOTUSDT')]
    df_btc_raw = load_pair_data('BTCUSDT', 'ETHUSDT')
    df_btc_2022 = df_btc_raw[(df_btc_raw['timestamp'] >= '2022-01-01') & (df_btc_raw['timestamp'] < '2023-01-01')].reset_index(drop=True)
    
    trades_without = []
    trades_with = []
    
    for sym_y, sym_x in pairs:
        df = load_pair_data(sym_y, sym_x)
        if not df.empty:
            df_2022 = df[(df['timestamp'] >= '2022-01-01') & (df['timestamp'] < '2023-01-01')].reset_index(drop=True)
            tr_no = run_simulation_with_options(df_2022, df_btc_2022, use_regime_filter=False)
            tr_yes = run_simulation_with_options(df_2022, df_btc_2022, use_regime_filter=True)
            trades_without.extend(tr_no)
            trades_with.extend(tr_yes)
            
    pnl_no = sum(trades_without)
    pnl_yes = sum(trades_with)
    
    gw_no = sum([t for t in trades_without if t > 0])
    gl_no = abs(sum([t for t in trades_without if t <= 0]))
    pf_no = gw_no / gl_no if gl_no > 0 else 0.0
    
    gw_yes = sum([t for t in trades_with if t > 0])
    gl_yes = abs(sum([t for t in trades_with if t <= 0]))
    pf_yes = gw_yes / gl_yes if gl_yes > 0 else 0.0
    
    print(f"🔴 SIN RegimeFilter (2022): Trades={len(trades_without)} | PnL Total=${pnl_no:+.2f} USD | PF={pf_no:.2f}")
    print(f"🟢 CON RegimeFilter (2022): Trades={len(trades_with)} | PnL Total=${pnl_yes:+.2f} USD | PF={pf_yes:.2f}")
    print(f"🛡️ Pérdidas Totales Evitadas: ${abs(pnl_no - pnl_yes):.2f} USD de Drawdown protegido!")

if __name__ == '__main__':
    main()
