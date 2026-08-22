# Factor Library & Taxonomy Catalog (Phase 2 Economic Redesign)

**Fecha de Publicación**: 2026-08-20  
**Estado**: ACTIVE / VERIFIED  

---

## 1. Visión General de la Biblioteca de Factores

La **Factor Library** extiende el sistema de memoria de Automaton para desacoplar el descubrimiento de señales (*Alpha Factors*) de la construcción de estrategias individuales.

Un factor no requiere ser rentable de manera aislada (*standalone*); su valor radica en su capacidad de aportar descorrelación, expansiones de Sharpe o filtros de régimen a la arquitectura global.

---

## 2. Taxonomía de Clasificación de Factores

- **`FACTOR_VALIDATED`**: Factor con ventaja estadística comprobada standalone ($PF > 1.30$) o con aporte positivo de portafolio ($\Delta \text{Sharpe} > +0.15$, $\rho < 0.20$).
- **`FACTOR_WEAK`**: Factor con información direccional u holística positiva (ej. evento positivo $+1.7\%$ a 10d), pero con riesgo standalone inaceptable sin stop loss o alta volatilidad.
- **`FACTOR_REJECTED`**: Factor donde la fricción de comisiones o la falta de estacionariedad destruye el rendimiento, o la correlación es nula.
- **`DATASET_UNAVAILABLE`**: Factor teóricamente concebido cuya evaluación requiere fuentes de datos comerciales no disponibles en feeds públicos gratuitos.

---

## 3. Catálogo Completo de Factores Históricos (Batches A – O)

