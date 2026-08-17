#!/usr/bin/env python3
"""Debug script para funding rates."""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.strategies.funding_rate_arbitrage import simulate_funding_data

# Cargar datos
collector = DataCollector('binance', sandbox=False)
df = collector.load_from_parquet('data/raw/BTC_USDT_1h_90d.parquet')

# Usar solo 500 registros
df = df.tail(500).copy()

# Simular funding rates
df_with_funding = simulate_funding_data(df)

print("Estadísticas de Funding Rate Simulado:")
print(df_with_funding['funding_rate'].describe())
print(f"\nValores extremos:")
print(f"Max: {df_with_funding['funding_rate'].max()}")
print(f"Min: {df_with_funding['funding_rate'].min()}")
print(f"\nCantidad de valores > 0.00001: {(df_with_funding['funding_rate'] > 0.00001).sum()}")
print(f"Cantidad de valores < -0.00001: {(df_with_funding['funding_rate'] < -0.00001).sum()}")

print(f"\nPrimeros 20 valores de funding rate:")
print(df_with_funding['funding_rate'].head(20))
