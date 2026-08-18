# 🧠 Automaton Research Ledger: Memoria de Hipótesis y Autopsias Cuantitativas

> **REGLA DE INVESTIGACIÓN AUTOMATON**:
> Consultar este libro antes de generar variantes. **Prohibido repetir hipótesis ya rechazadas** o alterar cosméticamente estrategias cuya estructura matemática básica haya demostrado expectativa negativa.

---

## 🏛️ Familias de Estrategias Evaluadas

### 1. `TREND_FOLLOWING_4H` (Batch A)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Donchian Breakout (N=20 a 40 velas de 4h) + ATR Trailing Stop (k=2.0 a 3.0).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: $0.39 - 0.66$ ($\ll 1.30$).
  - Max Drawdown: $45.5\% - 131.1\%$.
  - Expectancy: $-\$3.56$ a $-\$2.55$ USD / trade.
- **Autopsia Cuantitativa**:
  - En cripto en 4H, los rompimientos de máximos/mínimos sufren de reversión a la media frecuente antes de establecer una tendencia limpia (falsos breakouts).
  - Los trailing stops basados en ATR provocan salidas anticipadas en correcciones normales, pagando comisiones taker continuas ($0.16\%$ por ciclo).
- **Veredicto / Prohibición**:
  - ⛔ **NO REPETIR** el mecanismo Donchian 4H + ATR trailing estándar sin una hipótesis estructuralmente diferente (por ejemplo, filtros de compresión previa o regímenes macro explícitos).

---

### 2. `CROSS_SECTIONAL_MOMENTUM_4H` (Batch B)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Long #1 Winner / Short #6 Loser sobre un universo de 6 activos (`BTC`, `ETH`, `SOL`, `AVAX`, `LINK`, `DOT`) con rebalanceo sistemático cada 4H en lookbacks de $N \in [6, 12, 24, 48, 72]$.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: $0.82 - 0.92$ ($\ll 1.30$).
  - Max Drawdown: $6.1\% - 22.8\%$.
  - Expectancy: $-\$0.30$ a $-\$0.17$ USD / trade.
  - Trades: $1,264 - 4,369$ operaciones.
- **Autopsia Cuantitativa**:
  - **Turnover Destructivo**: El rebalanceo cada 4h genera una rotación extrema. El diferencial de rendimiento transversal promedio en 4h ($0.15\% - 0.25\%$) es absorbido en más del $80\%$ por la fricción de comisiones taker ($0.16\%$).
  - **Reversión a Corto Plazo en Altcoins**: Las altcoins que lideran el momentum a 24h-48h tienden a sufrir tomas de ganancias inmediatas en las siguientes velas, penalizando la pata Long.
- **Veredicto / Prohibición**:
  - ⛔ **NO REPETIR** rotaciones de momentum transversal con rebalanceo de alta frecuencia en 4H sin amortiguadores de turnover (hysteresis bands) o filtros de dispersión de volatilidad.

### 3. `VOLATILITY_COMPRESSION_BREAKOUT` (Batch C)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Rompimiento de canales Donchian (B=20 o 30) condicionado a compresión previa de Bollinger Bandwidth (Percentil 10, 15, 20 en 120 barras 4h) + ATR Trailing Stop (k=2.5).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.59 - 0.71
  - Max Drawdown: 16.0% - 30.8%
  - Expectancy: $-2.31 a $-1.57 USD / trade
- **Autopsia Cuantitativa**:
  - El filtro de compresión previa reduce el número de trades pero los falsos rompimientos y trailing stops siguen generando expectativa negativa.
- **Veredicto**:
  - ⛔ **NO REPETIR** rompimientos de compresión con trailing stops fijos en 4H sin filtros adicionales de régimen direccional macro.

### 4. `EVENT_SHOCK_REVERSAL_1H` (EVENT_SHOCK_PROXY - Batch D)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Entrada en contra de velas de 1H con shock de retorno ($|Z_{\text{ret}}| \ge 2.0 - 3.0$) y pico de volumen ($Z_{\text{vol}} \ge 1.5 - 2.0$) buscando reversión hacia SMA 20 con Time-Stop máximo incondicional de 4 velas (4h).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.62 - 0.72
  - Max Drawdown: 35.2% - 51.5%
  - Expectancy: $-1.13 a $-0.76 USD / trade
- **Autopsia Cuantitativa**:
  - Los shocks de precio y volumen en 1H tienden a continuar en cascada direccional a corto plazo (momentum de liquidación); la reversión a 4 barras no compensa las pérdidas en cascadas fuertes.
- **Veredicto**:
  - ⛔ **NO REPETIR** reversión ciega de shocks extremos en 1H sin confirmación de agotamiento en libro de órdenes o datos reales de desequilibrio de funding/liquidaciones.
