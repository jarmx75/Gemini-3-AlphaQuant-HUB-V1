"""
Batch K: Cross-Exchange Lead/Lag Strategy Engine (5m Timeframe, 2022-2026)
Venues: Binance vs Coinbase (BTC & ETH spot)

Phase 1: Discovery (TRAIN 2022-2023 ONLY)
- Cross-correlation analysis
- Direction of lead/lag (Binance -> Coinbase vs Coinbase -> Binance)
- Expected move modeling

Phase 2: Walk-Forward Validation (2022-2026, OOS 2024-2026)
- 5 Variants: K1 (lag=1), K2 (lag=2), K3 (lag=3), K4 (lag=6), K5 (lag=12)
- Strict transaction cost hurdle: Expected move > 3x Round-Trip Costs
- Realistic fees, slippage, and latency
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical_cross_exchange"

VARIANTS_K = [
    ('K1', 1),   # 5m
    ('K2', 2),   # 10m
    ('K3', 3),   # 15m
    ('K4', 6),   # 30m
    ('K5', 12)   # 60m
]


def load_aligned_data(asset: str) -> pd.DataFrame:
    """Loads and aligns Binance and Coinbase 5m candles by exact UTC timestamp."""
    if asset == "BTC":
        file_bin = DATA_DIR / "binance_BTCUSDT_5m_2022_2026.csv"
        file_cb = DATA_DIR / "coinbase_BTCUSD_5m_2022_2026.csv"
    else:
        file_bin = DATA_DIR / "binance_ETHUSDT_5m_2022_2026.csv"
        file_cb = DATA_DIR / "coinbase_ETHUSD_5m_2022_2026.csv"

    df_bin = pd.read_csv(file_bin)[['timestamp', 'close', 'volume']].rename(
        columns={'close': 'close_bin', 'volume': 'vol_bin'}
    )
    df_cb = pd.read_csv(file_cb)[['timestamp', 'close', 'volume']].rename(
        columns={'close': 'close_cb', 'volume': 'vol_cb'}
    )

    df_bin['timestamp'] = pd.to_datetime(df_bin['timestamp'], utc=True)
    df_cb['timestamp'] = pd.to_datetime(df_cb['timestamp'], utc=True)

    df = pd.merge(df_bin, df_cb, on='timestamp').sort_values('timestamp').reset_index(drop=True)

    # 5m log returns
    df['ret_bin_5m'] = np.log(df['close_bin'] / df['close_bin'].shift(1)).fillna(0.0)
    df['ret_cb_5m'] = np.log(df['close_cb'] / df['close_cb'].shift(1)).fillna(0.0)
    return df


def run_phase_1_discovery(df_btc: pd.DataFrame, df_eth: pd.DataFrame):
    """Evaluates lead/lag cross-correlations strictly on TRAIN (2022-2023)."""
    print("="*120)
    print("PHASE 1: DISCOVERY (TRAIN 2022-2023 ONLY - ZERO OOS ACCESS)")
    print("="*120)

    for asset_name, df in [("BTC", df_btc), ("ETH", df_eth)]:
        df_train = df[(df['timestamp'] >= '2022-01-01') & (df['timestamp'] < '2024-01-01')].reset_index(drop=True)
        r_bin = df_train['ret_bin_5m'].values
        r_cb = df_train['ret_cb_5m'].values
        n = len(r_bin)

        print(f"\n--- Cross-Correlation Analysis for {asset_name} (Train Bars: {n}) ---")
        print(f"{'Lag (k)':<10} | {'Binance leads Coinbase Corr':<30} | {'Coinbase leads Binance Corr':<30} | {'Dominant Lead'}")
        print("-" * 90)

        for lag in [1, 2, 3, 6, 12]:
            # Binance leads Coinbase at lag k: Corr(R_bin[t], R_cb[t+k])
            corr_bin_leads = np.corrcoef(r_bin[:-lag], r_cb[lag:])[0, 1]
            # Coinbase leads Binance at lag k: Corr(R_cb[t], R_bin[t+k])
            corr_cb_leads = np.corrcoef(r_cb[:-lag], r_bin[lag:])[0, 1]

            dom = "Binance -> Coinbase" if corr_bin_leads > corr_cb_leads else "Coinbase -> Binance"
            print(f"{lag} (={lag*5}m){'':<4} | {corr_bin_leads:<30.4f} | {corr_cb_leads:<30.4f} | {dom}")

    print("="*120)


def simulate_cross_exchange_lead_lag(
    df: pd.DataFrame,
    lead_col: str,
    follower_col: str,
    lag: int,
    start_date: str,
    end_date: str,
    follower_venue: str,
    notional: float = 300.0
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Simulates trading follower based on observable lead return."""
    df_slice = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)].reset_index(drop=True)

    p_foll = df_slice[follower_col].values
    r_lead = df_slice[lead_col].values
    ts = df_slice['timestamp'].values
    n = len(p_foll)

    # Costs
    if follower_venue == "binance":
        taker_fee = 0.0010  # 0.10% each side = 0.20% roundtrip
        slippage = 0.0002   # 0.02%
        latency_cost = 0.0001 # 0.01%
    else:  # coinbase
        taker_fee = 0.0060  # 0.60% each side = 1.20% roundtrip
        slippage = 0.0003   # 0.03%
        latency_cost = 0.0001

    roundtrip_cost = (taker_fee * 2) + (slippage * 2) + latency_cost
    hurdle = 3.0 * roundtrip_cost  # 3x cost hurdle

    trades = []
    t = 1
    while t < n - lag:
        # Observable return of leader on bar t
        ret_lead = r_lead[t]

        # Check if observable move exceeds hurdle
        if abs(ret_lead) >= hurdle:
            side = 'LONG' if ret_lead > 0 else 'SHORT'
            entry_p = p_foll[t]
            exit_p = p_foll[t + lag]
            entry_time = ts[t]
            exit_time = ts[t + lag]

            if side == 'LONG':
                gross_ret = (exit_p - entry_p) / entry_p
            else:
                gross_ret = (entry_p - exit_p) / entry_p

            gross_pnl = gross_ret * notional
            fees = notional * (taker_fee * 2)
            slip = notional * (slippage * 2 + latency_cost)
            net_pnl = gross_pnl - fees - slip

            trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'year': pd.to_datetime(entry_time).year,
                'side': side,
                'gross_ret': gross_ret,
                'gross_pnl': gross_pnl,
                'fees': fees,
                'slippage': slip,
                'net_pnl': net_pnl,
                'lag': lag
            })
            t += lag # Jump forward
        else:
            t += 1

    return trades, {
        'roundtrip_cost_pct': round(roundtrip_cost * 100.0, 3),
        'hurdle_pct': round(hurdle * 100.0, 3)
    }


