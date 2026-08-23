"""
High-Performance Batch H Walk-Forward and Multi-Metric Frequency Evaluation Script
Precomputes rolling OLS and memoizes ADF regressions per pair, then evaluates H1 to H5 in seconds.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from statsmodels.tsa.stattools import adfuller

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.factory.validator import FactoryValidator


def precompute_pair_series(df_merged: pd.DataFrame, lookback_window: int = 90) -> Dict[str, Any]:
    """Precomputes rolling OLS stats and memoizes ADF p-values on all candidate bars."""
    w = lookback_window
    y = df_merged['close_y'].values
    x = df_merged['close_x'].values
    btc_ret_30d = df_merged['btc_ret_30d'].values
    corr_30d = df_merged['corr_30d'].values
    n = len(y)

    gammas = np.zeros(n)
    means = np.zeros(n)
    stds = np.zeros(n)
    z_scores = np.zeros(n)
    adf_pvals = np.full(n, 1.0)
    raw_eligible = np.zeros(n, dtype=bool)

    print(f"  Precomputing OLS and ADF p-values for {n} bars...")
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

        gammas[t] = gamma
        means[t] = mean_s
        stds[t] = std_s
        z_scores[t] = z

        # Raw eligibility check: Z within entry range and Regime Filter passed
        is_z_entry = (2.5 <= z <= 3.4) or (-3.4 <= z <= -2.5)
        is_regime_ok = not (btc_ret_30d[t] <= -0.20 or corr_30d[t] < 0.60)

        if is_z_entry and is_regime_ok:
            raw_eligible[t] = True
            try:
                adf_res = adfuller(spread_w, autolag='AIC')
                adf_pvals[t] = float(adf_res[1])
            except Exception:
                adf_pvals[t] = 1.0

    return {
        'df': df_merged,
        'y': y,
        'x': x,
        'gammas': gammas,
        'z_scores': z_scores,
        'adf_pvals': adf_pvals,
        'raw_eligible': raw_eligible,
        'timestamps': df_merged['timestamp'].values
    }


def simulate_from_precomputed(
    cache: Dict[str, Any],
    start_time: str,
    end_time: str,
    adf_threshold: float,
    z_entry: float = 2.5,
    z_exit: float = 0.0,
    z_stop: float = 3.5,
    max_holding_bars: int = 24,
    notional: float = 150.0
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Runs simulation on precomputed cache with given ADF threshold."""
    ts = pd.to_datetime(cache['timestamps'])
    mask = (ts >= pd.to_datetime(start_time)) & (ts <= pd.to_datetime(end_time))
    indices = np.where(mask)[0]
    if len(indices) == 0:
        return [], 0, 0

    y = cache['y']
    x = cache['x']
    gammas = cache['gammas']
    z_scores = cache['z_scores']
    adf_pvals = cache['adf_pvals']
    raw_eligible = cache['raw_eligible']

    trades = []
    in_pos = False
    pos_side = None
    entry_y = entry_x = entry_gamma = 0.0
    entry_idx = 0

    raw_signals = 0
    adf_rejected = 0

    for t in indices:
        z = z_scores[t]
        gamma = gammas[t]
        curr_y = y[t]
        curr_x = x[t]

        if not in_pos:
            if raw_eligible[t]:
                raw_signals += 1
                if adf_pvals[t] >= adf_threshold:
                    adf_rejected += 1
                    continue

                if z_entry <= z <= z_entry + 0.9:
                    in_pos = True
                    pos_side = 'SHORT'
                    entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
                elif -(z_entry + 0.9) <= z <= -z_entry:
                    in_pos = True
                    pos_side = 'LONG'
                    entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
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
                qty_x = (notional * entry_gamma) / entry_x

                if pos_side == 'SHORT':
                    pnl_y = (entry_y - curr_y) * qty_y
                    pnl_x = (curr_x - entry_x) * qty_x
                else:
                    pnl_y = (curr_y - entry_y) * qty_y
                    pnl_x = (entry_x - curr_x) * qty_x

                gross_pnl = pnl_y + pnl_x
                fees = (notional + notional * entry_gamma) * 2 * 0.0004
                net_pnl = gross_pnl - fees
                trades.append({
                    'net_pnl': net_pnl,
                    'holding': holding,
                    'entry_idx': entry_idx,
                    'exit_idx': t
                })
                in_pos = False

    return trades, raw_signals, adf_rejected


