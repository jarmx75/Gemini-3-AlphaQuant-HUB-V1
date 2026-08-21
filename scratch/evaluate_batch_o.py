"""
Batch O — SEC Insider Cluster Buying Strategy Evaluator
Fast & Robust Evaluation using Active Liquid US Stocks
"""

import os
import zipfile
import json
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical_insiders"

def load_sec_form4_purchases() -> pd.DataFrame:
    zip_files = sorted(list(DATA_DIR.glob("*_form345.zip")))
    subs_list, trans_list, owners_list = [], [], []

    for zp in zip_files:
        try:
            with zipfile.ZipFile(zp) as z:
                if 'SUBMISSION.tsv' in z.namelist():
                    df_sub = pd.read_csv(z.open('SUBMISSION.tsv'), sep='\t', low_memory=False,
                                         usecols=['ACCESSION_NUMBER', 'FILING_DATE', 'DOCUMENT_TYPE', 'ISSUERCIK', 'ISSUERTRADINGSYMBOL'])
                    df_sub = df_sub[df_sub['DOCUMENT_TYPE'] == '4']
                    subs_list.append(df_sub)

                if 'NONDERIV_TRANS.tsv' in z.namelist():
                    df_tr = pd.read_csv(z.open('NONDERIV_TRANS.tsv'), sep='\t', low_memory=False,
                                        usecols=['ACCESSION_NUMBER', 'TRANS_DATE', 'TRANS_CODE', 'TRANS_SHARES', 'TRANS_PRICEPERSHARE', 'TRANS_ACQUIRED_DISP_CD'])
                    df_tr = df_tr[(df_tr['TRANS_CODE'] == 'P') & (df_tr['TRANS_ACQUIRED_DISP_CD'] == 'A')]
                    df_tr = df_tr[(df_tr['TRANS_PRICEPERSHARE'] > 1.0) & (df_tr['TRANS_SHARES'] > 0)]
                    trans_list.append(df_tr)

                if 'REPORTINGOWNER.tsv' in z.namelist():
                    df_ow = pd.read_csv(z.open('REPORTINGOWNER.tsv'), sep='\t', low_memory=False,
                                        usecols=['ACCESSION_NUMBER', 'RPTOWNERCIK'])
                    owners_list.append(df_ow)
        except Exception:
            pass

    df_subs = pd.concat(subs_list, ignore_index=True).drop_duplicates()
    df_trans = pd.concat(trans_list, ignore_index=True)
    df_owners = pd.concat(owners_list, ignore_index=True).drop_duplicates()

    merged = df_trans.merge(df_subs, on='ACCESSION_NUMBER', how='inner')
    merged = merged.merge(df_owners, on='ACCESSION_NUMBER', how='inner')

    merged['FILING_DATE'] = pd.to_datetime(merged['FILING_DATE'], format='%d-%b-%Y', errors='coerce')
    merged['TRANS_DATE'] = pd.to_datetime(merged['TRANS_DATE'], format='%d-%b-%Y', errors='coerce')
    merged['ISSUERTRADINGSYMBOL'] = merged['ISSUERTRADINGSYMBOL'].astype(str).str.upper().str.strip()
    merged = merged[merged['ISSUERTRADINGSYMBOL'].str.match(r'^[A-Z]{1,5}$', na=False)]
    merged = merged.dropna(subset=['FILING_DATE', 'ISSUERTRADINGSYMBOL', 'RPTOWNERCIK'])

    return merged

def fast_cluster_extraction(df: pd.DataFrame, window_days: int, min_insiders: int) -> pd.DataFrame:
    df_uniq = df[['ISSUERTRADINGSYMBOL', 'FILING_DATE', 'RPTOWNERCIK']].drop_duplicates()
    sym_counts = df_uniq.groupby('ISSUERTRADINGSYMBOL')['RPTOWNERCIK'].nunique()
    valid_syms = sym_counts[sym_counts >= min_insiders].index
    df_filtered = df_uniq[df_uniq['ISSUERTRADINGSYMBOL'].isin(valid_syms)]

    signals = []
    for sym, group in df_filtered.groupby('ISSUERTRADINGSYMBOL'):
        group = group.sort_values('FILING_DATE')
        filing_dates = group['FILING_DATE'].unique()
        
        last_sig_date = None
        for fdate in filing_dates:
            if last_sig_date is not None and (pd.to_datetime(fdate) - pd.to_datetime(last_sig_date)).days <= window_days:
                continue
            
            fdate_start = pd.to_datetime(fdate) - pd.Timedelta(days=window_days)
            sub = group[(group['FILING_DATE'] >= fdate_start) & (group['FILING_DATE'] <= fdate)]
            n_insiders = sub['RPTOWNERCIK'].nunique()
            
            if n_insiders >= min_insiders:
                signals.append({
                    'symbol': sym,
                    'filing_date': pd.to_datetime(fdate),
                    'insiders_count': n_insiders
                })
                last_sig_date = fdate

    return pd.DataFrame(signals) if signals else pd.DataFrame()

