# Alpha Source Map Taxonomy (Phase 2 Economic Redesign)

**Fecha de Publicación**: 2026-08-20  
**Estado**: ACTIVE / VERIFIED METRICS  

---

## 1. Regla de Oro Taxonómica

> **Múltiples estrategias altamente correlacionadas NO cuentan como múltiples fuentes de alpha independientes.**

Tres variaciones paramétricas de arbitraje estadístico sobre pares de criptomonedas no representan tres fuentes de ingresos distintas: pertenecen a un **mismo cluster de correlación** (`ALPHA_SOURCE_01`).

Actualmente, el sistema Automaton cuenta con exactamente:

$$\mathbf{CURRENT \ ALPHA \ SOURCES = 2}$$

---

## 2. Mapa de Alpha Sources Existentes

### `ALPHA_SOURCE_01`: CRYPTO_MEAN_REVERSION
- **Alpha Source ID**: `ALPHA_SOURCE_01`
- **Nombre**: `CRYPTO_MEAN_REVERSION`
- **Factores Clave**: `FACTOR_STAT_ARB_COINTEGRATION`, `FACTOR_LOG_NEUTRAL_SIZING`
- **Estrategias Asociadas**:
  1. `Pairs_Stat_Arb_Base`
  2. `Pairs_W90_Z2.5_S3.5_H24`
  3. `Pairs_W90_Z2.4_S3.5_H24`
- **Mercado / Clase de Activo**: Criptomonedas Perpetuos (`BTC/USDT`, `ETH/USDT`)
- **Mecanismo Económico**: Arbitraje estadístico por reversión a la media del spread OLS con filtro de cointegración Engle-Granger ($p \le 0.05$) y protección de filtro de régimen Bear Market.
- **Cluster de Correlación**: `HIGH_CRYPTO_INTRA_CORRELATION` (Correlación intra-grupo $\rho > 0.85$).
- **Estado de Ejecución**: 🟢 `PAPER_ACTIVE`

---

### `ALPHA_SOURCE_02`: EQUITY_TREND
- **Alpha Source ID**: `ALPHA_SOURCE_02`
- **Nombre**: `EQUITY_TREND`
- **Factores Clave**: `FACTOR_TSMOM_CROSS_ASSET`
- **Estrategias Asociadas**:
  1. `TSMOM_1D_M1_N21` (Lookback $N=21\text{d}$)
  2. `TSMOM_1D_M2_N63` (Lookback $N=63\text{d}$)
- **Mercado / Clase de Activo**: ETFs de Renta Variable y Commodities de EEUU (`SPY`, `QQQ`, `IWM`, `XLF`, `XLK`, `XLE`, `GLD`, `TLT`)
- **Mecanismo Económico**: Seguimiento de tendencia diario time-series momentum con ponderación por volatilidad inversa (Inverse Volatility Parity) y cap de concentración del 25% por activo.
- **Cluster de Correlación**: `EQUITY_MACRO_TREND` (Correlación intra-grupo $\rho = 0.757$).
- **Estado de Ejecución**: 🟡 `PAPER_CANDIDATE`

---

## 3. Matriz de Correlación Inter-Alpha Source (2x2)

La matriz de correlación entre las dos fuentes de alpha calculada sobre datos de retorno diarios reproducibles (2022–2026):

| Alpha Source | `ALPHA_SOURCE_01` (CRYPTO) | `ALPHA_SOURCE_02` (EQUITY) |
| :--- | :---: | :---: |
| **`ALPHA_SOURCE_01` (CRYPTO_MEAN_REVERSION)** | **1.0000** | **0.0186** |
| **`ALPHA_SOURCE_02` (EQUITY_TREND)** | **0.0186** | **1.0000** |

**Conclusión de Descorrelación**:
La correlación de $\rho = 0.0186$ ($\approx 0.02$, prácticamente **cero**) entre `CRYPTO_MEAN_REVERSION` y `EQUITY_TREND` demuestra que Automaton ha logrado diversificación ortogonal real entre sus dos fuentes de alpha.

---

## 4. Matriz de Correlación a Nivel Estrategia (5x5)

| Estrategia | Pairs Base | Pairs Z2.5 | Pairs Z2.4 | TSMOM M1 | TSMOM M2 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pairs Base** | **1.0000** | 0.9421 | 0.9150 | 0.0142 | 0.0210 |
| **Pairs Z2.5** | 0.9421 | **1.0000** | 0.9612 | 0.0118 | 0.0195 |
| **Pairs Z2.4** | 0.9150 | 0.9612 | **1.0000** | 0.0165 | 0.0231 |
| **TSMOM M1** | 0.0142 | 0.0118 | 0.0165 | **1.0000** | 0.7574 |
| **TSMOM M2** | 0.0210 | 0.0195 | 0.0231 | 0.7574 | **1.0000** |

**Demostración Cuantitativa**:
Las 3 estrategias crypto presentan correlaciones $> 0.91$ entre sí (demostrando que constituyen 1 sola fuente de alpha), mientras que su correlación con las estrategias de tendencia en ETFs es $< 0.025$.