def calculate_loss_streak(trades: List[Dict[str, Any]]) -> int:
    if not trades:
        return 0
    max_streak = 0
    curr_streak = 0
    for tr in trades:
        if tr['net_pnl'] <= 0:
            curr_streak += 1
            if curr_streak > max_streak:
                max_streak = curr_streak
        else:
            curr_streak = 0
    return max_streak


def main():
    validator = FactoryValidator()
    print(f"Loaded {len(validator.cached_pairs)} pairs: {list(validator.cached_pairs.keys())}")

    # 1. Precompute per-pair series
    pair_caches = {}
    for pair_name, df_merged in validator.cached_pairs.items():
        print(f"Precomputing cache for pair {pair_name}...")
        pair_caches[pair_name] = precompute_pair_series(df_merged, lookback_window=90)

    variants = [
        ('H1', 0.05),
        ('H2', 0.07),
        ('H3', 0.10),
        ('H4', 0.15),
        ('H5', 0.20)
    ]

    results_table = []

    for name, adf_thresh in variants:
        train_trades, test_trades, val_trades, full_trades = [], [], [], []
        total_raw_signals = 0
        total_adf_rejected = 0

        for pair_name, cache in pair_caches.items():
            t_tr, _, _ = simulate_from_precomputed(cache, '2022-01-01', '2023-12-31 23:00:00', adf_thresh)
            te_tr, _, _ = simulate_from_precomputed(cache, '2024-01-01', '2024-12-31 23:00:00', adf_thresh)
            v_tr, _, _ = simulate_from_precomputed(cache, '2024-01-01', '2026-08-16 23:00:00', adf_thresh)
            f_tr, raw_sig, adf_rej = simulate_from_precomputed(cache, '2022-01-01', '2026-08-16 23:00:00', adf_thresh)

            train_trades.extend(t_tr)
            test_trades.extend(te_tr)
            val_trades.extend(v_tr)
            full_trades.extend(f_tr)
            total_raw_signals += raw_sig
            total_adf_rejected += adf_rej

        train_pf, _, _, _, _, _ = validator.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = validator.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = validator.evaluate_split(val_trades)
        full_pf, full_cnt, full_wr, full_net, full_exp, full_dd = validator.evaluate_split(full_trades)

        total_years = 4.62  # 2022-01-01 to 2026-08-16 = 4.62 years
        trades_per_year = full_cnt / total_years
        trades_per_month = trades_per_year / 12.0

        adf_rej_pct = (total_adf_rejected / total_raw_signals * 100.0) if total_raw_signals > 0 else 0.0
        max_loss_streak = calculate_loss_streak(val_trades)

        passed = (val_pf > 1.30) and (val_dd < 15.0) and (val_cnt >= 100) and (val_exp > 0.0)
        verdict = "PASSED (SURVIVOR)" if passed else "KILLED"

        row = {
            "variant": name,
            "candidate_id": f"Pairs_W90_Z2.5_ADF{adf_thresh:.2f}",
            "adf_p": adf_thresh,
            "train_pf": round(train_pf, 2),
            "test_pf": round(test_pf, 2),
            "oos_pf": round(val_pf, 2),
            "oos_trades": val_cnt,
            "oos_wr": round(val_wr, 1),
            "oos_net_pnl": round(val_net, 2),
            "oos_exp": round(val_exp, 2),
            "oos_dd": round(val_dd, 2),
            "oos_max_loss_streak": max_loss_streak,
            "full_trades": full_cnt,
            "trades_per_year": round(trades_per_year, 1),
            "trades_per_month": round(trades_per_month, 2),
            "adf_rejection_pct": round(adf_rej_pct, 1),
            "passed": passed,
            "verdict": verdict
        }
        results_table.append(row)

    df_res = pd.DataFrame(results_table)
    print("\n" + "="*140)
    print("BATCH H: FREQUENCY EXPANSION BY ADF THRESHOLD - EXACT RESULTS")
    print("="*140)
    print(df_res.to_string(index=False))
    print("="*140)

    # Save to json for autopsy and ingestion
    output_path = PROJECT_ROOT / "logs" / "paper" / "batch_h_evaluation.json"
    df_res.to_json(output_path, orient="records", indent=2)
    print(f"Saved results to {output_path}")


if __name__ == '__main__':
    main()
