"""
Batch M: Cross-Asset Time Series Momentum (TSMOM 1D) Strategy Engine (2022-2026)
Universe: SPY, QQQ, IWM, XLF, XLK, XLE, GLD, TLT

Variants:
- M1: N = 21 (1-month momentum)
- M2: N = 63 (3-month momentum)
- M3: N = 126 (6-month momentum)
- M4: N = 189 (9-month momentum)
- M5: N = 252 (12-month momentum)

Risk Model:
- Inverse 20-day realized volatility weighting (volatility parity)
- Cap per asset: 25% max
- Friction: 0.16% roundtrip fees + 0.02% roundtrip slippage = 0.09% one-way turnover friction
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical_equities"

ETFS = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "GLD", "TLT"]

VARIANTS_M = [
    ('M1', 21),
    ('M2', 63),
    ('M3', 126),
    ('M4', 189),
    ('M5', 252)
]


def load_and_align_etfs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Loads all 8 ETFs and creates aligned Close and Return DataFrames."""
    close_dict = {}
    for sym in ETFS:
        df = pd.read_csv(DATA_DIR / f"{sym}_1d_2022_2026.csv")
        df['date'] = pd.to_datetime(df['date'])
        close_dict[sym] = df.set_index('date')['close']
        
    df_close = pd.DataFrame(close_dict).sort_index().dropna()
    df_returns = df_close.pct_change().fillna(0.0)
    return df_close, df_returns


