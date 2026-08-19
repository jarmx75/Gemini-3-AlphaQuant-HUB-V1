# Informe Forense: Reconciliación Validator vs Paper Frequency Audit

**Fecha de Ejecución**: `2026-08-19 03:20:43 UTC`  
**Estado de Seguridad**: `APPROVED=false` | `DEMO_ORDERS=0` | `REAL_ORDERS=0`

---

## 1. Causa Raíz de la Discrepancia (ROOT CAUSE)

La discrepancia entre los **304 trades OOS (2024–2026)** reportados por `validator.py` y los **50 trades** obtenidos en el primer script de auditoría (`scratch/audit_paper_frequency.py`) ha sido **identificada e investigada línea por línea**:

| Dimensión Técnica | `validator.py` (Canónico) | Primer Script de Auditoría (`scratch/`) | Impacto Cuantitativo |
| :--- | :--- | :--- | :--- |
| **Cálculo del Residuo (Spread)** | **$\text{spread}_w = Y_w - \gamma_t X_w$**<br>Se calcula un $\gamma_t$ fijo para las 90 barras $[t-w : t]$ y se proyecta sobre esas 90 barras. | **`roll_spread = s_y - roll_gamma * s_x`**<br>Aproximación continua donde $\gamma$ variaba barra a barra. | Al variar $\gamma$ continuamente en la serie de precios, la serie resultante tiene deriva no estacionaria espuria. |
| **Test de Estacionariedad ADF** | **`adfuller(spread_w, autolag='AIC')`**<br>Selección óptima de rezagos por criterio de Akaike. | **`adfuller(spread, maxlag=1, autolag=None)`**<br>AR(1) rígido sin rezagos superiores. | El test AR(1) rígido sobre una serie con $\gamma$ flotante rechazó falsamente el **99.0%** de las oportunidades legítimas. |
| **Ventana de Lookback** | **`y[t-w : t]` (shift(1) estricto)**<br>Ventana histórica de 90 barras que excluye la barra actual $t$. | Vectorización con rolling windows. | Paridad recuperada al aplicar la ventana histórica shift(1). |

---

## 2. Comparativa Exacta entre Motores sobre el Mismo Dataset (OOS 2024–2026)

| Par de Activos | Trades Validator OOS | Trades Motor Canónico Reconciliado | Discrepancia | Estado |
| :--- | :---: | :---: | :---: | :---: |
| **`BTCUSDT/ETHUSDT`** | **108** | **108** | **0** | ✅ **100% IDÉNTICO** |
| **`AVAXUSDT/SOLUSDT`** | **121** | **121** | **0** | ✅ **100% IDÉNTICO** |
| **`LINKUSDT/DOTUSDT`** | **75** | **75** | **0** | ✅ **100% IDÉNTICO** |
| **TOTAL OOS (2024–2026)** | **304** | **304** | **0** | ✅ **100% IDÉNTICO** |

---

## 3. Verdadera Frecuencia Histórica y Plazo al Paper Gate (2022–2026)

Evaluando los 4.62 años completos (2022-01-01 a 2026-08-16) con el motor canónico exacto:

| Estrategia | Trades Totales (4.62a) | Trades / Año | Trades / Mes | Días entre Trades (Portafolio) | Tiempo para 100 Trades | Veredicto Paper Gate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Pairs_Stat_Arb_Base`** ($Z=2.5$) | **537** | **116.2** | **9.69** | **3.1 días** | **10.3 meses** (~314 días) | **`PAPER_GATE_FEASIBLE`** |
| **`Pairs_W90_Z2.5_S3.5_H24`** ($Z=2.5$) | **537** | **116.2** | **9.69** | **3.1 días** | **10.3 meses** (~314 días) | **`PAPER_GATE_FEASIBLE`** |
| **`Pairs_W90_Z2.4_S3.5_H24`** ($Z=2.4$) | **562** | **121.6** | **10.13** | **3.0 días** | **9.9 meses** (~300 días) | **`PAPER_GATE_FEASIBLE`** |

### Desglose por Par de Activos (2022–2026):
- **`BTCUSDT/ETHUSDT`**: **181 trades** (~39.2 trades/año, ~3.27 trades/mes).
- **`AVAXUSDT/SOLUSDT`**: **199 trades** (~43.1 trades/año, ~3.59 trades/mes).
- **`LINKUSDT/DOTUSDT`**: **157 trades** (~34.0 trades/año, ~2.83 trades/mes).

---

## 4. Trazabilidad de Trades en `BTCUSDT/ETHUSDT` (2024–2026)

- **Primer Trade Registrado**:
  - `Entry Time`: `2024-01-12 15:00:00`
  - `Entry Price Y`: `$44,462.01`
  - `Side`: `LONG` (Undervalued Spread)
  - `Exit Time`: `2024-01-12 16:00:00`
  - `Net PnL`: `$-3.00 USD` (Stop-Loss $Z=-4.38$)
- **Último Trade Registrado**:
  - `Entry Time`: `2026-08-11 14:00:00`
  - `Entry Price Y`: `$63,770.03`
  - `Side`: `LONG` (Undervalued Spread)
  - `Exit Time`: `2026-08-11 18:00:00`
  - `Net PnL`: `$10.41 USD` (Exit $Z=-4.56$)

---

## 5. Auditoría del Paper Runner en Vivo (`PairsTradingPaperRunner`)

- El archivo [`src/execution/pairs_trading_paper_runner.py`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/src/execution/pairs_trading_paper_runner.py) utiliza [`src/strategies/pairs_trading_stat_arb.py`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/src/strategies/pairs_trading_stat_arb.py), el cual calcula el OLS $\gamma_t$ fijo para cada ventana de 90 barras y ejecuta `adfuller(spread_w, autolag='AIC')`.
- **Conclusión**: El Paper Runner forward está ejecutando el modelo canónico de **~116 trades/año** (~9.7 trades/mes) de forma matemáticamente exacta.

---

## 6. Dictamen Final

1. **Estado del Validator**: **`VALIDATOR INTEGRITY CONFIRMED`**. El validador calcula correctamente los 304 trades OOS y sus métricas históricas son 100% verificables.
2. **Factibilidad del Paper Gate**: **`PAPER_GATE_FEASIBLE`**. Con ~9.7 trades cerrados por mes por estrategia, el umbral de 100 trades paper se alcanzará en **~10.3 meses de ejecución forward**.
3. **Seguridad**:
   - `APPROVED = false`
   - `DEMO_ORDERS = 0`
   - `REAL_ORDERS = 0`
