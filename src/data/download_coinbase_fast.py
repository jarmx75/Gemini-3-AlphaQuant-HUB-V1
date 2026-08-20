"""
Clean rate-limited parallel downloader for Coinbase BTC-USD and ETH-USD 5m data (2022-2026).
"""

import sys
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "historical_cross_exchange"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_TIME = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
END_TIME = datetime(2026, 8, 16, 23, 55, tzinfo=timezone.utc)


def download_coinbase_series(symbol: str, filename: str):
    logger.info(f"[COINBASE] Starting download for {symbol}...")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
    
    start_ts = int(START_TIME.timestamp())
    end_ts = int(END_TIME.timestamp())
    step = 280 * 300 # 280 candles * 300s = 84,000s (~23.3h)
    
    curr = start_ts
    rows = []
    req_count = 0
    t0 = time.time()
    
    while curr < end_ts:
        c_end = min(curr + step, end_ts)
        start_iso = datetime.fromtimestamp(curr, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(c_end, tz=timezone.utc).isoformat()
        
        for attempt in range(5):
            try:
                r = session.get(url, params={"granularity": 300, "start": start_iso, "end": end_iso}, timeout=10)
                if r.status_code == 429:
                    time.sleep(0.5)
                    continue
                if r.status_code == 200:
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
                    break
                time.sleep(0.2)
            except Exception:
                time.sleep(0.5)
                
        curr = c_end
        req_count += 1
        if req_count % 200 == 0:
            pct = (curr - start_ts) / (end_ts - start_ts) * 100.0
            logger.info(f"[{symbol}] Progress: {pct:.1f}% ({len(rows)} candles in {time.time()-t0:.1f}s)")
        time.sleep(0.12) # ~8 req/sec max
        
    df = pd.DataFrame(rows).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    out_file = OUTPUT_DIR / filename
    df.to_csv(out_file, index=False)
    logger.info(f"[{symbol}] COMPLETED: Saved {len(df)} candles to {out_file} in {time.time()-t0:.1f}s.")
    return len(df)


def main():
    logger.info("=== DOWNLOADING COINBASE BTC-USD & ETH-USD 5M DATA (2022-2026) ===")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(download_coinbase_series, "BTC-USD", "coinbase_BTCUSD_5m_2022_2026.csv")
        f2 = executor.submit(download_coinbase_series, "ETH-USD", "coinbase_ETHUSD_5m_2022_2026.csv")
        f1.result()
        f2.result()
    logger.info(f"=== ALL COINBASE DATA DOWNLOADED IN {time.time()-t0:.1f}s ===")


if __name__ == '__main__':
    main()
