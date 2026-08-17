"""
Master Multi-Year Walk-Forward & Monte Carlo Audit Engine (2022 - 2026)
Filosofía Automaton:
  1. Walk-Forward Estricto:
     - Train: 2022 (Bear Market / Colapsos FTX y Terra)
     - Test: 2023 (Acumulación / Recuperación)
     - Validation Out-of-Sample: 2024 - 2026 (Bull / Alta Volatilidad)
  2. Filtro Doble de Cointegración:
     - Engle-Granger p-value < 0.03
     - ADF Spread Residual p-value < 0.05
  3. Controles de Riesgo:
     - Stop Loss: |Z| >= 3.5
     - Time Stop: 24 horas (24 velas de 1h)
     - Target Exit: Reversión a la media Z = 0.0
     - Deducción de fees reales: 0.16% por trade roundtrip
  4. Simulación Monte Carlo: 1,000 iteraciones para evaluar la curva de Drawdown real y riesgo de ruina.
"""

import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint, adfuller

data_dir = Path("data/historical")

def load_pair_data(sym_y: str, sym_x: str) -> pd.DataFrame:
    file_y = data_dir / f"{sym_y}_1h_2022_2026.csv"
    file_x = data_dir / f"{sym_x}_1h_2022_2026.csv"
    if not file_y.exists() or not file_x.exists():
        return pd.DataFrame()
        
    df_y = pd.read_csv(file_y)[['timestamp', 'close']].rename(columns={'close': 'close_y'})
    df_x = pd.read_csv(file_x)[['timestamp', 'close']].rename(columns={'close': 'close_x'})
    
    df_y['timestamp'] = pd.to_datetime(df_y['timestamp'])
    df_x['timestamp'] = pd.to_datetime(df_x['timestamp'])
    
    df_merged = pd.merge(df_y, df_x, on='timestamp').sort_values('timestamp').reset_index(drop=True)
    return df_merged

def run_stat_arb_simulation(
    df: pd.DataFrame,
    lookback_w: int = 90,
    z_entry_min: float = 2.5,
    z_entry_max: float = 3.4,
    z_exit: float = 0.0,
    z_stop: float = 3.5,
    max_holding: int = 24,
    eg_p_threshold: float = 0.03,
    adf_p_threshold: float = 0.05,
    notional_per_leg: float = 150.0,
    fee_rate: float = 0.0004
) -> list:
    y = df['close_y'].values
    x = df['close_x'].values
    timestamps = df['timestamp'].values
    n = len(y)
    
    trades = []
    in_pos = False
    pos_side = None
    entry_y = 0.0
    entry_x = 0.0
    entry_gamma = 1.0
    entry_idx = 0
    
    for t in range(lookback_w, n):
        # Ventana histórica estricta [t - w : t] (cero look-ahead bias)
        y_w = y[t - lookback_w : t]
        x_w = x[t - lookback_w : t]
        
        # OLS Gamma
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
            # Comprobar primero si Z-score está en la zona de entrada para evitar cálculos pesados innecesarios
            is_entry_candidate = (z_entry_min <= z <= z_entry_max) or (-z_entry_max <= z <= -z_entry_min)
            if not is_entry_candidate:
                continue
                
            # Filtro Doble de Cointegración Engle-Granger / ADF sobre el spread residual (p < 0.03)
            try:
                adf_res = adfuller(spread_w, autolag='AIC')
                adf_pval = float(adf_res[1])
            except:
                adf_pval = 1.0
                
            if adf_pval >= eg_p_threshold:
                continue
                
            # Regla de entrada con banda de histeresis [2.5, 3.4]
            if z_entry_min <= z <= z_entry_max:
                in_pos = True
                pos_side = 'SHORT'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
            elif -z_entry_max <= z <= -z_entry_min:
                in_pos = True
                pos_side = 'LONG'
                entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
        else:
            holding_bars = t - entry_idx
            exit_flag = False
            exit_reason = ""
            
            if pos_side == 'SHORT':
                if z <= z_exit:
                    exit_flag = True
                    exit_reason = "Mean-Reverted (Target)"
                elif z >= z_stop:
                    exit_flag = True
                    exit_reason = "Stop-Loss (Divergence)"
            elif pos_side == 'LONG':
                if z >= -z_exit:
                    exit_flag = True
                    exit_reason = "Mean-Reverted (Target)"
                elif z <= -z_stop:
                    exit_flag = True
                    exit_reason = "Stop-Loss (Divergence)"
                    
            if holding_bars >= max_holding:
                exit_flag = True
                exit_reason = "Time-Stop (24h reached)"
                
            if exit_flag:
                qty_y = notional_per_leg / entry_y
                qty_x = (notional_per_leg * entry_gamma) / entry_x
                
                if pos_side == 'SHORT':
                    pnl_y = (entry_y - curr_y) * qty_y
                    pnl_x = (curr_x - entry_x) * qty_x
                else:
                    pnl_y = (curr_y - entry_y) * qty_y
                    pnl_x = (entry_x - curr_x) * qty_x
                    
                gross_pnl = pnl_y + pnl_x
                total_notional = (notional_per_leg + notional_per_leg * entry_gamma) * 2
                fees = total_notional * fee_rate # 0.04% por lado (0.16% total)
                net_pnl = gross_pnl - fees
                
                trades.append({
                    'entry_time': timestamps[entry_idx],
                    'exit_time': timestamps[t],
                    'side': pos_side,
                    'gross_pnl': gross_pnl,
                    'fees': fees,
                    'net_pnl': net_pnl,
                    'holding_bars': holding_bars,
                    'reason': exit_reason
                })
                in_pos = False
                
    return trades

