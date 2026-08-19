"""
Phase 2 Validation & Phase 3 Portfolio Capacity Simulation for Batch I Universe Expansion.
Evaluates the 5 Train-selected pairs:
1. ETHUSDT/AVAXUSDT
2. BTCUSDT/SOLUSDT
3. BTCUSDT/DOTUSDT
4. AVAXUSDT/DOTUSDT
5. ETHUSDT/DOTUSDT

Along with the Base Portfolio pairs:
- BTCUSDT/ETHUSDT
- AVAXUSDT/SOLUSDT
- LINKUSDT/DOTUSDT
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from statsmodels.tsa.stattools import adfuller

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical"

BASE_PAIRS = [('BTCUSDT', 'ETHUSDT'), ('AVAXUSDT', 'SOLUSDT'), ('LINKUSDT', 'DOTUSDT')]
NEW_PAIRS = [
    ('ETHUSDT', 'AVAXUSDT'),
    ('BTCUSDT', 'SOLUSDT'),
    ('BTCUSDT', 'DOTUSDT'),
    ('AVAXUSDT', 'DOTUSDT'),
    ('ETHUSDT', 'DOTUSDT')
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


def simulate_full_series(
    df_merged: pd.DataFrame,
    lookback_window: int = 90,
    z_entry: float = 2.5,
    z_exit: float = 0.0,
    z_stop: float = 3.5,
    max_holding_bars: int = 24,
    adf_threshold: float = 0.05,
    notional: float = 150.0
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """Simulates trading and tracks active position timeline."""
    w = lookback_window
    y = df_merged['close_y'].values
    x = df_merged['close_x'].values
    btc_ret_30d = df_merged['btc_ret_30d'].values
    corr_30d = df_merged['corr_30d'].values
    ts = df_merged['timestamp'].values
    n = len(y)

    trades = []
    in_pos = False
    pos_side = None
    entry_y = entry_x = entry_gamma = 0.0
    entry_idx = 0

    position_active = np.zeros(n, dtype=int)

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
                try:
                    adf_res = adfuller(spread_w, autolag='AIC')
                    if adf_res[1] < adf_threshold:
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
            position_active[t] = 1
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
                trades.append({
                    'net_pnl': net_pnl,
                    'holding': holding,
                    'entry_idx': entry_idx,
                    'exit_idx': t,
                    'entry_time': ts[entry_idx],
                    'exit_time': ts[t]
                })
                in_pos = False

    return trades, position_active


def evaluate_split(trades: List[Dict[str, Any]], initial_cap: float = 5000.0) -> Dict[str, Any]:
    if not trades:
        return {'pf': 0.0, 'trades': 0, 'wr': 0.0, 'net_pnl': 0.0, 'exp': 0.0, 'dd': 0.0}

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

    return {
        'pf': round(pf, 2),
        'trades': len(df),
        'wr': round(wr, 1),
        'net_pnl': round(net_pnl, 2),
        'exp': round(exp, 2),
        'dd': round(max_dd_pct, 2)
    }


def filter_trades_by_date(trades: List[Dict[str, Any]], start: str, end: str) -> List[Dict[str, Any]]:
    s = pd.to_datetime(start)
    e = pd.to_datetime(end)
    return [tr for tr in trades if s <= pd.to_datetime(tr['exit_time']) <= e]


def main():
    print("="*140)
    print("BATCH I: WALK-FORWARD VALIDATION OF 5 NEW CANDIDATE PAIRS (2022-2026)")
    print("="*140)

    all_pairs_to_test = BASE_PAIRS + NEW_PAIRS
    pair_sim_results = {}
    pair_timeline = {}

    for sym_y, sym_x in all_pairs_to_test:
        pair_name = f"{sym_y}/{sym_x}"
        print(f"Simulating {pair_name}...")
        df_merged = load_pair_data(sym_y, sym_x)
        trades, pos_act = simulate_full_series(df_merged)
        pair_sim_results[pair_name] = trades
        pair_timeline[pair_name] = pos_act

    # 1. Individual Performance Table for New Pairs
    new_pair_rows = []
    surviving_pairs = []

    for sym_y, sym_x in NEW_PAIRS:
        pair_name = f"{sym_y}/{sym_x}"
        tr_full = pair_sim_results[pair_name]
        tr_train = filter_trades_by_date(tr_full, '2022-01-01', '2023-12-31 23:00:00')
        tr_test = filter_trades_by_date(tr_full, '2024-01-01', '2024-12-31 23:00:00')
        tr_oos = filter_trades_by_date(tr_full, '2024-01-01', '2026-08-16 23:00:00')

        m_train = evaluate_split(tr_train)
        m_test = evaluate_split(tr_test)
        m_oos = evaluate_split(tr_oos)
        m_full = evaluate_split(tr_full)

        trades_per_year = round(m_full['trades'] / 4.62, 1)
        trades_per_month = round(trades_per_year / 12.0, 2)

        # Killer Check: PF > 1.30, DD < 15%, Expectancy > 0
        passed = (m_oos['pf'] > 1.30) and (m_oos['dd'] < 15.0) and (m_oos['exp'] > 0.0) and (m_oos['trades'] >= 20)
        verdict = "PASSED (SURVIVOR)" if passed else "KILLED"
        if passed:
            surviving_pairs.append(pair_name)

        new_pair_rows.append({
            'pair': pair_name,
            'train_pf': m_train['pf'],
            'train_trades': m_train['trades'],
            'test_pf': m_test['pf'],
            'oos_pf': m_oos['pf'],
            'oos_trades': m_oos['trades'],
            'oos_wr': m_oos['wr'],
            'oos_net_pnl': m_oos['net_pnl'],
            'oos_exp': m_oos['exp'],
            'oos_dd': m_oos['dd'],
            'full_trades': m_full['trades'],
            'trades_per_year': trades_per_year,
            'trades_per_month': trades_per_month,
            'verdict': verdict
        })

    df_new = pd.DataFrame(new_pair_rows)
    print("\n" + "="*140)
    print("PHASE 2: NEW PAIRS INDIVIDUAL WALK-FORWARD OOS RESULTS")
    print("="*140)
    print(df_new.to_string(index=False))
    print("="*140)

    # 2. Portfolio Comparison
    print(f"\nSurviving New Pairs: {surviving_pairs}")

    # Base Portfolio (3 pairs)
    base_pair_names = [f"{y}/{x}" for y, x in BASE_PAIRS]
    base_trades_oos = []
    for p in base_pair_names:
        base_trades_oos.extend(filter_trades_by_date(pair_sim_results[p], '2024-01-01', '2026-08-16 23:00:00'))

    base_trades_oos.sort(key=lambda t: t['exit_time'])
    m_base_oos = evaluate_split(base_trades_oos)
    base_full_trades = sum(len(pair_sim_results[p]) for p in base_pair_names)
    base_tpy = round(base_full_trades / 4.62, 1)
    base_tpm = round(base_tpy / 12.0, 2)

    # Expanded Portfolio (Base + Survivors, or Base + Top New)
    expanded_pairs = base_pair_names + surviving_pairs
    expanded_trades_oos = []
    for p in expanded_pairs:
        expanded_trades_oos.extend(filter_trades_by_date(pair_sim_results[p], '2024-01-01', '2026-08-16 23:00:00'))

    expanded_trades_oos.sort(key=lambda t: t['exit_time'])
    m_expanded_oos = evaluate_split(expanded_trades_oos)
    expanded_full_trades = sum(len(pair_sim_results[p]) for p in expanded_pairs)
    expanded_tpy = round(expanded_full_trades / 4.62, 1)
    expanded_tpm = round(expanded_tpy / 12.0, 2)

    # Overlap Analysis
    base_timeline = np.sum([pair_timeline[p] for p in base_pair_names], axis=0)
    expanded_timeline = np.sum([pair_timeline[p] for p in expanded_pairs], axis=0)

    print("\n" + "="*120)
    print("PHASE 3: PORTFOLIO CAPACITY COMPARISON (BASE vs EXPANDED)")
    print("="*120)

    port_comp = [
        {
            'Metric': 'Portfolio Pairs Count',
            'Base Portfolio (3 pairs)': len(base_pair_names),
            'Expanded Portfolio': len(expanded_pairs),
            'Absolute Change': f"+{len(expanded_pairs) - len(base_pair_names)} pairs"
        },
        {
            'Metric': 'OOS Trades (2024-2026)',
            'Base Portfolio (3 pairs)': m_base_oos['trades'],
            'Expanded Portfolio': m_expanded_oos['trades'],
            'Absolute Change': f"+{m_expanded_oos['trades'] - m_base_oos['trades']} trades (+{((m_expanded_oos['trades'] - m_base_oos['trades'])/m_base_oos['trades']*100):.1f}%)"
        },
        {
            'Metric': 'Full Trades / Year (2022-2026)',
            'Base Portfolio (3 pairs)': base_tpy,
            'Expanded Portfolio': expanded_tpy,
            'Absolute Change': f"+{expanded_tpy - base_tpy:.1f} tr/yr (+{((expanded_tpy - base_tpy)/base_tpy*100):.1f}%)"
        },
        {
            'Metric': 'Full Trades / Month (2022-2026)',
            'Base Portfolio (3 pairs)': base_tpm,
            'Expanded Portfolio': expanded_tpm,
            'Absolute Change': f"+{expanded_tpm - base_tpm:.2f} tr/mo"
        },
        {
            'Metric': 'OOS Profit Factor (PF)',
            'Base Portfolio (3 pairs)': m_base_oos['pf'],
            'Expanded Portfolio': m_expanded_oos['pf'],
            'Absolute Change': f"{m_expanded_oos['pf'] - m_base_oos['pf']:+.2f}"
        },
        {
            'Metric': 'OOS Win Rate (%)',
            'Base Portfolio (3 pairs)': f"{m_base_oos['wr']}%",
            'Expanded Portfolio': f"{m_expanded_oos['wr']}%",
            'Absolute Change': f"{m_expanded_oos['wr'] - m_base_oos['wr']:+.1f}%"
        },
        {
            'Metric': 'OOS Net PnL ($)',
            'Base Portfolio (3 pairs)': f"${m_base_oos['net_pnl']:.2f}",
            'Expanded Portfolio': f"${m_expanded_oos['net_pnl']:.2f}",
            'Absolute Change': f"${m_expanded_oos['net_pnl'] - m_base_oos['net_pnl']:+.2f}"
        },
        {
            'Metric': 'OOS Expectancy ($/tr)',
            'Base Portfolio (3 pairs)': f"${m_base_oos['exp']:.2f}",
            'Expanded Portfolio': f"${m_expanded_oos['exp']:.2f}",
            'Absolute Change': f"${m_expanded_oos['exp'] - m_base_oos['exp']:+.2f}"
        },
        {
            'Metric': 'OOS Max Drawdown (%)',
            'Base Portfolio (3 pairs)': f"{m_base_oos['dd']}%",
            'Expanded Portfolio': f"{m_expanded_oos['dd']}%",
            'Absolute Change': f"{m_expanded_oos['dd'] - m_base_oos['dd']:+.2f}%"
        },
        {
            'Metric': 'Max Simultaneous Positions',
            'Base Portfolio (3 pairs)': int(np.max(base_timeline)),
            'Expanded Portfolio': int(np.max(expanded_timeline)),
            'Absolute Change': f"{int(np.max(expanded_timeline)) - int(np.max(base_timeline)):+d}"
        }
    ]

    df_port = pd.DataFrame(port_comp)
    print(df_port.to_string(index=False))
    print("="*120)

    # Position overlap distribution
    print("\nPosition Overlap Distribution (% of all 1H bars with N concurrent positions):")
    for n_pos in range(int(np.max(expanded_timeline)) + 1):
        pct_base = (np.sum(base_timeline == n_pos) / len(base_timeline)) * 100.0
        pct_exp = (np.sum(expanded_timeline == n_pos) / len(expanded_timeline)) * 100.0
        print(f"  {n_pos} concurrent positions: Base = {pct_base:.1f}% | Expanded = {pct_exp:.1f}%")


if __name__ == '__main__':
    main()