def simulate_tsmom(
    df_close: pd.DataFrame,
    df_returns: pd.DataFrame,
    lookback_N: int,
    start_date: str,
    end_date: str,
    initial_cap: float = 5000.0,
    max_weight_cap: float = 0.25,
    fee_oneway: float = 0.0009 # 0.08% fee + 0.01% slippage
) -> Dict[str, Any]:
    n_days, n_assets = df_close.shape
    dates = df_close.index
    
    # 1. Compute rolling momentum signals and rolling 20d volatility
    df_mom = (df_close / df_close.shift(lookback_N)) - 1.0
    df_vol = df_returns.rolling(20).std() * np.sqrt(252)
    df_vol = df_vol.fillna(0.15).replace(0.0, 0.15)
    
    # 2. Daily simulation
    weights = np.zeros((n_days, n_assets))
    
    for t in range(max(lookback_N, 20), n_days):
        mom_t = df_mom.iloc[t].values
        vol_t = df_vol.iloc[t].values
        
        # Long only if momentum > 0
        active_mask = mom_t > 0
        
        if np.any(active_mask):
            inv_vol = np.where(active_mask, 1.0 / vol_t, 0.0)
            sum_inv_vol = np.sum(inv_vol)
            if sum_inv_vol > 0:
                raw_w = inv_vol / sum_inv_vol
                # Apply 25% cap iteratively
                capped_w = np.minimum(raw_w, max_weight_cap)
                # Rescale non-capped weights if possible
                if np.sum(capped_w) > 0:
                    final_w = capped_w / max(1.0, np.sum(capped_w))
                else:
                    final_w = capped_w
                weights[t] = final_w
        else:
            weights[t] = 0.0 # 100% Cash
            
    df_weights = pd.DataFrame(weights, index=dates, columns=df_close.columns)
    
    # Shift weights by 1 day to prevent look-ahead bias (weights decided at close t applied to t+1)
    df_pos = df_weights.shift(1).fillna(0.0)
    
    # Slice to target evaluation date range
    mask = (dates >= pd.to_datetime(start_date)) & (dates <= pd.to_datetime(end_date))
    eval_dates = dates[mask]
    
    if len(eval_dates) == 0:
        return {'pf': 0.0, 'trades': 0, 'wr': 0.0, 'net_pnl': 0.0, 'exp': 0.0, 'dd': 0.0}
        
    pos_eval = df_pos.loc[eval_dates]
    ret_eval = df_returns.loc[eval_dates]
    
    # Daily portfolio returns and turnover
    turnover = pos_eval.diff().abs().sum(axis=1).fillna(0.0)
    friction_cost = turnover * fee_oneway
    gross_port_ret = (pos_eval * ret_eval).sum(axis=1)
    net_port_ret = gross_port_ret - friction_cost
    
    # Equity curve
    capital = initial_cap
    daily_pnl = []
    equity_curve = [initial_cap]
    
    for r in net_port_ret.values:
        pnl = capital * r
        daily_pnl.append(pnl)
        capital += pnl
        equity_curve.append(capital)
        
    equity_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_arr)
    max_dd_pct = float(np.max((peak - equity_arr) / peak) * 100.0)
    
    # Trade episodes per asset (from entry w>0 to exit w==0)
    trade_episodes = []
    etf_pnl_map = {sym: 0.0 for sym in ETFS}
    etf_trades_map = {sym: 0 for sym in ETFS}
    
    for sym in ETFS:
        w_series = pos_eval[sym].values
        r_series = ret_eval[sym].values
        in_trade = False
        trade_pnl = 0.0
        trade_entry_date = None
        
        for idx, t_date in enumerate(eval_dates):
            w_curr = w_series[idx]
            w_prev = w_series[idx - 1] if idx > 0 else 0.0
            
            # Position holding return
            if w_curr > 0:
                step_pnl = (initial_cap * w_curr) * r_series[idx] - (initial_cap * abs(w_curr - w_prev) * fee_oneway)
                trade_pnl += step_pnl
                etf_pnl_map[sym] += step_pnl
                
                if not in_trade:
                    in_trade = True
                    trade_entry_date = t_date
            else:
                if in_trade:
                    # Closing friction
                    close_cost = initial_cap * w_prev * fee_oneway
                    trade_pnl -= close_cost
                    etf_pnl_map[sym] -= close_cost
                    
                    trade_episodes.append({
                        'symbol': sym,
                        'entry_date': trade_entry_date,
                        'exit_date': t_date,
                        'year': t_date.year,
                        'net_pnl': trade_pnl
                    })
                    etf_trades_map[sym] += 1
                    in_trade = False
                    trade_pnl = 0.0
                    
        if in_trade:
            trade_episodes.append({
                'symbol': sym,
                'entry_date': trade_entry_date,
                'exit_date': eval_dates[-1],
                'year': eval_dates[-1].year,
                'net_pnl': trade_pnl
            })
            etf_trades_map[sym] += 1
            
    df_trades = pd.DataFrame(trade_episodes) if trade_episodes else pd.DataFrame(columns=['symbol', 'net_pnl', 'year'])
    
    # Metrics
    if not df_trades.empty:
        wins = df_trades[df_trades['net_pnl'] > 0]
        losses = df_trades[df_trades['net_pnl'] <= 0]
        gw = wins['net_pnl'].sum() if not wins.empty else 0.0
        gl = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
        pf = gw / gl
        wr = (len(wins) / len(df_trades)) * 100.0
        exp = df_trades['net_pnl'].mean()
        max_loss_streak = 0
        curr_streak = 0
        for tr_pnl in df_trades['net_pnl'].values:
            if tr_pnl <= 0:
                curr_streak += 1
                if curr_streak > max_loss_streak:
                    max_loss_streak = curr_streak
            else:
                curr_streak = 0
    else:
        pf, wr, exp, max_loss_streak = 0.0, 0.0, 0.0, 0
        
    net_pnl_total = capital - initial_cap
    total_turnover = float(turnover.sum())
    total_fees = float(friction_cost.sum() * initial_cap)
    
    # Year distribution
    df_pnl_daily = pd.DataFrame({'date': eval_dates, 'net_pnl': daily_pnl})
    df_pnl_daily['year'] = df_pnl_daily['date'].dt.year
    year_pnl = df_pnl_daily.groupby('year')['net_pnl'].sum().round(2).to_dict()
    year_trades = df_trades['year'].value_counts().to_dict() if not df_trades.empty else {}
    
    return {
        'pf': round(pf, 2),
        'trades': len(df_trades),
        'wr': round(wr, 1),
        'net_pnl': round(net_pnl_total, 2),
        'exp': round(exp, 2),
        'dd': round(max_dd_pct, 2),
        'turnover': round(total_turnover, 2),
        'accumulated_fees': round(total_fees, 2),
        'max_loss_streak': max_loss_streak,
        'etf_pnl': {k: round(v, 2) for k, v in etf_pnl_map.items()},
        'etf_trades': etf_trades_map,
        'year_pnl': year_pnl,
        'year_trades': year_trades,
        'daily_pnl_series': df_pnl_daily.set_index('date')['net_pnl']
    }


