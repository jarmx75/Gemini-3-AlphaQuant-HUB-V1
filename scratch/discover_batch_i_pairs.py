"""
Phase 1 Discovery Script for Batch I: Universe Expansion
Analyzes 12 remaining candidate pairs on TRAIN 2022-2023 ONLY.
NO OOS DATA IS ACCESSED DURING DISCOVERY.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from statsmodels.tsa.stattools import adfuller

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical"

ASSETS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
EXISTING_PAIRS = {('BTCUSDT', 'ETHUSDT'), ('AVAXUSDT', 'SOLUSDT'), ('LINKUSDT', 'DOTUSDT')}

CANDIDATE_PAIRS = []
for i in range(len(ASSETS)):
    for j in range(i + 1, len(ASSETS)):
        p = (ASSETS[i], ASSETS[j])
        if p not in EXISTING_PAIRS and (p[1], p[0]) not in EXISTING_PAIRS:
            CANDIDATE_PAIRS.append(p)


def load_train_data(sym_y: str, sym_x: str) -> pd.DataFrame:
    file_y = DATA_DIR / f"{sym_y}_1h_2022_2026.csv"
    file_x = DATA_DIR / f"{sym_x}_1h_2022_2026.csv"
    btc_file = DATA_DIR / "BTCUSDT_1h_2022_2026.csv"

    df_y = pd.read_csv(file_y)[['timestamp', 'close']].rename(columns={'close': 'close_y'})
    df_x = pd.read_csv(file_x)[['timestamp', 'close']].rename(columns={'close': 'close_x'})
    df_btc = pd.read_csv(btc_file)[['timestamp', 'close']].rename(columns={'close': 'close_btc'})

    df_y['timestamp'] = pd.to_datetime(df_y['timestamp'])
    df_x['timestamp'] = pd.to_datetime(df_x['timestamp'])
    df_btc['timestamp'] = pd.to_datetime(df_btc['timestamp'])

    df_merged = pd.merge(df_y, df_x, on='timestamp').sort_values('timestamp').reset_index(drop=True)
    df_merged = pd.merge(df_merged, df_btc, on='timestamp').sort_values('timestamp').reset_index(drop=True)

    df_merged['btc_ret_30d'] = df_merged['close_btc'].pct_change(720).fillna(0.0)
    df_merged['corr_30d'] = df_merged['close_y'].rolling(720).corr(df_merged['close_x']).fillna(1.0)

    # Filter STRICTLY for TRAIN: 2022-01-01 to 2023-12-31 23:00:00
    df_train = df_merged[(df_merged['timestamp'] >= '2022-01-01') & (df_merged['timestamp'] < '2024-01-01')].reset_index(drop=True)
    return df_train


def simulate_train_pair(
    df_train: pd.DataFrame,
    lookback_window: int = 90,
    z_entry: float = 2.5,
    z_exit: float = 0.0,
    z_stop: float = 3.5,
    max_holding_bars: int = 24,
    adf_threshold: float = 0.05,
    notional: float = 150.0
) -> Dict[str, Any]:
    w = lookback_window
    y = df_train['close_y'].values
    x = df_train['close_x'].values
    btc_ret_30d = df_train['btc_ret_30d'].values
    corr_30d = df_train['corr_30d'].values
    n = len(y)

    trades = []
    in_pos = False
    pos_side = None
    entry_y = entry_x = entry_gamma = 0.0
    entry_idx = 0

    raw_signals = 0
    adf_passed = 0

    for t in range(w, n):
        y_w = y[t-w : t]
        x_w = x[t-w : t]

        cov = np.cov(x_w, y_w)[0, 1]
        var = np.var(x_w)
        if var == 0:
            continue
        gamma = cov / var

        spread_w = y_w - gamma * x_w
        mean_s = np.mean(spread_w)
        std_s = np.std(spread_w)
        if std_s == 0:
            continue

        curr_y = y[t]
        curr_x = x[t]
        curr_s = curr_y - gamma * curr_x
        z = (curr_s - mean_s) / std_s

        if not in_pos:
            is_z = (z_entry <= z <= z_entry + 0.9) or (-(z_entry + 0.9) <= z <= -z_entry)
            is_regime = not (btc_ret_30d[t] <= -0.20 or corr_30d[t] < 0.60)

            if is_z and is_regime:
                raw_signals += 1
                try:
                    adf_res = adfuller(spread_w, autolag='AIC')
                    if adf_res[1] < adf_threshold:
                        adf_passed += 1
                        if z_entry <= z <= z_entry + 0.9:
                            in_pos = True
                            pos_side = 'SHORT'
                            entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
                        elif -(z_entry + 0.9) <= z <= -z_entry:
                            in_pos = True
                            pos_side = 'LONG'
                            entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
                except Exception:
                    pass
        else:
            holding = t - entry_idx
            exit_flag = False

            if holding >= max_holding_bars:
                exit_flag = True
            elif pos_side == 'SHORT':
                if z <= z_exit or z >= z_stop:
                    exit_flag = True
            elif pos_side == 'LONG':
                if z >= -z_exit or z <= -z_stop:
                    exit_flag = True

            if exit_flag:
                qty_y = notional / entry_y
                qty_x = qty_y * entry_gamma

                if pos_side == 'SHORT':
                    pnl_y = (entry_y - curr_y) * qty_y
                    pnl_x = (curr_x - entry_x) * qty_x
                else:
                    pnl_y = (curr_y - entry_y) * qty_y
                    pnl_x = (entry_x - curr_x) * qty_x

                gross_pnl = pnl_y + pnl_x
                notional_y = qty_y * entry_y
                notional_x = qty_x * entry_x
                fees = (notional_y + notional_x) * 2 * 0.0004
                net_pnl = gross_pnl - fees
                trades.append({'net_pnl': net_pnl, 'holding': holding})
                in_pos = False

    # Metrics
    df_tr = pd.DataFrame(trades) if trades else pd.DataFrame(columns=['net_pnl', 'holding'])
    if not df_tr.empty:
        wins = df_tr[df_tr['net_pnl'] > 0]
        losses = df_tr[df_tr['net_pnl'] <= 0]
        gw = wins['net_pnl'].sum() if not wins.empty else 0.0
        gl = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
        pf = gw / gl
        wr = (len(wins) / len(df_tr)) * 100.0
        net_pnl = df_tr['net_pnl'].sum()
        exp = df_tr['net_pnl'].mean()
        equity = 5000.0 + df_tr['net_pnl'].cumsum()
        peak = equity.cummax()
        dd = ((peak - equity).max() / 5000.0) * 100.0
    else:
        pf, wr, net_pnl, exp, dd = 0.0, 0.0, 0.0, 0.0, 0.0

    mean_corr = df_train['corr_30d'].mean()

    return {
        'total_bars': n,
        'mean_corr_30d': round(mean_corr, 2),
        'raw_signals': raw_signals,
        'adf_passed_signals': adf_passed,
        'adf_pass_rate_pct': round((adf_passed / raw_signals * 100.0) if raw_signals > 0 else 0.0, 1),
        'train_trades': len(trades),
        'train_pf': round(pf, 2),
        'train_wr': round(wr, 1),
        'train_net_pnl': round(net_pnl, 2),
        'train_exp': round(exp, 2),
        'train_dd': round(dd, 2)
    }


def main():
    print(f"Discovery Phase 1: Evaluating {len(CANDIDATE_PAIRS)} pairs strictly on TRAIN (2022-2023)...")
    results = []

    for sym_y, sym_x in CANDIDATE_PAIRS:
        pair_str = f"{sym_y}/{sym_x}"
        df_train = load_train_data(sym_y, sym_x)
        res = simulate_train_pair(df_train)
        res['pair'] = pair_str
        results.append(res)

    df_res = pd.DataFrame(results)

    # Ranking score based strictly on Train criteria:
    # 1. High stability / correlation (>0.60)
    # 2. Number of valid trades and signals
    # 3. ADF pass rate and statistical validity
    df_res['rank_score'] = (
        df_res['train_trades'] * 1.5 +
        df_res['adf_passed_signals'] * 1.0 +
        df_res['mean_corr_30d'] * 20.0 +
        np.clip(df_res['train_pf'], 0, 3) * 15.0
    )
    df_res = df_res.sort_values(by='rank_score', ascending=False).reset_index(drop=True)

    print("\n" + "="*140)
    print("BATCH I: DISCOVERY RANKING (TRAIN 2022-2023 ONLY - ZERO OOS ACCESS)")
    print("="*140)
    cols = ['pair', 'total_bars', 'mean_corr_30d', 'raw_signals', 'adf_passed_signals', 'adf_pass_rate_pct', 'train_trades', 'train_pf', 'train_wr', 'train_net_pnl', 'train_exp', 'train_dd', 'rank_score']
    print(df_res[cols].to_string(index=False))
    print("="*140)

    top_5 = df_res.head(5)['pair'].tolist()
    print(f"\n🎯 Top 5 Selected Pairs based STRICTLY on TRAIN criteria:\n")
    for i, p in enumerate(top_5, 1):
        print(f"  {i}. {p}")


if __name__ == '__main__':
    main()
