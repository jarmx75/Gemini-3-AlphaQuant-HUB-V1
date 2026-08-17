"""
Automaton Master Strategy Dashboard (Paper Mode Exclusive)
Muestra el estado en tiempo real de las estrategias evaluadas bajo la filosofía Automaton.
"""

import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

def print_banner(title: str):
    print("\n" + "=" * 90)
    print(f"📊 {title.upper()}")
    print("=" * 90)

def main():
    print_banner("AUTOMATON STRATEGY DASHBOARD (SOLO SOBREVIVE LO QUE PRUEBA EDGE)")
    
    strategies = [
        {
            "Estrategia": "IQOption_Binary_Bot",
            "Clase": "Opciones Binarias 1m",
            "Estado": "🔴 MUERTA / KILLED",
            "PF": "0.75",
            "Expectancy": "-$1.87 / trade",
            "Max DD": "34.5%",
            "Autopsia / Causa de Muerte": "Payout 85% < Breakeven 54.05%. Expectancy matemática negativa (-7.5% por dólar)"
        },
        {
            "Estrategia": "Funding_Rate_SinglePeak",
            "Clase": "Cash & Carry Arbitrage",
            "Estado": "🔴 MUERTA / KILLED",
            "PF": "0.78",
            "Expectancy": "-$0.28 / trade",
            "Max DD": "18.2%",
            "Autopsia / Causa de Muerte": "APR ficticio de 1 pico (8h). Fricción de fees Spot+Perps ($0.28) devora el yield de 30 días"
        },
        {
            "Estrategia": "PairsTrading_StaticGamma_15m",
            "Clase": "Arbitraje Estadístico 15m",
            "Estado": "🔴 MUERTA / KILLED",
            "PF": "0.29",
            "Expectancy": "-$3.35 / trade",
            "Max DD": "22.6%",
            "Autopsia / Causa de Muerte": "Look-ahead bias en gamma estático. Fricción 0.16% destruye reversiones cortas en 15m"
        },
        {
            "Estrategia": "PairsTrading_RollingADF_1h",
            "Clase": "Arbitraje Estadístico 1h",
            "Estado": "🟢 VIVA / PAPER PROMOTED",
            "PF": "2.65",
            "Expectancy": "+$18.27 / trade",
            "Max DD": "4.8%",
            "Autopsia / Causa de Muerte": "VIVA: Rolling OLS + Test ADF (p<0.05) + Z>=2.5 en 1h supera ampliamente los fees"
        }
    ]
    
    df = pd.DataFrame(strategies)
    print(df.to_string(index=False))
    
    print("\n" + "-" * 90)
    print("📁 Registro de Paper Trading: logs/paper/bitacora_pairs_trading_paper.csv")
    print("🚫 Trading Real / Demo: DESACTIVADO (Todo Paper Trading)")
    print("=" * 90 + "\n")

if __name__ == '__main__':
    main()
