# Dataset Manifest: Cross-Exchange 5m Historical Data (2022–2026)

## 1. Executive Summary

This manifest documents the historical multi-venue 5m dataset acquired for **Batch K (Cross-Exchange Lead/Lag Research)**.
Data coverage spans **January 1, 2022 00:00:00 UTC** to **August 16, 2026 23:55:00 UTC** (~4.62 years, 486,000+ 5-minute bars per venue).

---

## 2. Venue Availability & Public API Audit

| Venue | Asset / Symbol | Interval | Start Date (UTC) | End Date (UTC) | Total Candles | Timezone | Historical Depth Status | Standard Retail Taker Fee |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Binance** | `BTCUSDT` | 5m | 2022-01-01 00:00:00 | 2026-08-16 23:55:00 | **486,416** | UTC | Complete (Full 2022–2026 available) | 0.10% (0.075% w/ BNB) |
| **Binance** | `ETHUSDT` | 5m | 2022-01-01 00:00:00 | 2026-08-16 23:55:00 | **486,416** | UTC | Complete (Full 2022–2026 available) | 0.10% (0.075% w/ BNB) |
| **Coinbase** | `BTC-USD` | 5m | 2022-01-01 00:00:00 | 2026-08-16 23:55:00 | **486,195** | UTC | Complete (Full 2022–2026 available) | 0.60% (Tier 1 <$10k) |
| **Coinbase** | `ETH-USD` | 5m | 2022-01-01 00:00:00 | 2026-08-16 23:55:00 | **486,187** | UTC | Complete (Full 2022–2026 available) | 0.60% (Tier 1 <$10k) |
| **OKX** | `BTC-USDT` / `ETH-USDT` | 5m | — | — | N/A | UTC | **API Limited**: Public REST `market/history-candles` caps at ~100 days | 0.10% |

---

## 3. Data Schema & Formats

All datasets are saved under `data/historical_cross_exchange/` with schema:
- `timestamp`: ISO8601 UTC timestamp (`YYYY-MM-DD HH:MM:SS+00:00`)
- `open`: Float (USD/USDT price)
- `high`: Float (USD/USDT price)
- `low`: Float (USD/USDT price)
- `close`: Float (USD/USDT price)
- `volume`: Float (Base asset volume)

---

## 4. Gap & Alignment Audit

- **Theoretical expected bars**: $4.62 \text{ years} \times 365.25 \times 24 \times 12 = 486,432 \text{ bars}$.
- **Binance completeness**: $486,416 / 486,432 = \mathbf{99.997\%}$ (16 missing bars across 4.62 years due to scheduled maintenance).
- **Coinbase completeness**: $486,195 / 486,432 = \mathbf{99.951\%}$ (237 missing bars across 4.62 years due to brief exchange maintenance windows).
- **Inner Merge Alignment**: Timestamps match with sub-second precision on 5m boundaries.
