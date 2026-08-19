# Auditoría de Frecuencia y Factibilidad del Paper Gate (2022 - 2026)

Este documento audita la **frecuencia real de señales y trades** de las 3 estrategias `PAPER_ACTIVE` sobre datos históricos continuos de 1H (2022-01-01 a 2026-08-16, ~4.62 años), evaluando la tasa de acumulación hacia el objetivo de **100 trades cerrados en forward paper mode**.

---

## 1. Resumen Ejecutivo de Frecuencia y Tiempo Estimado

| Estrategia | $Z_{\text{entry}}$ | Trades Totales (4.62a) | Trades / Año | Trades / Mes | Intervalo Promedio (Portafolio) | Tiempo Estimado para 100 Trades | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Pairs_Stat_Arb_Base` | `2.5` | **537** | **116.2** | **9.69** | 3.1 días (74.4h) | **10.3 meses** (~314 días) | `PAPER_GATE_FEASIBLE` |
| `Pairs_W90_Z2.5_S3.5_H24` | `2.5` | **537** | **116.2** | **9.69** | 3.1 días (74.4h) | **10.3 meses** (~314 días) | `PAPER_GATE_FEASIBLE` |
| `Pairs_W90_Z2.4_S3.5_H24` | `2.4` | **562** | **121.6** | **10.13** | 3.0 días (72.0h) | **9.9 meses** (~300 días) | `PAPER_GATE_FEASIBLE` |

> [!NOTE]
> **Veredicto Global**: **`PAPER_GATE_FEASIBLE`**.
> Evaluado con el motor canónico exacto (`validator.py` y `PairsTradingStatArb`), cada estrategia genera en promedio **~116 a 122 trades cerrados por año** (~9.7 a 10.1 trades/mes por estrategia), lo que permite acumular **100 trades en ~10 meses de ejecución continua**.
> Si se evalúan las 3 estrategias concurrentemente dentro del runner, el portafolio genera **~350+ ejecuciones combinadas por año** (~29 trades/mes a nivel portafolio agregando las 3 variantes).

---

## 2. Desglose Detallado por Par de Activos (2022 - 2026)

### 📊 Estrategia: `Pairs_Stat_Arb_Base` ($Z=2.5$)

| Par de Activos | Trades Totales | Trades / Año | Trades / Mes | Intervalo Medio |
| :--- | :---: | :---: | :---: | :---: |
| `BTCUSDT/ETHUSDT` | **181** | 39.2 | 3.27 | 9.3 días |
| `AVAXUSDT/SOLUSDT` | **199** | 43.1 | 3.59 | 8.5 días |
| `LINKUSDT/DOTUSDT` | **157** | 34.0 | 2.83 | 10.7 días |
| **TOTAL** | **537** | **116.2** | **9.69** | **3.1 días** |

---

## 3. Desglose en Validación OOS (2024 - 2026)

| Par de Activos | Trades OOS (2024-2026) | Trades / Año | Trades / Mes |
| :--- | :---: | :---: | :---: |
| `BTCUSDT/ETHUSDT` | **108** | 41.2 | 3.44 |
| `AVAXUSDT/SOLUSDT` | **121** | 46.2 | 3.85 |
| `LINKUSDT/DOTUSDT` | **75** | 28.6 | 2.39 |
| **TOTAL OOS** | **304** | **116.0** | **9.67** |

---

## 4. Auditoría de Integridad del Paper Runner

- **Verificación de Adapters**: Las 3 estrategias cargadas coinciden exactamente con `registry.json`.
- **Lógica Matemática**: Utiliza OLS $\gamma$ fijo por ventana de 90 barras y test ADF con selección AIC (`autolag='AIC'`).
- **Detección de Bugs**: **`NO BUGS DETECTED`**. El runner forward reproduce con fidelidad matemática la tasa de ejecución de ~9.7 trades/mes.

---

## 5. Conclusión Final y Factibilidad Operacional

1. **Factibilidad**: **`PAPER_GATE_FEASIBLE`**.
2. **Ritmo de Generación Real**: **~9.7 a 10.1 trades/mes** por estrategia.
3. **Plazo para 100 Trades**: **~10.3 meses** por estrategia individual en forward paper mode.
4. **Seguridad**:
   - `APPROVED = false`
   - `DEMO_ORDERS = 0`
   - `REAL_ORDERS = 0`
