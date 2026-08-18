# 📊 DATASET MANIFEST: Binance Historical Derivatives (2022 - 2026)

> **PROPÓSITO**: Dataset verificado de derivados (Funding Rate, Open Interest y Taker Volume Ratio) para investigación cuantitativa y pruebas de microestructura en BTCUSDT y ETHUSDT.

---

## 📁 Archivos Disponibles en `data/historical_derivatives/`

### 1. `BTCUSDT_funding_rate_2022_2026.csv` & `ETHUSDT_funding_rate_2022_2026.csv`
- **Fuente**: Binance Futures Public REST API (`https://fapi.binance.com/fapi/v1/fundingRate`).
- **Fecha Inicial**: `2022-01-01 08:00:00 UTC`
- **Fecha Final**: `2026-08-16 00:00:00 UTC`
- **Frecuencia**: 8 Horas (00:00, 08:00, 16:00 UTC).
- **Total Registros**: 5,064 observaciones por símbolo.
- **Cobertura**: `100.0%` (0 gaps, serie continua de 8h).
- **Columnas**:
  - `symbol`: Símbolo del contrato perp (`BTCUSDT` / `ETHUSDT`).
  - `fundingTime`: Timestamp UTC del cobro/pago efectivo del funding rate.
  - `fundingRate`: Tasa de financiación periódica de 8h (decimal).
  - `markPrice`: Precio de marca en el momento del funding.
  - `rateType`: Tipo de funding (`Regular`).

---

### 2. `BTCUSDT_metrics_1h_2022_2026.csv` & `ETHUSDT_metrics_1h_2022_2026.csv`
- **Fuente**: Archivos oficiales de métricas diarias de Binance Data Vision (`https://data.binance.vision/data/futures/um/daily/metrics/`).
- **Fecha Inicial**: `2022-01-30 00:00:00 UTC` *(Inicio oficial de publicación de métricas de derivados por Binance)*.
- **Fecha Final**: `2026-08-16 23:00:00 UTC`.
- **Frecuencia**: 1 Hora (agregación determinista desde datos de 5 minutos).
- **Total Velas 1H**:
  - BTCUSDT: 37,457 velas 1H.
  - ETHUSDT: 37,458 velas 1H.
- **Cobertura**: `99.8%` desde enero 2022 hasta agosto 2026 (sin huecos significativos).
- **Columnas**:
  - `create_time`: Timestamp UTC de la vela 1H.
  - `symbol`: Símbolo del activo.
  - `sum_open_interest`: Contratos de Interés Abierto (OI en unidades base).
  - `sum_open_interest_value`: Valor nocional total del Interés Abierto en USD.
  - `sum_taker_long_short_vol_ratio`: Ratio de volumen taker comprador / taker vendedor en la hora ($> 1.0 \implies$ presión compradora taker; $< 1.0 \implies$ presión vendedora taker).

---

## 🔒 Regla de Integridad Temporal (Anti Look-Ahead)
- El **Funding Rate** de las 08:00 UTC solo está disponible **a partir de las 08:00 UTC**; no puede utilizarse antes de esa hora.
- Las métricas de **Open Interest** y **Taker Ratio** de la hora $t$ solo se evalúan al cierre de la vela $t$ para generar señales en el Open de la vela $t+1$.
