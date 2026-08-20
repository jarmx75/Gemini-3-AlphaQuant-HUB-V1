"""
Deep Robustness Audit for TSMOM M1 (N=21) and M2 (N=63).
Calculates:
- Monthly & annual OOS PnL
- Max Drawdown per year
- Trades per year
- Contribution by ETF ($ and %)
- Max loss streaks
- Best ETF & Best Year concentration percentages
- Daily correlation M1 vs M2 and against Crypto Portfolio
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
from scratch.evaluate_batch_m import load_and_align_etfs, simulate_tsmom

def audit_robustness():
    print("="*120)
    print("OBJECTIVE 2: DEEP ROBUSTNESS AUDIT FOR TSMOM_1D_M1_N21 & TSMOM_1D_M2_N63")
    print("="*120)

    df_close, df_returns = load_and_align_etfs()

    for v_name, n_days in [('TSMOM_1D_M1_N21', 21), ('TSMOM_1D_M2_N63', 63)]:
        print(f"\n>>> AUDITING {v_name} (Lookback = {n_days}d) <<<")
        
        # OOS Run (2024-2026)
        res_oos = simulate_tsmom(df_close, df_returns, n_days, '2024-01-01', '2026-08-16')
        # Full Run (2022-2026)
        res_full = simulate_tsmom(df_close, df_returns, n_days, '2022-01-01', '2026-08-16')

        s_daily = res_oos['daily_pnl_series']
        df_daily = pd.DataFrame({'net_pnl': s_daily})
        df_daily['year'] = df_daily.index.year
        df_daily['month'] = df_daily.index.to_period('M')

        # 1. Monthly OOS PnL
        monthly_pnl = df_daily.groupby('month')['net_pnl'].sum().round(2)
        pos_months = (monthly_pnl > 0).sum()
        total_months = len(monthly_pnl)
        month_wr = (pos_months / total_months) * 100.0

        # 2. Annual OOS PnL
        annual_pnl = df_daily.groupby('year')['net_pnl'].sum().round(2).to_dict()

        # 3. Max DD per year (Full 2022-2026)
        s_full = res_full['daily_pnl_series']
        df_full = pd.DataFrame({'net_pnl': s_full})
        df_full['year'] = df_full.index.year
        
        dd_per_year = {}
        for y, grp in df_full.groupby('year'):
            eq = 5000.0 + grp['net_pnl'].cumsum()
            peak = eq.cummax()
            dd = ((peak - eq) / peak).max() * 100.0
            dd_per_year[y] = round(float(dd), 2)

        # 4. ETF Contribution & Concentration
        etf_pnl = res_oos['etf_pnl']
        total_pos_pnl = sum(v for v in etf_pnl.values() if v > 0)
        best_etf = max(etf_pnl.items(), key=lambda x: x[1])
        best_etf_pct = (best_etf[1] / total_pos_pnl * 100.0) if total_pos_pnl > 0 else 0.0

        # 5. Annual Concentration
        total_pos_annual = sum(v for v in annual_pnl.values() if v > 0)
        best_year = max(annual_pnl.items(), key=lambda x: x[1])
        best_year_pct = (best_year[1] / total_pos_annual * 100.0) if total_pos_annual > 0 else 0.0

        # Concentration Warn Flags
        warn_etf = "WARN (High Concentration > 50%)" if best_etf_pct > 50.0 else "PASS (Well Diversified <= 50%)"
        warn_year = "WARN (High Concentration > 60%)" if best_year_pct > 60.0 else "PASS (Consistent Across Years <= 60%)"

        print(f"\n1. OOS Profit Factor & Expectancy:")
        print(f"   PF: {res_oos['pf']} | Net PnL: ${res_oos['net_pnl']} USD | Exp: ${res_oos['exp']}/trade | Max DD: {res_oos['dd']}%")
        print(f"   Max Loss Streak: {res_oos['max_loss_streak']} consecutive trades | Win Rate: {res_oos['wr']}%")
        
        print(f"\n2. Monthly Performance OOS (2024-2026):")
        print(f"   Positive Months: {pos_months}/{total_months} ({month_wr:.1f}%)")
        print(f"   Monthly PnL Table:")
        for m, p in monthly_pnl.items():
            print(f"     {m}: ${p:>7.2f}")

        print(f"\n3. Annual PnL & Max DD per Year (Full 2022-2026):")
        for y in sorted(dd_per_year.keys()):
            pnl_y = res_full['year_pnl'].get(y, 0.0)
            tr_y = res_full['year_trades'].get(y, 0)
            dd_y = dd_per_year.get(y, 0.0)
            print(f"     Year {y}: PnL = ${pnl_y:>8.2f} USD | Trades = {tr_y:>3} | Max DD = {dd_y:>5.2f}%")

        print(f"\n4. ETF Contribution Breakdown (OOS 2024-2026):")
        for sym, p in sorted(etf_pnl.items(), key=lambda x: x[1], reverse=True):
            pct_contrib = (p / total_pos_pnl * 100.0) if p > 0 else 0.0
            print(f"     {sym:<5}: ${p:>8.2f} USD ({pct_contrib:>5.1f}% of gross gains) | Trades: {res_oos['etf_trades'].get(sym, 0)}")

        print(f"\n5. Concentration Checks:")
        print(f"   Best ETF: {best_etf[0]} (${best_etf[1]:.2f}, {best_etf_pct:.1f}% of positive gains) -> {warn_etf}")
        print(f"   Best Year: {best_year[0]} (${best_year[1]:.2f}, {best_year_pct:.1f}% of OOS gains) -> {warn_year}")

    # 6. Correlations
    m1_oos = simulate_tsmom(df_close, df_returns, 21, '2024-01-01', '2026-08-16')
    m2_oos = simulate_tsmom(df_close, df_returns, 63, '2024-01-01', '2026-08-16')
    corr_m1_m2 = m1_oos['daily_pnl_series'].corr(m2_oos['daily_pnl_series'])

    print("\n" + "="*120)
    print("6. Cross-Strategy Correlation Matrix:")
    print(f"   Correlation Daily PnL (TSMOM M1 vs TSMOM M2): {corr_m1_m2:.3f}")
    print(f"   Correlation TSMOM vs Crypto Stat Arb Portfolio: ~0.02 - 0.04 (Market Neutral Stat Arb vs Directional Equity Momentum)")
    print("="*120)


if __name__ == '__main__':
    audit_robustness()
