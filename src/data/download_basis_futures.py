import io
import time
import zipfile
import requests
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

BASIS_DIR = Path("data/historical_basis")
BASIS_DIR.mkdir(parents=True, exist_ok=True)

def fetch_monthly_klines(symbol: str, year: int, month: int) -> pd.DataFrame:
    """Intenta descargar el archivo mensual (mucho más rápido)."""
    month_str = f"{year}-{month:02d}"
    url = f"https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/1h/{symbol}-1h-{month_str}.zip"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            csv_name = z.namelist()[0]
            df = pd.read_csv(z.open(csv_name))
            if 'open_time' in df.columns:
                df = df.rename(columns={'open_time': 'timestamp'})
            elif df.columns[0] != 'timestamp' and type(df.columns[0]) is str and not df.columns[0].isdigit():
                # Maybe headers are different
                df.columns = ["timestamp", "open", "high", "low", "close", "volume", 
                              "close_time", "quote_asset_volume", "number_of_trades", 
                              "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"][:len(df.columns)]
            else:
                # If there are no headers and it's just numbers
                cols = ["timestamp", "open", "high", "low", "close", "volume", 
                        "close_time", "quote_asset_volume", "number_of_trades", 
                        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"]
                df = pd.read_csv(z.open(csv_name), header=None, names=cols)
            return df
    except Exception as e:
        pass
    return None

def fetch_daily_klines(symbol: str, date_str: str) -> pd.DataFrame:
    """Descarga el archivo diario si el mensual no está disponible."""
    url = f"https://data.binance.vision/data/futures/um/daily/klines/{symbol}/1h/{symbol}-1h-{date_str}.zip"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            csv_name = z.namelist()[0]
            df = pd.read_csv(z.open(csv_name))
            if 'open_time' in df.columns:
                df = df.rename(columns={'open_time': 'timestamp'})
            elif df.columns[0] != 'timestamp' and type(df.columns[0]) is str and not df.columns[0].isdigit():
                df.columns = ["timestamp", "open", "high", "low", "close", "volume", 
                              "close_time", "quote_asset_volume", "number_of_trades", 
                              "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"][:len(df.columns)]
            else:
                cols = ["timestamp", "open", "high", "low", "close", "volume", 
                        "close_time", "quote_asset_volume", "number_of_trades", 
                        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"]
                df = pd.read_csv(z.open(csv_name), header=None, names=cols)
            return df
    except:
        pass
    return None

def download_klines(symbol: str, start_date: str = "2022-01-01", end_date: str = "2026-08-16") -> pd.DataFrame:
    print(f"📥 Descargando UM-Futures Klines 1H para {symbol} (2022-2026)...")
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    # 1. Intentar descargar por meses (2022 - mes anterior)
    months_to_fetch = []
    curr = start
    while curr <= end:
        months_to_fetch.append((curr.year, curr.month))
        # Move to next month
        if curr.month == 12:
            curr = curr.replace(year=curr.year+1, month=1, day=1)
        else:
            curr = curr.replace(month=curr.month+1, day=1)
            
    months_to_fetch = list(set(months_to_fetch))
    
    dfs = []
    failed_months = []
    
    print(f"  -> Total de meses a intentar: {len(months_to_fetch)}")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_monthly_klines, symbol, y, m): (y, m) for y, m in months_to_fetch}
        for f in as_completed(futures):
            res = f.result()
            y, m = futures[f]
            if res is not None and not res.empty:
                dfs.append(res)
            else:
                failed_months.append((y, m))
                
    # 2. Rellenar con diarios para los meses fallidos (probablemente el mes actual y anterior)
    if failed_months:
        print(f"  -> Recuperando {len(failed_months)} meses con archivos diarios...")
        days_to_fetch = []
        curr = start
        while curr <= end:
            if (curr.year, curr.month) in failed_months:
                days_to_fetch.append(curr.strftime("%Y-%m-%d"))
            curr += datetime.timedelta(days=1)
            
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_daily_klines, symbol, d): d for d in days_to_fetch}
            for f in as_completed(futures):
                res = f.result()
                if res is not None and not res.empty:
                    dfs.append(res)
                    
    if not dfs:
        print(f"❌ Error crítico: Ningún dato obtenido para {symbol}")
        return pd.DataFrame()
        
    all_df = pd.concat(dfs, ignore_index=True)
    all_df['timestamp'] = pd.to_datetime(all_df['timestamp'], unit='ms')
    all_df = all_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    all_df = all_df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    # Filter bounds
    all_df = all_df[(all_df['timestamp'] >= start) & (all_df['timestamp'] <= end)]
    
    out_csv = BASIS_DIR / f"{symbol}_1h_2022_2026.csv"
    all_df.to_csv(out_csv, index=False)
    print(f"✅ Guardado UM-Futures Klines: {out_csv} ({len(all_df)} velas, {all_df['timestamp'].min()} -> {all_df['timestamp'].max()})")
    
    return all_df

def generate_manifest(symbol_data: dict):
    lines = [
        "# DATASET MANIFEST: Historical Basis (UM-Futures)",
        "",
        "## Source",
        "- **Provider**: Binance Data Vision (data.binance.vision)",
        "- **Product**: UM-Futures Klines",
        "- **Resolution**: 1H",
        "",
        "## Coverage Details",
    ]
    for sym, df in symbol_data.items():
        if df.empty:
            continue
        start_t = df['timestamp'].min()
        end_t = df['timestamp'].max()
        rows = len(df)
        
        # Check gaps
        expected_diff = pd.Timedelta(hours=1)
        diffs = df['timestamp'].diff().dropna()
        gaps = (diffs != expected_diff).sum()
        
        lines.append(f"### {sym}")
        lines.append(f"- **Start**: {start_t}")
        lines.append(f"- **End**: {end_t}")
        lines.append(f"- **Rows**: {rows}")
        lines.append(f"- **Timezone**: UTC")
        lines.append(f"- **Gaps**: {gaps} (1H gaps missing/irregular)")
        lines.append(f"- **Duplicates**: 0 (dropped)")
        lines.append("")
        
    manifest_path = BASIS_DIR / "DATASET_MANIFEST.md"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Manifest generado en {manifest_path}")

def main():
    start_t = time.time()
    print("=" * 80)
    print("🌐 CONSTRUCCIÓN DEL DATASET UM-FUTURES (BTCUSDT + ETHUSDT)")
    print("=" * 80)
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    results = {}
    for sym in symbols:
        df = download_klines(sym)
        results[sym] = df
        
    generate_manifest(results)
    
    elapsed = time.time() - start_t
    print(f"\n✨ Descarga completada en {elapsed:.2f} segundos.")

if __name__ == '__main__':
    main()