def evaluate_split(trades: List[Dict[str, Any]], initial_cap: float = 5000.0) -> Dict[str, Any]:
    if not trades:
        return {
            'pf': 0.0, 'trades': 0, 'wr': 0.0, 'net_pnl': 0.0, 'exp': 0.0,
            'dd': 0.0, 'avg_gross_edge': 0.0, 'avg_fees': 0.0, 'avg_slip': 0.0,
            'net_edge_pct': 0.0, 'max_loss_streak': 0, 'year_dist': {}
        }

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

    year_dist = df['year'].value_counts().to_dict()

    avg_gross = df['gross_pnl'].mean()
    avg_fees = df['fees'].mean()
    avg_slip = df['slippage'].mean()
    net_edge_pct = (df['net_pnl'].sum() / (len(df) * 300.0)) * 100.0

    return {
        'pf': round(pf, 2),
        'trades': len(df),
        'wr': round(wr, 1),
        'net_pnl': round(net_pnl, 2),
        'exp': round(exp, 2),
        'dd': round(max_dd_pct, 2),
        'avg_gross_edge': round(avg_gross, 2),
        'avg_fees': round(avg_fees, 2),
        'avg_slip': round(avg_slip, 2),
        'net_edge_pct': round(net_edge_pct, 3),
        'max_loss_streak': max_streak,
        'year_dist': year_dist
    }