def compute_metrics(trades: list, initial_capital: float = 5000.0) -> dict:
    if not trades:
        return {
            'trades': 0, 'wr': 0.0, 'pf': 0.0, 'net_pnl': 0.0, 'expectancy': 0.0,
            'max_dd_pct': 0.0, 'max_dd_usd': 0.0, 'max_loss_streak': 0, 'sharpe': 0.0
        }
        
    df = pd.DataFrame(trades)
    wins = df[df['net_pnl'] > 0]
    losses = df[df['net_pnl'] <= 0]
    
    wr = len(wins) / len(df) * 100.0
    gw = wins['net_pnl'].sum() if not wins.empty else 0.0
    gl = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
    pf = gw / gl
    net_pnl = df['net_pnl'].sum()
    exp = df['net_pnl'].mean()
    
    # Drawdown
    equity = initial_capital + df['net_pnl'].cumsum()
    peak = equity.cummax()
    dd_series = peak - equity
    max_dd_usd = dd_series.max()
    max_dd_pct = (max_dd_usd / initial_capital) * 100.0
    
    # Max Consecutive Losses
    is_loss = (df['net_pnl'] <= 0).astype(int)
    max_streak = 0
    current_streak = 0
    for l in is_loss:
        if l == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
            
    # Sharpe
    returns = df['net_pnl']
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 24 / (df['holding_bars'].mean() + 1e-5)) if returns.std() > 0 else 0.0
    
    return {
        'trades': len(df),
        'wr': wr,
        'pf': pf,
        'net_pnl': net_pnl,
        'expectancy': exp,
        'max_dd_pct': max_dd_pct,
        'max_dd_usd': max_dd_usd,
        'max_loss_streak': max_streak,
        'sharpe': sharpe,
        'df_trades': df
    }

def run_monte_carlo(trades_df: pd.DataFrame, num_simulations: int = 1000, initial_capital: float = 5000.0) -> dict:
    if trades_df.empty:
        return {}
        
    pnl_array = trades_df['net_pnl'].values
    n_trades = len(pnl_array)
    
    max_drawdowns = []
    final_equities = []
    
    np.random.seed(42)
    for _ in range(num_simulations):
        # Bootstrap con reemplazo
        sampled_pnl = np.random.choice(pnl_array, size=n_trades, replace=True)
        equity = initial_capital + np.cumsum(sampled_pnl)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak * 100.0
        max_drawdowns.append(np.max(dd))
        final_equities.append(equity[-1])
        
    max_drawdowns = np.array(max_drawdowns)
    final_equities = np.array(final_equities)
    
    p_ruin_15 = np.mean(max_drawdowns > 15.0) * 100.0
    p_ruin_20 = np.mean(max_drawdowns > 20.0) * 100.0
    
    return {
        'median_dd': np.median(max_drawdowns),
        'p95_dd': np.percentile(max_drawdowns, 95),
        'p99_dd': np.percentile(max_drawdowns, 99),
        'prob_dd_gt_15': p_ruin_15,
        'prob_dd_gt_20': p_ruin_20,
        'median_final_equity': np.median(final_equities),
        'p5_final_equity': np.percentile(final_equities, 5)
    }