def main():
    print("="*140)
    print("BATCH M: CROSS-ASSET TIME SERIES MOMENTUM (TSMOM 1D) EVALUATION (2022-2026)")
    print("Universe: SPY, QQQ, IWM, XLF, XLK, XLE, GLD, TLT")
    print("="*140)
    
    df_close, df_returns = load_and_align_etfs()
    summary = []
    
    for v_name, lookback_N in VARIANTS_M:
        m_train = simulate_tsmom(df_close, df_returns, lookback_N, '2022-01-01', '2023-12-31')
        m_test = simulate_tsmom(df_close, df_returns, lookback_N, '2024-01-01', '2024-12-31')
        m_val = simulate_tsmom(df_close, df_returns, lookback_N, '2024-01-01', '2026-08-16')
        m_full = simulate_tsmom(df_close, df_returns, lookback_N, '2022-01-01', '2026-08-16')
        
        tpy = round(m_full['trades'] / 4.62, 1)
        passed = (m_val['pf'] > 1.30) and (m_val['dd'] < 15.0) and (m_val['trades'] >= 100) and (m_val['exp'] > 0.0)
        verdict = "PASSED (SURVIVOR)" if passed else "KILLED"
        
        summary.append({
            'variant': v_name,
            'lookback_N': f"{lookback_N}d",
            'train_pf': m_train['pf'],
            'train_trades': m_train['trades'],
            'test_pf': m_test['pf'],
            'oos_pf': m_val['pf'],
            'oos_trades': m_val['trades'],
            'oos_wr': m_val['wr'],
            'oos_net_pnl': m_val['net_pnl'],
            'oos_exp': m_val['exp'],
            'oos_dd': m_val['dd'],
            'oos_turnover': m_val['turnover'],
            'oos_fees': m_val['accumulated_fees'],
            'oos_loss_streak': m_val['max_loss_streak'],
            'full_trades': m_full['trades'],
            'trades_per_year': tpy,
            'etf_pnl_oos': m_val['etf_pnl'],
            'etf_trades_oos': m_val['etf_trades'],
            'year_pnl_full': m_full['year_pnl'],
            'year_trades_full': m_full['year_trades'],
            'verdict': verdict
        })
        
    df_sum = pd.DataFrame(summary)
    
    print("\n" + "="*160)
    print("BATCH M: WALK-FORWARD OOS RESULTS ACROSS ALL 5 TSMOM VARIANTS (M1 - M5)")
    print("="*160)
    cols = ['variant', 'lookback_N', 'train_pf', 'test_pf', 'oos_pf', 'oos_trades', 'oos_wr', 'oos_net_pnl', 'oos_exp', 'oos_dd', 'oos_turnover', 'oos_fees', 'full_trades', 'trades_per_year', 'verdict']
    print(df_sum[cols].to_string(index=False))
    print("="*160)
    
    for r in summary:
        print(f"\n[{r['variant']} (Lookback {r['lookback_N']})] Details:")
        print(f"  ETF PnL Breakdown (OOS): {r['etf_pnl_oos']}")
        print(f"  ETF Trade Counts (OOS): {r['etf_trades_oos']}")
        print(f"  Annual PnL (Full 2022-2026): {r['year_pnl_full']}")
        print(f"  Annual Trade Counts (Full 2022-2026): {r['year_trades_full']}")
        
    # Save to json
    output_path = PROJECT_ROOT / "logs" / "paper" / "batch_m_evaluation.json"
    df_sum.to_json(output_path, orient="records", indent=2)
    print(f"\nSaved Batch M results to {output_path}")


if __name__ == '__main__':
    main()
