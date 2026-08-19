"""
Batch J: Log-Price / Dollar-Neutral Statistical Arbitrage Engine
Evaluates 5 lookback window variants (J1=60, J2=90, J3=120, J4=180, J5=240) across 5 asymmetric pairs:
1. BTCUSDT/DOTUSDT
2. ETHUSDT/DOTUSDT
3. BTCUSDT/SOLUSDT
4. ETHUSDT/AVAXUSDT
5. BTCUSDT/AVAXUSDT

Features:
- Log-price OLS: y = ln(P_y), x = ln(P_x), beta = Cov(x, y) / Var(x)
- Log spread: s_t = ln(y_t) - beta * ln(x_t)
- Dimensionless beta-weighted dollar-neutral sizing: notional_y = $150, notional_x = |beta| * $150
- Zero nominal scale distortion.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from statsmodels.tsa.stattools import adfuller

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical"

PAIRS_J = [
    ('BTCUSDT', 'DOTUSDT'),
    ('ETHUSDT', 'DOTUSDT'),
    ('BTCUSDT', 'SOLUSDT'),
    ('ETHUSDT', 'AVAXUSDT'),
    ('BTCUSDT', 'AVAXUSDT')
]

VARIANTS_J = [
    ('J1', 60),
    ('J2', 90),
    ('J3', 120),
    ('J4', 180),
    ('J5', 240)
]


def load_pair_data(sym_y: str, sym_x: str) -> pd.DataFrame:
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
    return df_merged


def precompute_log_pair(df_merged: pd.DataFrame, window: int) -> Dict[str, Any]:
    w = window
    p_y = df_merged['close_y'].values
    p_x = df_merged['close_x'].values
    log_y = np.log(p_y)
    log_x = np.log(p_x)
    btc_ret_30d = df_merged['btc_ret_30d'].values
    corr_30d = df_merged['corr_30d'].values
    n = len(p_y)

    betas = np.zeros(n)
    means = np.zeros(n)
    stds = np.zeros(n)
    z_scores = np.zeros(n)
    adf_pvals = np.full(n, 1.0)
    raw_eligible = np.zeros(n, dtype=bool)

    for t in range(w, n):
        log_y_w = log_y[t-w : t]
        log_x_w = log_x[t-w : t]

        cov = np.cov(log_x_w, log_y_w)[0, 1]
        var = np.var(log_x_w)
        if var == 0:
            continue
        beta = cov / var

        spread_w = log_y_w - beta * log_x_w
        mean_s = np.mean(spread_w)
        std_s = np.std(spread_w)
        if std_s == 0:
            continue

        curr_spread = log_y[t] - beta * log_x[t]
        z = (curr_spread - mean_s) / std_s

        betas[t] = beta
        means[t] = mean_s
        stds[t] = std_s
        z_scores[t] = z

        is_z = (2.5 <= z <= 3.4) or (-3.4 <= z <= -2.5)
        is_regime = not (btc_ret_30d[t] <= -0.20 or corr_30d[t] < 0.60)

        if is_z and is_regime:
            raw_eligible[t] = True
            try:
                adf_res = adfuller(spread_w, autolag='AIC')
                adf_pvals[t] = float(adf_res[1])
            except Exception:
                adf_pvals[t] = 1.0

    return {
        'p_y': p_y,
        'p_x': p_x,
        'betas': betas,
        'z_scores': z_scores,
        'adf_pvals': adf_pvals,
        'raw_eligible': raw_eligible,
        'timestamps': df_merged['timestamp'].values
    }


def simulate_log_stat_arb(
    cache: Dict[str, Any],
    start_time: str,
    end_time: str,
    base_notional: float = 150.0,
    z_entry: float = 2.5,
    z_exit: float = 0.0,
    z_stop: float = 3.5,
    max_holding_bars: int = 24,
    adf_threshold: float = 0.05
) -> Tuple[List[Dict[str, Any]], int, int, List[float]]:
    ts = pd.to_datetime(cache['timestamps'])
    mask = (ts >= pd.to_datetime(start_time)) & (ts <= pd.to_datetime(end_time))
    indices = np.where(mask)[0]
    if len(indices) == 0:
        return [], 0, 0, []

    p_y = cache['p_y']
    p_x = cache['p_x']
    betas = cache['betas']
    z_scores = cache['z_scores']
    adf_pvals = cache['adf_pvals']
    raw_eligible = cache['raw_eligible']

    trades = []
    in_pos = False
    pos_side = None
    entry_p_y = entry_p_x = entry_beta = 0.0
    entry_idx = 0

    raw_signals = 0
    adf_rejected = 0
    used_betas = []

    for t in indices:
        z = z_scores[t]
        beta = betas[t]
        curr_p_y = p_y[t]
        curr_p_x = p_x[t]

        if not in_pos:
            if raw_eligible[t]:
                raw_signals += 1
                if adf_pvals[t] >= adf_threshold:
                    adf_rejected += 1
                    continue

                if z_entry <= z <= z_entry + 0.9:
                    in_pos = True
                    pos_side = 'SHORT'
                    entry_p_y, entry_p_x, entry_beta, entry_idx = curr_p_y, curr_p_x, beta, t
                    used_betas.append(beta)
                elif -(z_entry + 0.9) <= z <= -z_entry:
                    in_pos = True
                    pos_side = 'LONG'
                    entry_p_y, entry_p_x, entry_beta, entry_idx = curr_p_y, curr_p_x, beta, t
                    used_betas.append(beta)
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
                # Dollar-neutral sizing:
                notional_y = base_notional
                notional_x = abs(entry_beta) * base_notional

                qty_y = notional_y / entry_p_y
                qty_x = notional_x / entry_p_x

                if pos_side == 'SHORT':
                    pnl_y = (entry_p_y - curr_p_y) * qty_y
                    pnl_x = (curr_p_x - entry_p_x) * qty_x
                else:
                    pnl_y = (curr_p_y - entry_p_y) * qty_y
                    pnl_x = (entry_p_x - curr_p_x) * qty_x

                gross_pnl = pnl_y + pnl_x
                fees = (notional_y + notional_x) * 2 * 0.0004
                net_pnl = gross_pnl - fees

                trades.append({
                    'net_pnl': net_pnl,
                    'gross_pnl': gross_pnl,
                    'fees': fees,
                    'holding': holding,
                    'entry_idx': entry_idx,
                    'exit_idx': t,
                    'beta': entry_beta,
                    'notional_y': notional_y,
                    'notional_x': notional_x
                })
                in_pos = False

    return trades, raw_signals, adf_rejected, used_betas


def evaluate_split(trades: List[Dict[str, Any]], initial_cap: float = 5000.0) -> Dict[str, Any]:
    if not trades:
        return {'pf': 0.0, 'trades': 0, 'wr': 0.0, 'net_pnl': 0.0, 'exp': 0.0, 'dd': 0.0, 'max_loss_streak': 0}

    df = pd.DataFrame(trades)
    wins = df[df['net_pnl'] > 0]
    losses = df[df['net_pnl'] <= 0]

    gw = wins['net_pnl'].sum() if not wins.empty else 0.0
    gl = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
    pf = gw / gl
    wr = (len(wins) / len(df)) * 100.0
    net_pnl = df['net_pnl'].sum()
    exp = df['net_pnl'].mean()

    equity = initial_cap + df['net_pnl'].cumsum()
    peak = equity.cummax()
    max_dd_pct = ((peak - equity).max() / initial_cap) * 100.0

    max_streak = 0
    curr_streak = 0
    for tr in trades:
        if tr['net_pnl'] <= 0:
            curr_streak += 1
            if curr_streak > max_streak:
                max_streak = curr_streak
        else:
            curr_streak = 0

    return {
        'pf': round(pf, 2),
        'trades': len(df),
        'wr': round(wr, 1),
        'net_pnl': round(net_pnl, 2),
        'exp': round(exp, 2),
        'dd': round(max_dd_pct, 2),
        'max_loss_streak': max_streak
    }


def main():
    print("="*140)
    print("BATCH J: LOG-PRICE / DOLLAR-NEUTRAL STATISTICAL ARBITRAGE (2022-2026)")
    print("="*140)

    # 1. Load data for 5 pairs
    pair_dfs = {}
    for y, x in PAIRS_J:
        p_name = f"{y}/{x}"
        print(f"Loading {p_name}...")
        pair_dfs[p_name] = load_pair_data(y, x)

    variant_summary = []

    for v_name, window in VARIANTS_J:
        print(f"\nEvaluating Variant {v_name} (Lookback W={window})...")
        train_trades, test_trades, val_trades, full_trades = [], [], [], []
        all_raw_signals = 0
        all_adf_rejected = 0
        all_betas = []
        all_time_betas = []

        for p_name, df_m in pair_dfs.items():
            cache = precompute_log_pair(df_m, window=window)
            all_time_betas.extend(cache['betas'][window:])

            tr_train, _, _, _ = simulate_log_stat_arb(cache, '2022-01-01', '2023-12-31 23:00:00')
            tr_test, _, _, _ = simulate_log_stat_arb(cache, '2024-01-01', '2024-12-31 23:00:00')
            tr_val, _, _, _ = simulate_log_stat_arb(cache, '2024-01-01', '2026-08-16 23:00:00')
            tr_full, raw_sig, adf_rej, used_b = simulate_log_stat_arb(cache, '2022-01-01', '2026-08-16 23:00:00')

            train_trades.extend(tr_train)
            test_trades.extend(tr_test)
            val_trades.extend(tr_val)
            full_trades.extend(tr_full)
            all_raw_signals += raw_sig
            all_adf_rejected += adf_rej
            all_betas.extend(used_b)

        m_train = evaluate_split(train_trades)
        m_test = evaluate_split(test_trades)
        m_val = evaluate_split(val_trades)
        m_full = evaluate_split(full_trades)

        tpy = round(m_full['trades'] / 4.62, 1)
        tpm = round(tpy / 12.0, 2)
        adf_rej_pct = round((all_adf_rejected / all_raw_signals * 100.0) if all_raw_signals > 0 else 0.0, 1)

        # Beta stats
        arr_b = np.array(all_betas) if all_betas else np.array([1.0])
        beta_min = round(float(np.min(arr_b)), 2)
        beta_max = round(float(np.max(arr_b)), 2)
        beta_mean = round(float(np.mean(arr_b)), 2)
        beta_std = round(float(np.std(arr_b)), 2)

        extreme_betas = int(np.sum((arr_b < 0.1) | (arr_b > 5.0)))

        # Time with dollar neutrality deviation > 5% (|beta - 1.0| > 0.05)
        arr_time_b = np.array(all_time_betas)
        dev_gt_5pct = round(float(np.sum(np.abs(arr_time_b - 1.0) > 0.05) / len(arr_time_b) * 100.0), 1)

        # Killer check
        passed = (m_val['pf'] > 1.30) and (m_val['dd'] < 15.0) and (m_val['trades'] >= 100) and (m_val['exp'] > 0.0)
        verdict = "PASSED (SURVIVOR)" if passed else "KILLED"

        variant_summary.append({
            'variant': v_name,
            'lookback_W': window,
            'train_pf': m_train['pf'],
            'test_pf': m_test['pf'],
            'oos_pf': m_val['pf'],
            'oos_trades': m_val['trades'],
            'oos_wr': m_val['wr'],
            'oos_net_pnl': m_val['net_pnl'],
            'oos_exp': m_val['exp'],
            'oos_dd': m_val['dd'],
            'oos_loss_streak': m_val['max_loss_streak'],
            'full_trades': m_full['trades'],
            'trades_per_year': tpy,
            'trades_per_month': tpm,
            'beta_min_max': f"[{beta_min}, {beta_max}]",
            'beta_mean': beta_mean,
            'extreme_betas': extreme_betas,
            'adf_rej_pct': adf_rej_pct,
            'dev_neutral_gt5pct': f"{dev_gt_5pct}%",
            'verdict': verdict
        })

    df_sum = pd.DataFrame(variant_summary)
    print("\n" + "="*160)
    print("BATCH J: SUMMARY OF ALL 5 LOG-PRICE DOLLAR-NEUTRAL VARIANTS (J1 - J5)")
    print("="*160)
    cols = ['variant', 'lookback_W', 'train_pf', 'test_pf', 'oos_pf', 'oos_trades', 'oos_wr', 'oos_net_pnl', 'oos_exp', 'oos_dd', 'oos_loss_streak', 'full_trades', 'trades_per_year', 'trades_per_month', 'beta_min_max', 'beta_mean', 'adf_rej_pct', 'verdict']
    print(df_sum[cols].to_string(index=False))
    print("="*160)

    # Save to json
    output_path = PROJECT_ROOT / "logs" / "paper" / "batch_j_evaluation.json"
    df_sum.to_json(output_path, orient="records", indent=2)
    print(f"Saved Batch J results to {output_path}")


if __name__ == '__main__':
    main()
