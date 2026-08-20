"""
High-Performance Parallel Cross-Exchange 5m Historical Data Downloader (2022-2026)
Uses chunked multi-threading and persistent HTTP connection pooling.
"""

import sys
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "historical_cross_exchange"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNKS = [
    (datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2022, 12, 31, 23, 55, tzinfo=timezone.utc)),
    (datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2023, 12, 31, 23, 55, tzinfo=timezone.utc)),
    (datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2024, 12, 31, 23, 55, tzinfo=timezone.utc)),
    (datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 8, 16, 23, 55, tzinfo=timezone.utc)),
]


def fetch_binance_chunk(symbol: str, start_dt: datetime, end_dt: datetime) -> list:
    session = requests.Session()
    url = "https://api.binance.com/api/v3/klines"
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    curr = start_ts
    rows = []
    
    while curr < end_ts:
        try:
            r = session.get(url, params={"symbol": symbol, "interval": "5m", "startTime": curr, "endTime": end_ts, "limit": 1000}, timeout=10)
            if r.status_code != 200:
                time.sleep(0.5)
                continue
            data = r.json()
            if not data:
                break
            for k in data:
                rows.append({
                    "timestamp": pd.to_datetime(k[0], unit='ms', utc=True),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            curr = data[-1][0] + 300000
            if len(data) < 1000:
                break
        except Exception:
            time.sleep(0.5)
    return rows


def fetch_coinbase_chunk(symbol: str, start_dt: datetime, end_dt: datetime) -> list:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
    
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())
    step = 250 * 300 # 75,000s
    curr = start_ts
    rows = []
    
    while curr < end_ts:
        c_end = min(curr + step, end_ts)
        start_iso = datetime.fromtimestamp(curr, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(c_end, tz=timezone.utc).isoformat()
        
        try:
            r = session.get(url, params={"granularity": 300, "start": start_iso, "end": end_iso}, timeout=10)
            if r.status_code == 429:
                time.sleep(0.5)
                continue
            if r.status_code != 200:
                time.sleep(0.2)
                continue
            data = r.json()
            if isinstance(data, list) and data:
                for k in data:
                    rows.append({
                        "timestamp": pd.to_datetime(k[0], unit='s', utc=True),
                        "open": float(k[3]),
                        "high": float(k[2]),
                        "low": float(k[1]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
            curr = c_end
            time.sleep(0.04)
        except Exception:
            time.sleep(0.5)
    return rows


def fetch_okx_chunk(symbol: str, start_dt: datetime, end_dt: datetime) -> list:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    url = "https://www.okx.com/api/v5/market/history-candles"
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    curr_after = end_ts + 300000
    rows = []
    
    while curr_after > start_ts:
        try:
            r = session.get(url, params={"instId": symbol, "bar": "5m", "after": str(curr_after), "limit": "100"}, timeout=10)
            if r.status_code != 200:
                time.sleep(0.2)
                continue
            data = r.json()
            candles = data.get("data", [])
            if not candles:
                break
            for k in candles:
                ts = int(k[0])
                if ts < start_ts:
                    break
                rows.append({
                    "timestamp": pd.to_datetime(ts, unit='ms', utc=True),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            oldest_ts = int(candles[-1][0])
            if oldest_ts >= curr_after or oldest_ts <= start_ts:
                break
            curr_after = oldest_ts
            time.sleep(0.03)
        except Exception:
            time.sleep(0.5)
    return rows


def download_symbol(venue: str, symbol: str, fetch_fn, filename: str):
    logger.info(f"[{venue.upper()}] Starting parallel download for {symbol} across {len(CHUNKS)} annual chunks...")
    t0 = time.time()
    all_rows = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch_fn, symbol, s_dt, e_dt) for s_dt, e_dt in CHUNKS]
        for f in as_completed(futures):
            all_rows.extend(f.result())
            
    df = pd.DataFrame(all_rows).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    out_file = OUTPUT_DIR / filename
    df.to_csv(out_file, index=False)
    logger.info(f"[{venue.upper()}] Saved {len(df)} candles to {out_file} in {time.time()-t0:.1f}s.")
    return len(df)


def main():
    logger.info("=== BATCH K: STARTING PARALLEL MULTI-VENUE DATA INGESTION ===")
    t_start = time.time()
    
    tasks = [
        ("binance", "BTCUSDT", fetch_binance_chunk, "binance_BTCUSDT_5m_2022_2026.csv"),
        ("binance", "ETHUSDT", fetch_binance_chunk, "binance_ETHUSDT_5m_2022_2026.csv"),
        ("coinbase", "BTC-USD", fetch_coinbase_chunk, "coinbase_BTCUSD_5m_2022_2026.csv"),
        ("coinbase", "ETH-USD", fetch_coinbase_chunk, "coinbase_ETHUSD_5m_2022_2026.csv"),
        ("okx", "BTC-USDT", fetch_okx_chunk, "okx_BTCUSDT_5m_2022_2026.csv"),
        ("okx", "ETH-USDT", fetch_okx_chunk, "okx_ETHUSDT_5m_2022_2026.csv"),
    ]
    
    with ThreadPoolExecutor(max_workers=6) as master_executor:
        futures = [master_executor.submit(download_symbol, venue, sym, fn, fname) for venue, sym, fn, fname in tasks]
        for f in as_completed(futures):
            f.result()
            
    logger.info(f"=== ALL 6 DATASETS DOWNLOADED IN {time.time()-t_start:.1f}s ===")


if __name__ == '__main__':
    main()