def main():
    print("Loading aligned 5m datasets...")
    df_btc = load_aligned_data("BTC")
    df_eth = load_aligned_data("ETH")

    # 1. Phase 1 Discovery
    run_phase_1_discovery(df_btc, df_eth)

    # Lead/Follower selection based on Train Discovery:
    # Binance is global volume leader (80%+ volume share, higher cross-correlation to future Coinbase prices than vice-versa).
    # We evaluate both combinations:
    # A) Binance Leads -> Coinbase Follows
    # B) Coinbase Leads -> Binance Follows (Lower fee follower)

    print("\n" + "="*160)
    print("PHASE 2: WALK-FORWARD VALIDATION OF 5 VARIANTS (K1 - K5) ACROSS 2022-2026")
    print("="*160)

    # We evaluate the primary configurations on BTC and ETH:
    # Configuration 1: Binance Leads -> Coinbase Follows (High fee hurdle)
    # Configuration 2: Coinbase Leads -> Binance Follows (Low fee hurdle)

    for config_name, lead_c, foll_c, lead_v, foll_v, foll_venue_name in [
        ("Binance -> Coinbase (BTC)", "ret_bin_5m", "close_cb", "Binance", "Coinbase", "coinbase"),
        ("Coinbase -> Binance (BTC)", "ret_cb_5m", "close_bin", "Coinbase", "Binance", "binance"),
        ("Binance -> Coinbase (ETH)", "ret_bin_5m", "close_cb", "Binance", "Coinbase", "coinbase"),
        ("Coinbase -> Binance (ETH)", "ret_cb_5m", "close_bin", "Coinbase", "Binance", "binance"),
    ]:
        df_target = df_btc if "BTC" in config_name else df_eth
        print(f"\n>>> CONFIGURATION: {config_name} <<<")
        variant_results = []

        for v_name, lag in VARIANTS_K:
            tr_train, c_info = simulate_cross_exchange_lead_lag(df_target, lead_c, foll_c, lag, '2022-01-01', '2023-12-31 23:55:00', foll_venue_name)
            tr_test, _ = simulate_cross_exchange_lead_lag(df_target, lead_c, foll_c, lag, '2024-01-01', '2024-12-31 23:55:00', foll_venue_name)
            tr_val, _ = simulate_cross_exchange_lead_lag(df_target, lead_c, foll_c, lag, '2024-01-01', '2026-08-16 23:55:00', foll_venue_name)
            tr_full, _ = simulate_cross_exchange_lead_lag(df_target, lead_c, foll_c, lag, '2022-01-01', '2026-08-16 23:55:00', foll_venue_name)

            m_train = evaluate_split(tr_train)
            m_test = evaluate_split(tr_test)
            m_val = evaluate_split(tr_val)
            m_full = evaluate_split(tr_full)

            tpy = round(m_full['trades'] / 4.62, 1)
            passed = (m_val['pf'] > 1.30) and (m_val['dd'] < 15.0) and (m_val['trades'] >= 100) and (m_val['exp'] > 0.0) and (m_val['net_edge_pct'] > 0.0)
            verdict = "PASSED (SURVIVOR)" if passed else "KILLED"

            variant_results.append({
                'variant': v_name,
                'lag_bars': lag,
                'lag_minutes': f"{lag*5}m",
                'hurdle_pct': f"{c_info['hurdle_pct']}%",
                'train_pf': m_train['pf'],
                'train_trades': m_train['trades'],
                'test_pf': m_test['pf'],
                'oos_pf': m_val['pf'],
                'oos_trades': m_val['trades'],
                'oos_wr': m_val['wr'],
                'oos_net_pnl': m_val['net_pnl'],
                'oos_exp': m_val['exp'],
                'oos_dd': m_val['dd'],
                'avg_gross_edge': m_val['avg_gross_edge'],
                'avg_fees': m_val['avg_fees'],
                'avg_slip': m_val['avg_slip'],
                'net_edge_pct': f"{m_val['net_edge_pct']}%",
                'trades_per_year': tpy,
                'year_distribution': str(m_full['year_dist']),
                'verdict': verdict
            })

        df_res = pd.DataFrame(variant_results)
        cols = ['variant', 'lag_minutes', 'hurdle_pct', 'train_pf', 'oos_pf', 'oos_trades', 'oos_wr', 'oos_net_pnl', 'oos_exp', 'oos_dd', 'avg_gross_edge', 'avg_fees', 'avg_slip', 'trades_per_year', 'verdict']
        print(df_res[cols].to_string(index=False))
        print(f"Yearly distribution (Full 2022-2026): {[r['year_distribution'] for r in variant_results]}")

    print("\n" + "="*160)


if __name__ == '__main__':
    main()
