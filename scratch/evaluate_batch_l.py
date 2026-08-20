"""
Batch L: Equity Overnight Gap Reversal Strategy Engine (2022-2026)
Universe: SPY, QQQ, IWM, XLF, XLK, XLE, GLD, TLT

Variants:
- L1: Gap <= -0.75%
- L2: Gap <= -1.00%
- L3: Gap <= -1.25%
- L4: Gap <= -1.50%
- L5: Gap <= -2.00%

Safety filter: Exclude gaps >= 8.0%
Friction: 0.16% roundtrip fees + 0.02% roundtrip slippage = 0.18% total
Notional: $300 USD per trade
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical_equities"

ETFS = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "GLD", "TLT"]

VARIANTS_L = [
    ('L1', 0.0075),
    ('L2', 0.0100),
    ('L3', 0.0125),
    ('L4', 0.0150),
    ('L5', 0.0200)
]


def load_etf_data() -> Dict[str, pd.DataFrame]:
    dfs = {}
    for sym in ETFS:
        file_path = DATA_DIR / f"{sym}_1d_2022_2026.csv"
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate overnight gap
        df['prev_close'] = df['close'].shift(1)
        df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
        df['intraday_ret'] = (df['close'] - df['open']) / df['open']
        df['gap_dollar'] = df['prev_close'] - df['open']
        df['intraday_dollar'] = df['close'] - df['open']
        
        # Recovery %: how much of the overnight gap was recovered intraday
        # If gap_dollar > 0 (down gap), recovery = intraday_dollar / gap_dollar
        df['recovery_pct'] = np.where(
            df['gap_dollar'] > 0,
            (df['intraday_dollar'] / df['gap_dollar']) * 100.0,
            0.0
        )
        dfs[sym] = df
    return dfs


def simulate_gap_reversal(
    dfs: Dict[str, pd.DataFrame],
    threshold: float,
    start_date: str,
    end_date: str,
    notional: float = 300.0,
    fee_rate: float = 0.0016,
    slippage_rate: float = 0.0002
) -> List[Dict[str, Any]]:
    trades = []
    
    for sym, df in dfs.items():
        df_slice = df[(df['date'] >= start_date) & (df['date'] <= end_date)].dropna(subset=['gap']).reset_index(drop=True)
        
        for _, row in df_slice.iterrows():
            gap = row['gap']
            # Entry condition: Gap <= -threshold and |Gap| < 8.0% safety limit
            if gap <= -threshold and abs(gap) < 0.08:
                intraday_ret = row['intraday_ret']
                gross_pnl = intraday_ret * notional
                fees = notional * fee_rate
                slippage = notional * slippage_rate
                net_pnl = gross_pnl - fees - slippage
                
                trades.append({
                    'symbol': sym,
                    'date': row['date'],
                    'year': row['date'].year,
                    'gap_pct': gap * 100.0,
                    'intraday_ret_pct': intraday_ret * 100.0,
                    'recovery_pct': row['recovery_pct'],
                    'gross_pnl': gross_pnl,
                    'fees': fees,
                    'slippage': slippage,
                    'net_pnl': net_pnl
                })
                
    trades.sort(key=lambda t: t['date'])
    return trades


def evaluate_split(trades: List[Dict[str, Any]], initial_cap: float = 5000.0) -> Dict[str, Any]:
    if not trades:
        return {
            'pf': 0.0, 'trades': 0, 'wr': 0.0, 'net_pnl': 0.0, 'exp': 0.0, 'dd': 0.0,
            'avg_gap': 0.0, 'avg_recovery': 0.0, 'avg_fees': 0.0, 'avg_slip': 0.0,
            'max_loss_streak': 0, 'etf_pnl': {}, 'etf_trades': {}, 'year_dist': {}
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
            
    etf_pnl = df.groupby('symbol')['net_pnl'].sum().round(2).to_dict()
    etf_trades = df['symbol'].value_counts().to_dict()
    year_dist = df['year'].value_counts().to_dict()
    
    return {
        'pf': round(pf, 2),
        'trades': len(df),
        'wr': round(wr, 1),
        'net_pnl': round(net_pnl, 2),
        'exp': round(exp, 2),
        'dd': round(max_dd_pct, 2),
        'avg_gap': round(df['gap_pct'].mean(), 2),
        'avg_recovery': round(df['recovery_pct'].mean(), 1),
        'avg_fees': round(df['fees'].mean(), 2),
        'avg_slip': round(df['slippage'].mean(), 2),
        'max_loss_streak': max_streak,
        'etf_pnl': etf_pnl,
        'etf_trades': etf_trades,
        'year_dist': year_dist
    }


def main():
    print("="*140)
    print("BATCH L: EQUITY OVERNIGHT GAP REVERSAL (2022-2026)")
    print("Universe: SPY, QQQ, IWM, XLF, XLK, XLE, GLD, TLT")
    print("="*140)
    
    dfs = load_etf_data()
    summary = []
    
    for v_name, thresh in VARIANTS_L:
        thresh_pct = thresh * 100.0
        tr_train = simulate_gap_reversal(dfs, thresh, '2022-01-01', '2023-12-31')
        tr_test = simulate_gap_reversal(dfs, thresh, '2024-01-01', '2024-12-31')
        tr_val = simulate_gap_reversal(dfs, thresh, '2024-01-01', '2026-08-16')
        tr_full = simulate_gap_reversal(dfs, thresh, '2022-01-01', '2026-08-16')
        
        m_train = evaluate_split(tr_train)
        m_test = evaluate_split(tr_test)
        m_val = evaluate_split(tr_val)
        m_full = evaluate_split(tr_full)
        
        tpy = round(m_full['trades'] / 4.62, 1)
        passed = (m_val['pf'] > 1.30) and (m_val['dd'] < 15.0) and (m_val['trades'] >= 100) and (m_val['exp'] > 0.0)
        verdict = "PASSED (SURVIVOR)" if passed else "KILLED"
        
        summary.append({
            'variant': v_name,
            'gap_threshold': f"<=-{thresh_pct:.2f}%",
            'train_pf': m_train['pf'],
            'train_trades': m_train['trades'],
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
            'avg_gap': f"{m_val['avg_gap']}%",
            'avg_recovery': f"{m_val['avg_recovery']}%",
            'avg_fees': m_val['avg_fees'],
            'avg_slip': m_val['avg_slip'],
            'etf_pnl_oos': m_val['etf_pnl'],
            'etf_trades_oos': m_val['etf_trades'],
            'yearly_trades_full': m_full['year_dist'],
            'verdict': verdict
        })
        
    df_sum = pd.DataFrame(summary)
    
    print("\n" + "="*160)
    print("BATCH L: WALK-FORWARD OOS RESULTS ACROSS ALL 5 GAP VARIANTS (L1 - L5)")
    print("="*160)
    cols = ['variant', 'gap_threshold', 'train_pf', 'test_pf', 'oos_pf', 'oos_trades', 'oos_wr', 'oos_net_pnl', 'oos_exp', 'oos_dd', 'oos_loss_streak', 'full_trades', 'trades_per_year', 'avg_gap', 'avg_recovery', 'verdict']
    print(df_sum[cols].to_string(index=False))
    print("="*160)
    
    for r in summary:
        print(f"\n[{r['variant']} ({r['gap_threshold']})] OOS Details:")
        print(f"  ETF PnL Breakdown: {r['etf_pnl_oos']}")
        print(f"  ETF Trade Counts: {r['etf_trades_oos']}")
        print(f"  Annual Trade Distribution (Full): {r['yearly_trades_full']}")
        
    # Save to json
    output_path = PROJECT_ROOT / "logs" / "paper" / "batch_l_evaluation.json"
    df_sum.to_json(output_path, orient="records", indent=2)
    print(f"\nSaved Batch L results to {output_path}")


if __name__ == '__main__':
    main()
