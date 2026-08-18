"""
Downloader for Binance Historical Derivatives Data (2022-2026)
Fuentes oficiales:
1) Binance Futures Public REST API: fapi.binance.com (Funding Rate)
2) Binance Data Vision Archives: data.binance.vision (Daily Metrics: Open Interest & Taker Flow)
"""

import os
import io
import time
import zipfile
import requests
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np

DERIVATIVES_DIR = Path("data/historical_derivatives")
DERIVATIVES_DIR.mkdir(parents=True, exist_ok=True)

def download_funding_rates(symbol: str, start_date: str = "2022-01-01", end_date: str = "2026-08-16") -> pd.DataFrame:
    """Descarga todo el historial de funding rate usando la API pública con paginación."""
    print(f"📥 Descargando Funding Rate para {symbol} desde {start_date}...")
    start_ts = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    all_records = []
    curr_start = start_ts
    
    while curr_start < end_ts:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&startTime={curr_start}&endTime={end_ts}&limit=1000"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                print(f"Error {r.status_code} en {url}: {r.text}")
                break
            data = r.json()
            if not data:
                break
            all_records.extend(data)
            last_ts = data[-1]['fundingTime']
            if last_ts <= curr_start:
                break
            curr_start = last_ts + 1
            if len(data) < 1000:
                break
            time.sleep(0.05)
        except Exception as e:
            print(f"Excepción descargando funding: {e}")
            time.sleep(1)
            
    df = pd.DataFrame(all_records)
    if not df.empty:
        df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['fundingRate'] = df['fundingRate'].astype(float)
        df['markPrice'] = pd.to_numeric(df['markPrice'], errors='coerce')
        df = df.sort_values('fundingTime').drop_duplicates(subset=['fundingTime']).reset_index(drop=True)
        
        out_csv = DERIVATIVES_DIR / f"{symbol}_funding_rate_2022_2026.csv"
        df.to_csv(out_csv, index=False)
        print(f"✅ Guardado Funding Rate: {out_csv} ({len(df)} registros, {df['fundingTime'].min()} -> {df['fundingTime'].max()})")
    return df

def fetch_single_day_metrics(symbol: str, date_str: str) -> Optional[pd.DataFrame]:
    """Descarga y extrae el archivo zip de métricas diarias de data.binance.vision."""
    url = f"https://data.binance.vision/data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date_str}.zip"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            csv_name = z.namelist()[0]
            df = pd.read_csv(z.open(csv_name))
            return df
    except:
        pass
    return None

def download_daily_metrics(symbol: str, start_date: str = "2022-01-01", end_date: str = "2026-08-16") -> pd.DataFrame:
    """Descarga Open Interest y Taker Volume Ratio concurrentemente desde data.binance.vision."""
    print(f"📥 Descargando Métricas (OI & Taker Ratio) para {symbol} (2022-2026)...")
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    date_list = []
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y-%m-%d"))
        curr += datetime.timedelta(days=1)
        
    print(f"  -> Total de días a descargar: {len(date_list)}")
    
    dfs = []
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(fetch_single_day_metrics, symbol, d): d for d in date_list}
        completed = 0
        for f in as_completed(futures):
            res = f.result()
            if res is not None and not res.empty:
                dfs.append(res)
            completed += 1
            if completed % 300 == 0 or completed == len(date_list):
                print(f"  [{symbol}] Progreso: {completed}/{len(date_list)} días...")
                
    if not dfs:
        print(f"❌ No se pudieron descargar métricas para {symbol}")
        return pd.DataFrame()
        
    all_df = pd.concat(dfs, ignore_index=True)
    all_df['create_time'] = pd.to_datetime(all_df['create_time'])
    all_df = all_df.sort_values('create_time').drop_duplicates(subset=['create_time']).reset_index(drop=True)
    
    # Resample a 1h para alineación perfecta con OHLCV
    all_df = all_df.set_index('create_time')
    df_1h = all_df.resample('1h').agg({
        'symbol': 'last',
        'sum_open_interest': 'last',
        'sum_open_interest_value': 'last',
        'sum_taker_long_short_vol_ratio': 'mean'
    }).dropna().reset_index()
    
    out_csv = DERIVATIVES_DIR / f"{symbol}_metrics_1h_2022_2026.csv"
    df_1h.to_csv(out_csv, index=False)
    print(f"✅ Guardadas Métricas 1H: {out_csv} ({len(df_1h)} velas 1H, {df_1h['create_time'].min()} -> {df_1h['create_time'].max()})")
    return df_1h

def main():
    start_t = time.time()
    print("=" * 80)
    print("🌐 CONSTRUCCIÓN DEL DATASET DE DERIVADOS HISTÓRICOS (BTCUSDT + ETHUSDT)")
    print("=" * 80)
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    for sym in symbols:
        download_funding_rates(sym)
        download_daily_metrics(sym)
        
    elapsed = time.time() - start_t
    print(f"\n✨ Descarga completada en {elapsed:.2f} segundos.")

if __name__ == '__main__':
    main()
