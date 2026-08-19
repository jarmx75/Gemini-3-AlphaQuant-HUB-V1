# Monitor de Progreso del Paper Gate (100 Trades Forward)

**Última Actualización**: `2026-08-19 03:27:11 UTC`  
**Estado General del Gate**: `PAPER_GATE_IN_PROGRESS`  
**Objetivo de Seguridad**: Requerimiento estricto de **100 trades cerrados** en forward paper antes de evaluar Binance Demo.  
**Invariantes de Seguridad**: `APPROVED=false` | `DEMO_ORDERS=0` | `REAL_ORDERS=0`

---

## 1. Tabla de Progreso por Estrategia

| Estrategia ID | Trades Cerrados | Progreso (%) | Restantes | Win Rate (%) | PnL Paper | PF Paper | Max DD (%) | Días Activo | Est. Días a 100 | Estado del Gate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Pairs_Stat_Arb_Base` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 2.23 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `Pairs_W90_Z2.5_S3.5_H24` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 1.54 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |
| `Pairs_W90_Z2.4_S3.5_H24` | **0 / 100** | **0.0%** | 100 | 0.0% | $0.00 | 0.00 | 0.0% | 1.54 | INSUFFICIENT_FORWARD_DATA | `PAPER_ACTIVE` |

---

## 2. Detalle de Señales y Operativa

### 📌 `Pairs_Stat_Arb_Base`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Promedio por Trade**: `$0.00 USD`
- **Holding Promedio**: `0.0 barras`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Última Señal**: `Ninguna señal registrada aún`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `Pairs_W90_Z2.5_S3.5_H24`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Promedio por Trade**: `$0.00 USD`
- **Holding Promedio**: `0.0 barras`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Última Señal**: `Ninguna señal registrada aún`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

### 📌 `Pairs_W90_Z2.4_S3.5_H24`
- **Primer Trade Paper**: `N/A`
- **Último Trade Paper**: `N/A`
- **Promedio por Trade**: `$0.00 USD`
- **Holding Promedio**: `0.0 barras`
- **Racha Máxima de Pérdidas**: `0 trades`
- **Última Señal**: `Ninguna señal registrada aún`
- **Alertas / Anomalías**: `✅ Normal (Sin anomalías)`

---

## 3. Análisis de Solapamiento del Portafolio (Portfolio Overlap)

| Par de Estrategias | Entradas Simultáneas | % de Solapamiento | Estado Operativo |
| :--- | :---: | :---: | :---: |
| `Base` vs `W90_Z2.5_S3.5_H24` | **0** | **0.0%** | ℹ️ Supervisión Continua |
| `Base` vs `W90_Z2.4_S3.5_H24` | **0** | **0.0%** | ℹ️ Supervisión Continua |
| `W90_Z2.5` vs `W90_Z2.4` | **0** | **0.0%** | ℹ️ Supervisión Continua |

> [!NOTE]
> El solapamiento es una métrica de monitoreo e información. **No bloquea la ejecución** de las estrategias ni altera los parámetros configurados.

---

## 4. Reglas del Paper Gate y Criterios de Promoción

1. **Requisito Cuantitativo**: Cada estrategia debe acumular de forma independiente $\ge 100$ trades cerrados en forward paper mode (`gate_status == 'PAPER_GATE_READY'`).
2. **Requisito Cualitativo**:
   - $\text{PF Paper} \ge 1.20$
   - $\text{Max DD Paper} < 12.0\%$
   - Ausencia de anomalías de ejecución (`SLIPPAGE_BREACH`, `EXCESSIVE_FEES`).
3. **Cero Bypass**:
   - `OPEN` trades no cuentan hacia el umbral de 100.
   - Backtests históricos no cuentan hacia el umbral de 100.
   - `APPROVED` requiere firma manual humana explícita posterior a la aprobación del Paper Gate.