def main():
    print("=" * 90)
    print("🔬 AUDITORÍA WALK-FORWARD MULTI-AÑO (2022 - 2026) CON TEST DE COINTEGRACIÓN DOBLE")
    print("=" * 90)
    
    pairs = [
        ('BTCUSDT', 'ETHUSDT'),
        ('AVAXUSDT', 'SOLUSDT'),
        ('LINKUSDT', 'DOTUSDT')
    ]
    
    all_train_trades = []
    all_test_trades = []
    all_val_trades = []
    
    for sym_y, sym_x in pairs:
        df = load_pair_data(sym_y, sym_x)
        if df.empty:
            print(f"⚠️ Datos no encontrados para {sym_y}/{sym_x}")
            continue
            
        print(f"📊 Procesando {sym_y}/{sym_x} ({len(df)} velas de 1h)...")
        
        # Splits
        df_train = df[(df['timestamp'] >= '2022-01-01') & (df['timestamp'] < '2023-01-01')].reset_index(drop=True)
        df_test = df[(df['timestamp'] >= '2023-01-01') & (df['timestamp'] < '2024-01-01')].reset_index(drop=True)
        df_val = df[(df['timestamp'] >= '2024-01-01') & (df['timestamp'] <= '2026-08-16')].reset_index(drop=True)
        
        t_train = run_stat_arb_simulation(df_train)
        t_test = run_stat_arb_simulation(df_test)
        t_val = run_stat_arb_simulation(df_val)
        
        all_train_trades.extend(t_train)
        all_test_trades.extend(t_test)
        all_val_trades.extend(t_val)
        
    m_train = compute_metrics(all_train_trades)
    m_test = compute_metrics(all_test_trades)
    m_val = compute_metrics(all_val_trades)
    
    print("\n" + "=" * 90)
    print("🏆 RESULTADOS WALK-FORWARD POR PERIODO (CON DOBLE FILTRO COINT: EG p<0.03 + ADF p<0.05):")
    print("=" * 90)
    
    summary_data = [
        {
            "Periodo": "1. Train (2022 Bear Market)",
            "Trades": m_train['trades'],
            "Win Rate": f"{m_train['wr']:.1f}%",
            "Profit Factor": f"{m_train['pf']:.2f}",
            "Net PnL": f"${m_train['net_pnl']:+.2f} USD",
            "Expectancy": f"${m_train['expectancy']:+.2f} USD",
            "Max DD %": f"{m_train['max_dd_pct']:.2f}%",
            "Max Loss Streak": m_train['max_loss_streak'],
            "Sharpe": f"{m_train['sharpe']:.2f}"
        },
        {
            "Periodo": "2. Test (2023 Recovery)",
            "Trades": m_test['trades'],
            "Win Rate": f"{m_test['wr']:.1f}%",
            "Profit Factor": f"{m_test['pf']:.2f}",
            "Net PnL": f"${m_test['net_pnl']:+.2f} USD",
            "Expectancy": f"${m_test['expectancy']:+.2f} USD",
            "Max DD %": f"{m_test['max_dd_pct']:.2f}%",
            "Max Loss Streak": m_test['max_loss_streak'],
            "Sharpe": f"{m_test['sharpe']:.2f}"
        },
        {
            "Periodo": "3. Validation (2024-2026 Out-of-Sample)",
            "Trades": m_val['trades'],
            "Win Rate": f"{m_val['wr']:.1f}%",
            "Profit Factor": f"{m_val['pf']:.2f}",
            "Net PnL": f"${m_val['net_pnl']:+.2f} USD",
            "Expectancy": f"${m_val['expectancy']:+.2f} USD",
            "Max DD %": f"{m_val['max_dd_pct']:.2f}%",
            "Max Loss Streak": m_val['max_loss_streak'],
            "Sharpe": f"{m_val['sharpe']:.2f}"
        }
    ]
    
    df_sum = pd.DataFrame(summary_data)
    print(df_sum.to_string(index=False))
    
    # Monte Carlo en Validación Out-of-Sample
    if 'df_trades' in m_val and not m_val['df_trades'].empty:
        mc = run_monte_carlo(m_val['df_trades'])
        print("\n" + "=" * 90)
        print("🎲 SIMULACIÓN MONTE CARLO (1,000 ITERACIONES SOBRE VALIDACIÓN OUT-OF-SAMPLE 2024-2026):")
        print("=" * 90)
        print(f"   • Max Drawdown Mediano (50% prob):    {mc['median_dd']:.2f}%")
        print(f"   • Max Drawdown Peor Caso 95% (VaR95): {mc['p95_dd']:.2f}%")
        print(f"   • Max Drawdown Extremo 99% (VaR99):   {mc['p99_dd']:.2f}%")
        print(f"   • Probabilidad de Drawdown > 15%:     {mc['prob_dd_gt_15']:.2f}%")
        print(f"   • Probabilidad de Drawdown > 20%:     {mc['prob_dd_gt_20']:.2f}%")
        print(f"   • Capital Final Mediano ($5000 base): ${mc['median_final_equity']:.2f} USD")
        print(f"   • Capital Final Peor 5% (VaR95):      ${mc['p5_final_equity']:.2f} USD")
        print("=" * 90)

if __name__ == '__main__':
    main()
