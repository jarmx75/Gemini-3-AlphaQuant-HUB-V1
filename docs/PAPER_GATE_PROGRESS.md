# Monitor de Progreso del Paper Gate (100 Trades Forward)

**Última Actualización**: `2026-08-23 02:41:59 UTC`  
**Estado General del Gate**: `PAPER_GATE_IN_PROGRESS`  
**Meta Cuantitativa**: **100 trades cerrados forward** por estrategia antes de evaluar Demo / Live.  
**Invariantes de Seguridad**: `APPROVED=false` | `DEMO_ORDERS=0` | `REAL_ORDERS=0` | `ALPACA_LIVE_ORDERS=0`

---

## 1. Tabla de Progreso Multi-Mercado

| Estrategia ID | Mercado | Broker | Trades Cerrados | Progreso (%) | Restantes | Win Rate (%) | PnL Paper | PF Paper | Max DD (%) | Días Activo | Est. Días a 100 | Estado del Gate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Pairs_Stat_Arb_Base` | `CRYPTO_FUTURES` | `BINANCE` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 6.2 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `Pairs_W90_Z2.5_S3.5_H24` | `CRYPTO_FUTURES` | `BINANCE` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 5.51 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `Pairs_W90_Z2.4_S3.5_H24` | `CRYPTO_FUTURES` | `BINANCE` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 5.51 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `TSMOM_1D_M1_N21` | `US_EQUITY_ETF` | `ALPACA` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 3.02 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `TSMOM_1D_M2_N63` | `US_EQUITY_ETF` | `ALPACA` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 3.02 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |

---

## 2. Detalle de Operativa y Salud

### 📌 `Pairs_Stat_Arb_Base` (CRYPTO_FUTURES)
- **Broker**: `BINANCE Paper`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `Pairs_W90_Z2.5_S3.5_H24` (CRYPTO_FUTURES)
- **Broker**: `BINANCE Paper`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `Pairs_W90_Z2.4_S3.5_H24` (CRYPTO_FUTURES)
- **Broker**: `BINANCE Paper`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `TSMOM_1D_M1_N21` (US_EQUITY_ETF)
- **Broker**: `ALPACA Paper`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `TSMOM_1D_M2_N63` (US_EQUITY_ETF)
- **Broker**: `ALPACA Paper`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

---

## 3. Criterios de Aprobación del Paper Gate

1. **Requisito Cuantitativo**: $\ge 100$ trades cerrados reales en forward paper mode por estrategia (`gate_status == 'PAPER_GATE_READY'`).
2. **Requisito Cualitativo**:
   - $\text{{PF Paper}} \ge 1.20$
   - $\text{{Max DD Paper}} < 12.0\%$
   - Ausencia de anomalías de ejecución (`SLIPPAGE_BREACH`, `EXCESSIVE_FEES`).
3. **Cero Bypass**:
   - `OPEN` trades no cuentan.
   - Backtests y dry-runs no cuentan.
   - `APPROVED` requiere firma manual humana explícita posterior a la aprobación del Paper Gate.
