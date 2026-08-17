"""
Multi-Year Historical Data Downloader (2022 - 2026)
Descarga y almacena en caché velas de 1h desde Binance API para pruebas Walk-Forward sin sesgo.
"""

import os
import time
from pathlib import Path
import pandas as pd
import requests

data_dir = Path("data/historical")
data_dir.mkdir(parents=True, exist_ok=True)

def download_pair_klines(symbol: str, start_str: str = "2022-01-01", end_str: str = "2026-08-16") -> pd.DataFrame:
    cache_file = data_dir / f"{symbol}_1h_2022_2026.csv"
    if cache_file.exists():
        print(f"📦 Cargando desde caché local: {cache_file}")
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
        
    print(f"🌐 Descargando historial completo de {symbol} (1h) de {start_str} a {end_str}...")
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_str).timestamp() * 1000)
    
    current_start = start_ts
    all_rows = []
    
    url = "https://api.binance.com/api/v3/klines"
    
    while current_start < end_ts:
        params = {
            'symbol': symbol,
            'interval': '1h',
            'startTime': current_start,
            'endTime': end_ts,
            'limit': 1000
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"Error {resp.status_code} descargando {symbol}")
                break
            data = resp.json()
            if not data or len(data) == 0:
                break
                
            for row in data:
                all_rows.append({
                    'timestamp': pd.to_datetime(row[0], unit='ms'),
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5])
                })
                
            # Avanzar startTime al final del último bloque
            current_start = data[-1][6] + 1
            time.sleep(0.08) # Rate limiting
        except Exception as e:
            print(f"Excepción descargando {symbol}: {e}")
            break
            
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.drop_duplicates(subset=['timestamp']).sort_values(by='timestamp').reset_index(drop=True)
        df.to_csv(cache_file, index=False)
        print(f"✅ Descarga completa de {symbol}: {len(df)} velas guardadas en {cache_file}")
    return df

if __name__ == '__main__':
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
    for sym in symbols:
        download_pair_klines(sym)