def main():
    print("=== BATCH O — SEC INSIDER CLUSTER BUYING EVALUATION ===")
    df_sec = load_sec_form4_purchases()
    print(f"Loaded {len(df_sec):,} purchase records across {df_sec['ISSUERTRADINGSYMBOL'].nunique():,} tickers.")

    variants = {
        'O1': {'window': 5, 'insiders': 2},
        'O2': {'window': 10, 'insiders': 2},
        'O3': {'window': 20, 'insiders': 2},
        'O4': {'window': 10, 'insiders': 3},
        'O5': {'window': 20, 'insiders': 3},
    }

    # Extract all variant signals
    variant_signals = {}
    all_symbols = set()
    for var_id, spec in variants.items():
        sig_df = fast_cluster_extraction(df_sec, spec['window'], spec['insiders'])
        variant_signals[var_id] = sig_df
        if not sig_df.empty:
            all_symbols.update(sig_df['symbol'].unique())
        print(f"Variant {var_id} (Insiders>={spec['insiders']}, Window={spec['window']}d): {len(sig_df):,} signals across {sig_df['symbol'].nunique() if not sig_df.empty else 0} tickers.")

    # High liquidity active stocks list to avoid delisted timeouts
    active_stocks = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'AMD', 'INTC', 'JPM', 'BAC', 
        'GS', 'WFC', 'C', 'XOM', 'CVX', 'COP', 'PFE', 'JNJ', 'UNH', 'MRK', 
        'ABBV', 'LLY', 'PG', 'KO', 'PEP', 'WMT', 'COST', 'HD', 'DIS', 'NFLX', 
        'META', 'CRM', 'ORCL', 'CSCO', 'IBM', 'CAT', 'DE', 'GE', 'HON', 'MMM', 
        'LMT', 'BA', 'NKE', 'SBUX', 'MCD', 'LOW', 'T', 'VZ', 'MAR', 'HLT',
        'SCHW', 'MS', 'AXP', 'BLK', 'SYK', 'MDLZ', 'TXN', 'QCOM', 'AVGO', 'NOW',
        'AMAT', 'LRCX', 'ADI', 'PANW', 'SNPS', 'CDNS', 'KLAC', 'MCHP', 'ON', 'MU',
        'SLB', 'EOG', 'PXD', 'OXY', 'MPC', 'VLO', 'PSX', 'HAL', 'DVN', 'FANG',
        'ETN', 'ITW', 'EMR', 'PH', 'CMI', 'ROK', 'IR', 'AME', 'FAST', 'ODFL'
    ]

    # Intersect cluster symbols with active liquid stocks
    eval_symbols = [s for s in active_stocks if s in all_symbols]
    if len(eval_symbols) < 30:
        # Include top symbols present in cluster signals
        eval_symbols = list(all_symbols)[:60]

    print(f"\nDownloading price data for {len(eval_symbols)} active tickers...")
    df_prices = yf.download(eval_symbols, start="2022-01-01", end="2026-07-01", progress=False, group_by='ticker')

    price_data = {}
    for sym in eval_symbols:
        try:
            px = df_prices[sym].copy() if len(eval_symbols) > 1 else df_prices.copy()
            px = px.dropna(subset=['Close', 'Open'])
            if len(px) > 20:
                price_data[sym] = px
        except Exception:
            pass

    print(f"Loaded active price data for {len(price_data)} tickers.")

    fee_rate, slip_rate = 0.0010, 0.0010
    friction = fee_rate + slip_rate

    all_results = {}

    for var_id, df_sig in variant_signals.items():
        if df_sig.empty:
            continue

        df_sub = df_sig[df_sig['symbol'].isin(price_data.keys())].copy()
        trades = []
        lookahead_violations = 0

        for _, sig in df_sub.iterrows():
            sym = sig['symbol']
            fdate = sig['filing_date']
            px = price_data[sym]

            post_px = px[px.index > fdate]
            if len(post_px) < 21:
                continue

            entry_dt = post_px.index[0]
            entry_p = float(post_px.iloc[0]['Open'])

            # Look-Ahead Audit assertion
            if fdate >= entry_dt:
                lookahead_violations += 1
                continue

            exit_dt = post_px.index[20]
            exit_p = float(post_px.iloc[20]['Close'])

            ret_1d = (float(post_px.iloc[1]['Close']) - entry_p) / entry_p
            ret_5d = (float(post_px.iloc[5]['Close']) - entry_p) / entry_p
            ret_10d = (float(post_px.iloc[10]['Close']) - entry_p) / entry_p
            ret_20d = (exit_p - entry_p) / entry_p

            gross_ret = ret_20d
            net_ret = gross_ret - friction

            trades.append({
                'symbol': sym,
                'filing_date': fdate,
                'entry_date': entry_dt,
                'exit_date': exit_dt,
                'entry_price': entry_p,
                'exit_price': exit_p,
                'gross_ret': gross_ret,
                'net_ret': net_ret,
                'ret_1d': ret_1d,
                'ret_5d': ret_5d,
                'ret_10d': ret_10d,
                'ret_20d': ret_20d,
                'year': entry_dt.year
            })

        df_tr = pd.DataFrame(trades)
        if df_tr.empty:
            continue

        df_train = df_tr[df_tr['year'].isin([2022, 2023])]
        df_oos = df_tr[df_tr['year'].isin([2024, 2025, 2026])]

        def get_metrics(d):
            if d.empty:
                return {'pf': 0.0, 'dd': 0.0, 'trades': 0, 'exp': 0.0, 'win_rate': 0.0, 'net_pnl': 0.0}
            g = d[d['net_ret'] > 0]['net_ret'].sum()
            l = abs(d[d['net_ret'] < 0]['net_ret'].sum())
            pf = g / l if l > 0 else (99.0 if g > 0 else 0.0)
            cum = (1 + d['net_ret']).cumprod()
            dd = abs(float(((cum - cum.cummax()) / cum.cummax()).min())) * 100
            return {
                'pf': round(pf, 2),
                'dd': round(dd, 2),
                'trades': len(d),
                'exp': round(float(d['net_ret'].mean()) * 100, 2),
                'win_rate': round(float((d['net_ret'] > 0).mean()) * 100, 2),
                'net_pnl': round(float(d['net_ret'].sum()) * 100, 2)
            }

        tr_m = get_metrics(df_train)
        oos_m = get_metrics(df_oos)

        event_study = {
            '1d_mean_pct': round(float(df_oos['ret_1d'].mean() * 100), 2) if not df_oos.empty else 0.0,
            '5d_mean_pct': round(float(df_oos['ret_5d'].mean() * 100), 2) if not df_oos.empty else 0.0,
            '10d_mean_pct': round(float(df_oos['ret_10d'].mean() * 100), 2) if not df_oos.empty else 0.0,
            '20d_mean_pct': round(float(df_oos['ret_20d'].mean() * 100), 2) if not df_oos.empty else 0.0,
        }

        yr_pnl = df_oos.groupby('year')['net_ret'].sum() if not df_oos.empty else pd.Series()
        tot_pnl = yr_pnl.sum()
        max_yr_share = (yr_pnl.max() / tot_pnl * 100) if tot_pnl > 0 else 0.0

        stk_pnl = df_oos.groupby('symbol')['net_ret'].sum().sort_values(ascending=False) if not df_oos.empty else pd.Series()
        top5_stk_share = (stk_pnl.head(5).sum() / tot_pnl * 100) if tot_pnl > 0 else 0.0

        killer_passed = (
            oos_m['pf'] > 1.30 and
            oos_m['dd'] < 15.0 and
            oos_m['trades'] > 100 and
            oos_m['exp'] > 0 and
            max_yr_share < 60.0 and
            top5_stk_share < 50.0 and
            lookahead_violations == 0
        )

        all_results[var_id] = {
            'train': tr_m,
            'oos': oos_m,
            'event_study': event_study,
            'max_year_share_pct': round(float(max_yr_share), 2),
            'top5_stock_share_pct': round(float(top5_stk_share), 2),
            'lookahead_violations': int(lookahead_violations),
            'verdict': 'SURVIVOR' if killer_passed else 'REJECTED'
        }

        print(f"\nVariant {var_id}:")
        print(f"  TRAIN: PF={tr_m['pf']} | DD={tr_m['dd']}% | Trades={tr_m['trades']} | Exp={tr_m['exp']}%")
        print(f"  OOS:   PF={oos_m['pf']} | DD={oos_m['dd']}% | Trades={oos_m['trades']} | Exp={oos_m['exp']}%")
        print(f"  Event Study (OOS): 1d={event_study['1d_mean_pct']}%, 5d={event_study['5d_mean_pct']}%, 10d={event_study['10d_mean_pct']}%, 20d={event_study['20d_mean_pct']}%")
        print(f"  Verdict: {'SURVIVOR' if killer_passed else 'REJECTED'}")

    res_file = DATA_DIR / "batch_o_results.json"
    with open(res_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved Batch O evaluation results to {res_file}")

if __name__ == '__main__':
    main()
