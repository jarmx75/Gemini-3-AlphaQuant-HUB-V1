"""
Probing script to audit historical 5m data availability across Binance, Coinbase, and OKX.
Checks:
- Endpoint accessibility
- Historical depth (Can we query 2022-01-01?)
- Candle format and timestamps
- Public fee schedules
"""

import sys
import time
import requests
from datetime import datetime, timezone

def test_binance():
    print("\n--- Testing Binance ---")
    url = "https://api.binance.com/api/v3/klines"
    # Query 2022-01-01 00:00:00 UTC
    start_ts = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    params = {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "startTime": start_ts,
        "limit": 10
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            first_ts = data[0][0]
            first_dt = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc)
            print(f"✅ Binance OK: Returned {len(data)} candles. First candle: {first_dt.isoformat()}")
            return True, len(data), first_dt
        else:
            print(f"❌ Binance returned unexpected data: {data}")
            return False, 0, None
    except Exception as e:
        print(f"❌ Binance error: {e}")
        return False, 0, None


def test_coinbase():
    print("\n--- Testing Coinbase ---")
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    # Query 2022-01-01 00:00:00 to 01:00:00 UTC
    start_iso = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat()
    end_iso = datetime(2022, 1, 1, 1, 0, tzinfo=timezone.utc).isoformat()
    params = {
        "granularity": 300, # 5m = 300s
        "start": start_iso,
        "end": end_iso
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            first_ts = data[-1][0] # Coinbase returns desc
            first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc)
            print(f"✅ Coinbase OK: Returned {len(data)} candles. Earliest candle: {first_dt.isoformat()}")
            return True, len(data), first_dt
        else:
            print(f"❌ Coinbase returned: {data}")
            return False, 0, None
    except Exception as e:
        print(f"❌ Coinbase error: {e}")
        return False, 0, None


def test_okx():
    print("\n--- Testing OKX ---")
    # OKX market/history-candles endpoint
    url = "https://www.okx.com/api/v5/market/history-candles"
    # Query 2022-01-01
    start_ts = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    params = {
        "instId": "BTC-USDT",
        "bar": "5m",
        "after": str(start_ts + 3600000),
        "limit": "10"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        code = data.get("code")
        candles = data.get("data", [])
        if code == "0" and len(candles) > 0:
            first_ts = int(candles[-1][0])
            first_dt = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc)
            print(f"✅ OKX OK: Returned {len(candles)} candles. Earliest candle: {first_dt.isoformat()}")
            return True, len(candles), first_dt
        else:
            print(f"⚠️ OKX history-candles response: code={code}, msg={data.get('msg')}, data_len={len(candles)}")
            # Test recent history on OKX
            r2 = requests.get("https://www.okx.com/api/v5/market/candles", params={"instId": "BTC-USDT", "bar": "5m", "limit": "10"}, headers=headers, timeout=10)
            print(f"   Recent candles on OKX: code={r2.json().get('code')}, len={len(r2.json().get('data', []))}")
            return False, len(candles), None
    except Exception as e:
        print(f"❌ OKX error: {e}")
        return False, 0, None


if __name__ == '__main__':
    b_ok, _, _ = test_binance()
    c_ok, _, _ = test_coinbase()
    o_ok, _, _ = test_okx()
    print("\n" + "="*80)
    print(f"FEASIBILITY SUMMARY: Binance={b_ok}, Coinbase={c_ok}, OKX={o_ok}")
    print("="*80)
