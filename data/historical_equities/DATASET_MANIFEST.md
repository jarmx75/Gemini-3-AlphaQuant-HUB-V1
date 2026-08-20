# Dataset Manifest: Historical Equities Daily Data (2022–2026)

## 1. Overview
- **Research Batch**: Batch L — Equity Overnight Gap Reversal
- **Data Source**: Yahoo Finance via `yfinance`
- **Timeframe**: Daily (1D) Market Open to Market Close
- **Timezone**: US Eastern Market Hours (09:30 - 16:00 EST/EDT)
- **Look-Ahead Bias Prevention**: All entries use strictly current day Open ($Open_t$) after observing previous day Close ($Close_{t-1}$).

## 2. ETF Universe Coverage

| Symbol | Asset Class / Sector | Start Date | End Date | Total Trading Days | Missing Values | Adjustments Applied |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **SPY** | S&P 500 US Large Cap Core | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **QQQ** | Nasdaq 100 Technology Core | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **IWM** | Russell 2000 Small Cap Core | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **XLF** | Financial Select Sector SPDR | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **XLK** | Technology Select Sector SPDR | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **XLE** | Energy Select Sector SPDR | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **GLD** | SPDR Gold Shares (Commodities) | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |
| **TLT** | iShares 20+ Year Treasury Bond (Fixed Income) | 2022-01-03 | 2026-08-14 | 1158 | 0 | Split & Dividend Auto-Adjusted (Consistent OHLC) |

## 3. Data Integrity & Verification
- Zero missing values across all trading days.
- US equity market holidays (NYSE/NASDAQ calendar) accurately preserved.
- OHLC is strictly split- and dividend-adjusted to avoid artificial gap artifacts.
