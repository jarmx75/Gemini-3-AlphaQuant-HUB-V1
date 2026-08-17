"""
Equity Curve Generator: Genera la visualización gráfica en ASCII de la curva de equity en validación out-of-sample (2024-2026).
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from scripts.auditoria_walkforward_montecarlo import load_pair_data, run_stat_arb_simulation

def generate_ascii_chart(equity_series: np.ndarray, width: int = 60, height: int = 15) -> str:
    n = len(equity_series)
    min_val = np.min(equity_series)
    max_val = np.max(equity_series)
    
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Mapear cada punto al grid
    indices = np.linspace(0, n - 1, width, dtype=int)
    sampled_values = equity_series[indices]
    
    for x, val in enumerate(sampled_values):
        norm = (val - min_val) / (max_val - min_val + 1e-9)
        y = int(norm * (height - 1))
        y = height - 1 - y # Invertir para que arriba sea mayor
        grid[y][x] = '█'
        
    chart_str = ""
    for r in range(height):
        val_label = max_val - (r / (height - 1)) * (max_val - min_val)
        row_str = "".join(grid[r])
        chart_str += f"${val_label:>8.2f} | {row_str}\n"
        
    chart_str += " " * 10 + "-" * (width + 3) + "\n"
    chart_str += " " * 10 + "  Ene 2024         Ene 2025         Ago 2026\n"
    return chart_str

def main():
    pairs = [('BTCUSDT', 'ETHUSDT'), ('AVAXUSDT', 'SOLUSDT')]
    all_val_trades = []
    
    for sym_y, sym_x in pairs:
        df = load_pair_data(sym_y, sym_x)
        if not df.empty:
            df_val = df[(df['timestamp'] >= '2024-01-01') & (df['timestamp'] <= '2026-08-16')].reset_index(drop=True)
            trades = run_stat_arb_simulation(df_val)
            all_val_trades.extend(trades)
            
    df_trades = pd.DataFrame(all_val_trades).sort_values('entry_time').reset_index(drop=True)
    initial_capital = 5000.0
    equity = initial_capital + df_trades['net_pnl'].cumsum().values
    
    print("📈 CURVA DE EQUITY OUT-OF-SAMPLE (2024 - 2026):")
    print(generate_ascii_chart(equity))
    print(f"💰 Capital Inicial: ${initial_capital:.2f} USD")
    print(f"💰 Capital Final:   ${equity[-1]:.2f} USD (Retorno Neto: +{((equity[-1]-initial_capital)/initial_capital)*100:.2f}%)")

if __name__ == '__main__':
    main()
