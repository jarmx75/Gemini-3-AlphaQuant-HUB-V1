"""
Cross-Exchange 5m Historical Data Downloader (2022-01-01 to 2026-08-16)
Fetches BTC and ETH spot 5m candles from:
- Binance: BTCUSDT, ETHUSDT
- Coinbase: BTC-USD, ETH-USD
- OKX: BTC-USDT, ETH-USDT

Saves standardized CSVs to data/historical_cross_exchange/:
- timestamp (UTC ISO8601)
- open
- high
- low
- close
- volume
"""

import os
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


def download_binance(symbol: str) -> pd.DataFrame:
    """Fetches full 5m historical data from Binance."""
    logger.info(f"Starting Binance download for {symbol}...")
    url = "https://api.binance.com/api/v3/klines"
    
    start_ts = int(START_TIME.timestamp() * 1000)
    end_ts = int(END_TIME.timestamp() * 1000)
    
    curr_start = start_ts
    all_rows = []
    
    while curr_start < end_ts:
        params = {
            "symbol": symbol,
            "interval": "5m",
            "startTime": curr_start,
            "endTime": end_ts,
            "limit": 1000
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code != 200:
                time.sleep(1)
                continue
            data = r.json()
            if not data:
                break
            for k in data:
                all_rows.append({
                    "timestamp": pd.to_datetime(k[0], unit='ms', utc=True),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            last_ts = data[-1][0]
            curr_start = last_ts + 300000 # +5m
            if len(data) < 1000:
                break
            time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Binance fetch error on {symbol}: {e}")
            time.sleep(1)
            
    df = pd.DataFrame(all_rows).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    logger.info(f"Binance {symbol} complete: {len(df)} candles.")
    return df


def download_coinbase(symbol: str) -> pd.DataFrame:
    """Fetches 5m historical data from Coinbase in chunks of 300 candles (1500 min = 25h)."""
    logger.info(f"Starting Coinbase download for {symbol}...")
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    start_ts = int(START_TIME.timestamp())
    end_ts = int(END_TIME.timestamp())
    
    # 250 candles per request = 75000 seconds (~20.8 hours)
    chunk_step = 250 * 300
    curr_start = start_ts
    all_rows = []
    
    while curr_start < end_ts:
        curr_end = min(curr_start + chunk_step, end_ts)
        start_iso = datetime.fromtimestamp(curr_start, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(curr_end, tz=timezone.utc).isoformat()
        
        params = {
            "granularity": 300,
            "start": start_iso,
            "end": end_iso
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            if r.status_code == 429:
                time.sleep(1.0)
                continue
            if r.status_code != 200:
                time.sleep(0.5)
                continue
            data = r.json()
            if isinstance(data, list) and data:
                for k in data:
                    all_rows.append({
                        "timestamp": pd.to_datetime(k[0], unit='s', utc=True),
                        "open": float(k[3]),
                        "high": float(k[2]),
                        "low": float(k[1]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
            curr_start = curr_end
            time.sleep(0.08)
        except Exception as e:
            logger.warning(f"Coinbase fetch error on {symbol}: {e}")
            time.sleep(1)
            
    df = pd.DataFrame(all_rows).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    logger.info(f"Coinbase {symbol} complete: {len(df)} candles.")
    return df


def download_okx(symbol: str) -> pd.DataFrame:
    """Fetches 5m historical data from OKX using history-candles."""
    logger.info(f"Starting OKX download for {symbol}...")
    url = "https://www.okx.com/api/v5/market/history-candles"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # OKX pagination: 'after' takes a timestamp and returns candles older than that timestamp.
    # So we paginate backwards from END_TIME to START_TIME.
    end_ts = int(END_TIME.timestamp() * 1000)
    start_ts = int(START_TIME.timestamp() * 1000)
    
    curr_after = end_ts + 300000
    all_rows = []
    
    while curr_after > start_ts:
        params = {
            "instId": symbol,
            "bar": "5m",
            "after": str(curr_after),
            "limit": "100"
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            if r.status_code != 200:
                time.sleep(0.5)
                continue
            data = r.json()
            candles = data.get("data", [])
            if not candles:
                break
            for k in candles:
                ts = int(k[0])
                if ts < start_ts:
                    break
                all_rows.append({
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
            time.sleep(0.06)
        except Exception as e:
            logger.warning(f"OKX fetch error on {symbol}: {e}")
            time.sleep(1)
            
    df = pd.DataFrame(all_rows).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    logger.info(f"OKX {symbol} complete: {len(df)} candles.")
    return df


def main():
    logger.info("=== BATCH K: DOWNLOADING CROSS-EXCHANGE 5M HISTORICAL DATA ===")
    
    # 1. Binance BTC & ETH
    df_bin_btc = download_binance("BTCUSDT")
    df_bin_btc.to_csv(OUTPUT_DIR / "binance_BTCUSDT_5m_2022_2026.csv", index=False)
    
    df_bin_eth = download_binance("ETHUSDT")
    df_bin_eth.to_csv(OUTPUT_DIR / "binance_ETHUSDT_5m_2022_2026.csv", index=False)
    
    # 2. Coinbase BTC & ETH
    df_cb_btc = download_coinbase("BTC-USD")
    df_cb_btc.to_csv(OUTPUT_DIR / "coinbase_BTCUSD_5m_2022_2026.csv", index=False)
    
    df_cb_eth = download_coinbase("ETH-USD")
    df_cb_eth.to_csv(OUTPUT_DIR / "coinbase_ETHUSD_5m_2022_2026.csv", index=False)
    
    # 3. OKX BTC & ETH
    df_okx_btc = download_okx("BTC-USDT")
    df_okx_btc.to_csv(OUTPUT_DIR / "okx_BTCUSDT_5m_2022_2026.csv", index=False)
    
    df_okx_eth = download_okx("ETH-USDT")
    df_okx_eth.to_csv(OUTPUT_DIR / "okx_ETHUSDT_5m_2022_2026.csv", index=False)
    
    logger.info("=== CROSS-EXCHANGE DOWNLOAD COMPLETED SUCCESSFULLY ===")


if __name__ == '__main__':
    main()
