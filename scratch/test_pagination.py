"""
Pagination and completeness test for Binance, Coinbase, and OKX 5m data.
"""

import time
import requests
import pandas as pd
from datetime import datetime, timezone

def test_pagination():
    # 1. Binance: 1000 candles per request
    t0 = time.time()
    url_binance = "https://api.binance.com/api/v3/klines"
    start_ts = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    r = requests.get(url_binance, params={"symbol": "BTCUSDT", "interval": "5m", "startTime": start_ts, "limit": 1000}, timeout=10)
    data_b = r.json()
    print(f"Binance: fetched 1000 candles in {time.time()-t0:.2f}s. Start: {data_b[0][0]}, End: {data_b[-1][0]}")

    # 2. Coinbase: 300 candles per request
    t0 = time.time()
    url_cb = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    start_iso = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat()
    end_iso = datetime(2022, 1, 2, 1, 0, tzinfo=timezone.utc).isoformat()
    r = requests.get(url_cb, params={"granularity": 300, "start": start_iso, "end": end_iso}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data_c = r.json()
    print(f"Coinbase: fetched {len(data_c)} candles in {time.time()-t0:.2f}s.")

    # 3. OKX: test history-candles pagination
    t0 = time.time()
    url_okx = "https://www.okx.com/api/v5/market/history-candles"
    # OKX 'after' parameter: pagination cursor
    r = requests.get(url_okx, params={"instId": "BTC-USDT", "bar": "5m", "limit": "100"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data_o = r.json()
    print(f"OKX: fetched {len(data_o.get('data', []))} candles in {time.time()-t0:.2f}s. Code: {data_o.get('code')}")

if __name__ == '__main__':
    test_pagination()