| Factor ID | Familia | Tipo de Factor | Clasificación | Standalone PF | Standalone DD | Expectancy | Correlación con Portafolio | Research Score | Source Batch | Notas y Reclasificación |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`FACTOR_BATCH_A`** | `TREND_FOLLOWING_4H` | Momentum Breakout | 🔴 `FACTOR_REJECTED` | 0.66 | 131.1% | -$2.55 | 0.35 | 4.2 | Batch A | Whipsaws constantes en 4H y fricción acumulada de trailing stops. |
| **`FACTOR_BATCH_B`** | `CROSS_SECTIONAL_MOMENTUM_4H` | Cross-Sectional | 🔴 `FACTOR_REJECTED` | 0.92 | 22.8% | -$0.17 | 0.40 | 6.5 | Batch B | Turnover masivo (1200-4300 trades); comisiones de 16 bps destruyen la dispersión. |
| **`FACTOR_BATCH_C`** | `VOLATILITY_COMPRESSION_BREAKOUT` | Volatility Compression | 🔴 `FACTOR_REJECTED` | 0.71 | 30.8% | -$1.57 | 0.28 | 5.8 | Batch C | Falsos rompimientos tras compresión de Bollinger mantienen expectativa negativa. |
| **`FACTOR_BATCH_D`** | `EVENT_SHOCK_REVERSAL_1H` | Event Shock | 🔴 `FACTOR_REJECTED` | 0.72 | 51.5% | -$0.76 | 0.15 | 7.1 | Batch D | Shocks de precio/volumen en 1H continúan en cascada direccional (momentum de liquidación). |
| **`FACTOR_BATCH_D2`** | `LIQUIDATION_DERIVATIVES_REVERSAL` | Microstructure Liquidation | 🔴 `FACTOR_REJECTED` | 0.64 | 0.9% | -$0.77 | 0.10 | 8.4 | Batch D2 | Frecuencia de oportunidades insosteniblemente baja (< 100 trades). |
| **`FACTOR_BATCH_E`** | `FUNDING_CONTRARIAN` | Funding Rate Anomaly | 🔴 `FACTOR_REJECTED` | 0.61 | 8.0% | -$0.90 | 0.12 | 6.9 | Batch E | Funding extremo actúa como persistencia de régimen en lugar de agotamiento inmediato. |
| **`FACTOR_BATCH_F`** | `FUNDING_MOMENTUM_1H` | Funding Momentum | 🔴 `FACTOR_REJECTED` | 0.94 | 18.5% | -$0.13 | 0.22 | 7.5 | Batch F | Late entry drag: cuando el momentum a 12h-24h confirma, el movimiento ya está maduro. |
| **`FACTOR_BATCH_G`** | `BASIS_SPOT_PERP` | Basis Arbitrage | 🔴 `FACTOR_REJECTED` | 0.00 | 100.8% | -$1.46 | 0.05 | 5.0 | Batch G | El basis en crypto se arbitra rápidamente; comisiones taker consumen el rendimiento. |
| **`FACTOR_BATCH_H`** | `MEAN_REVERSION_1H_FREQUENCY_EXPANSION` | Cointegration Threshold | 🔴 `FACTOR_REJECTED` | 0.96 | 26.6% | -$0.44 | 0.85 | 3.1 | Batch H | Relajar ADF p > 0.05 admite caminatas aleatorias no estacionarias y cuadruplica DD. |
| **`FACTOR_BATCH_I`** | `MEAN_REVERSION_1H_UNIVERSE_EXPANSION` | Pair Selection | 🟡 `FACTOR_WEAK` | 1.22 | 195.3% | -$97.69 | 0.70 | 6.2 | Batch I | Pares altcoins cruzados sufren de distorsión de escala de beta inter-capa. |
| **`FACTOR_BATCH_J`** | `LOG_DOLLAR_NEUTRAL_STAT_ARB_1H` | Log Neutral Sizing | 🟢 `FACTOR_VALIDATED` | 1.02 | 0.7% | $0.02 | 0.65 | 12.5 | Batch J | Formulación logarítmica elimina la distorsión de beta y mantiene DD < 1.0%. |
| **`FACTOR_BATCH_K`** | `CROSS_EXCHANGE_LEAD_LAG_5M` | Cross-Exchange Latency | 🔴 `FACTOR_REJECTED` | 0.58 | 15.8% | -$0.70 | 0.02 | 8.0 | Batch K | Arbitraje 5m dominado por HFT sub-segundo; comisiones arruinan el edge. |
| **`FACTOR_BATCH_L`** | `EQUITY_OVERNIGHT_GAP_REVERSAL_1D` | Overnight Gap | 🔴 `FACTOR_REJECTED` | 0.93 | 3.9% | -$0.13 | 0.04 | 7.8 | Batch L | Gaps bajistas nocturnos en ETFs reflejan revalorizaciones macro y no revierten intradía. |
| **`FACTOR_BATCH_M`** | `CROSS_ASSET_TSMOM_1D` | Macro Trend Following | 🟢 `FACTOR_VALIDATED` | 2.98 | 6.55% | $14.53 | 0.03 | 18.5 | Batch M | Seguimiento de tendencia multi-activo demuestra fuerte alpha ortogonal (PF 1.64-2.98). |
| **`FACTOR_BATCH_N`** | `FUTURES_TERM_STRUCTURE_CARRY` | Futures Term Structure | ⚪ `DATASET_UNAVAILABLE` | 0.00 | 0.0% | $0.00 | 0.00 | 0.0 | Batch N | Faltan datos públicos de vencimientos simultáneos reales (F_near vs F_far). |
| **`FACTOR_BATCH_O`** | `SEC_INSIDER_CLUSTER_BUYING` | Event Insider Accumulation | 🟡 `FACTOR_WEAK` | 1.33 | 92.5% | $1.51 | 0.01 | 14.2 | Batch O | Muestra drift positivo a 10d (+1.7%), pero desprovisto de stop loss sufre DD > 90%. |

---

## 4. Reclasificaciones Históricas y Justificación

1. **Batch M (`CROSS_ASSET_TSMOM_1D`)**:
   - Reclasificado a **`FACTOR_VALIDATED`**.
   - Justificación: Estrategias M1 ($N=21\text{d}$) y M2 ($N=63\text{d}$) superan los filtros Standalone ($PF = 1.64 - 2.98, DD = 6.55\% - 9.91\%$) y aportan descorrelación pura ($\rho = 0.0186$) con el portafolio crypto.
2. **Batch O (`SEC_INSIDER_CLUSTER_BUYING`)**:
   - Reclasificado a **`FACTOR_WEAK`**.
   - Justificación: Aunque fue rechazado como estrategia *standalone* por drawdowns masivos ($> 90\%$) debido al holding ciego de 20 días sin stop loss, el evento de cluster buying en Form 4 demuestra una anomalía predictiva positiva a 10 días ($+1.78\%$). Se conserva en memoria como señal contextual de filtro.
3. **Batch J (`LOG_DOLLAR_NEUTRAL_STAT_ARB_1H`)**:
   - Reclasificado a **`FACTOR_VALIDATED` (en herramienta de Sizing)**.
   - Justificación: La transformación logarítmica y neutral en dólares corrigió con éxito la distorsión de escala nominal de beta y mantuvo el drawdown por debajo del $1.0\%$.
