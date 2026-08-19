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
  - ⛔ **NO REPETIR** el mecanismo Donchian 4H + ATR trailing estándar sin una hipótesis estructuralmente diferente.

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
  - ⛔ **NO REPETIR** rotaciones de momentum transversal con rebalanceo de alta frecuencia en 4H sin amortiguadores de turnover o filtros de dispersión.

---

### 3. `VOLATILITY_COMPRESSION_BREAKOUT` (Batch C)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Rompimiento de canales Donchian (B=20 o 30) condicionado a compresión previa de Bollinger Bandwidth (Percentil 10, 15, 20 en 120 barras 4h) + ATR Trailing Stop (k=2.5).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: $0.59 - 0.71$
  - Max Drawdown: $16.0\% - 30.8\%$
  - Expectancy: $-\$2.31$ a $-\$1.57$ USD / trade
- **Autopsia Cuantitativa**:
  - El filtro de compresión previa reduce el número de trades pero los falsos rompimientos y trailing stops siguen generando expectativa negativa.
- **Veredicto**:
  - ⛔ **NO REPETIR** rompimientos de compresión con trailing stops fijos en 4H sin filtros adicionales de régimen direccional macro.

---

### 4. `EVENT_SHOCK_REVERSAL_1H` (EVENT_SHOCK_PROXY - Batch D)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Entrada en contra de velas de 1H con shock de retorno ($|Z_{\text{ret}}| \ge 2.0 - 3.0$) y pico de volumen ($Z_{\text{vol}} \ge 1.5 - 2.0$) buscando reversión hacia SMA 20 con Time-Stop máximo incondicional de 4 velas (4h).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: $0.62 - 0.72$
  - Max Drawdown: $35.2\% - 51.5\%$
  - Expectancy: $-\$1.13$ a $-\$0.76$ USD / trade
- **Autopsia Cuantitativa**:
  - Los shocks de precio y volumen en 1H tienden a continuar en cascada direccional a corto plazo (momentum de liquidación); la reversión a 4 barras no compensa las pérdidas en cascadas fuertes.
- **Veredicto**:
  - ⛔ **NO REPETIR** reversión ciega de shocks extremos en 1H sin confirmación de agotamiento en libro de órdenes o datos reales de desequilibrio de funding/liquidaciones.

---

### 5. `FUNDING_CONTRARIAN` (Batch E)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Reversión media 1H hacia SMA 20 tras publicación de Funding Rate 8H extremo ($Z_{\text{funding}} \ge 1.5 - 2.5$) y extensión de precio ($0.5 - 1.0 \times \text{ATR}$), con Time-Stop de 8 horas y Stop de emergencia del 3.0%.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.57 - 0.61
  - Max Drawdown: 2.3% - 8.0%
  - Expectancy: $-1.42 a $-0.90 USD / trade
- **Autopsia Cuantitativa**:
  - El funding rate extremo actúa como señal de persistencia de régimen en lugar de agotamiento inmediato a 8h; los mercados pueden mantener funding extremo durante días en rallies y caídas fuertes.
- **Veredicto**:
  - ⛔ **NO REPETIR** reversión ciega de funding rates extremos en 8H sin filtros de agotamiento de volumen o ruptura de estructura de tendencia.

### 6. `LIQUIDATION_DERIVATIVES_REVERSAL` (DERIVATIVES_SHOCK_REVERSAL - Batch D2)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Reversión 1H hacia SMA 20 con Time-Stop de 4 velas y Stop de emergencia del 3.0%, activada exclusivamente por conjunción estricta de:
  - Shock de retorno ($|Z_{\text{ret}}| \ge 2.0 - 3.0$)
  - Shock de Open Interest ($|Z_{\Delta \text{OI}}| \ge 2.0 - 2.5$)
  - Desequilibrio extremo de flujo Taker ($|Z_{\text{taker}}| \ge 2.0 - 2.5$)
  - Confirmación de Funding Rate ($Z_{\text{funding}}$)
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.00 - 0.64
  - Max Drawdown: 0.1% - 0.9%
  - Expectancy: $-2.21 a $-0.77 USD / trade
- **Autopsia Cuantitativa**:
  - El filtro conjunto de OI y Taker Imbalance redujo falsas entradas, pero el número de trades calificados fue insuficiente (<100) y las cascadas fuertes mantuvieron expectativa negativa.
- **Veredicto**:
  - ⛔ **NO REPETIR** reversión de derivados con time-stops cortos en 1H sin confirmación de formación de suelo/techo en estructura de precios.

### 7. `FUNDING_MOMENTUM_1H` (Batch F)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Continuación direccional 1H entrando a favor de Funding Rate 8H ($Z_{\text{funding}} \ge 0.5 - 1.5$) confirmado por momentum de precio a 12h o 24h, con salida por neutralidad/inversión y Time-Stop de 24 horas.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.71 - 0.94
  - Max Drawdown: 3.6% - 18.5%
  - Expectancy: $-0.71 a $-0.13 USD / trade
- **Autopsia Cuantitativa**:
  - El momentum de funding sufre de 'late entry drag': cuando el funding alcanza Z>=1.0 y el momentum de 12-24h se confirma, el movimiento ya está maduro y propenso a retrocesos inmediatos.
- **Veredicto**:
  - ⛔ **NO REPETIR** seguimiento de momentum de funding en 1H sin filtros de punto de entrada temprano o descuento en libro de órdenes.

### 8. `BASIS_SPOT_PERP` (Batch G)
- **Estado**: 🔴 **REJECTED (TODAS KILLED)**
- **Mecanismo**: Posición delta-neutral. Si Z-Score del Basis (Perp - Spot) >= Umbral, Long Spot + Short Perp. Salida al cruzar media.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: 0.00 - 0.00
  - Max Drawdown: 2.7% - 100.8%
  - Expectancy: $-1.58 a $-1.46 USD / trade
- **Autopsia Cuantitativa**:
  - El basis en mercados crypto modernos (2024+) se arbitra demasiado rápido y el costo de fees (0.16% roundtrip en dos patas) destruye el minúsculo yield antes de la reversión a la media.
- **Veredicto**:
  - ⛔ **NO REPETIR** arbitraje estadístico de basis en timeframes intradiarios donde las comisiones conjuntas superan el spread.

---

### 9. `MEAN_REVERSION_1H_FREQUENCY_EXPANSION` (Batch H - ADF Threshold)
- **Estado**: 🔴 **REJECTED (FREQUENCY_EXPANSION_FAILED)**
- **Mecanismo**: Relajar el filtro de cointegración/estacionariedad Augmented Dickey-Fuller (ADF) de $p \le 0.05$ hacia $p \in [0.07, 0.10, 0.15, 0.20]$ sobre pares 1H con $W=90, Z=2.5, S=3.5, H=24$.
- **Resultados Comparativos Out-of-Sample (2024 - 2026)**:
  - **H1 (ADF $\le 0.05$, Baseline)**: $PF = 1.37$ | $DD = 6.70\%$ | $Trades = 305$ ($9.69$/mes) | $Exp = +\$3.45$ | Rejection: $89.1\%$ (SURVIVOR).
  - **H2 (ADF $\le 0.07$)**: $PF = 1.16$ | $DD = 17.19\%$ | $Trades = 343$ ($11.20$/mes) | $Exp = +\$1.74$ | Rejection: $86.9\%$ (KILLED: $PF \le 1.30$, $DD \ge 15\%$).
  - **H3 (ADF $\le 0.10$)**: $PF = 1.15$ | $DD = 19.26\%$ | $Trades = 402$ ($12.99$/mes) | $Exp = +\$1.66$ | Rejection: $84.2\%$ (KILLED: $PF \le 1.30$, $DD \ge 15\%$).
  - **H4 (ADF $\le 0.15$)**: $PF = 1.06$ | $DD = 16.76\%$ | $Trades = 474$ ($15.40$/mes) | $Exp = +\$0.63$ | Rejection: $80.3\%$ (KILLED: $PF \le 1.30$, $DD \ge 15\%$).
  - **H5 (ADF $\le 0.20$)**: $PF = 0.96$ | $DD = 26.62\%$ | $Trades = 531$ ($17.55$/mes) | $Exp = -\$0.44$ | Rejection: $76.2\%$ (KILLED: $PF \le 1.30$, $DD \ge 15\%$, $PnL < 0$).
- **Autopsia Cuantitativa**:
  - **Degradación Monotónica**: Incrementar el umbral ADF de 0.05 a 0.20 aumenta el volumen de trades (+74%), pero destruye el edge al degradar el PF ($1.37 \to 0.96$) y casi cuadruplicar el drawdown ($6.70\% \to 26.62\%$).
  - **Causa Estructural**: El filtro ADF $p < 0.05$ no es un cuello de botella ineficiente, sino el **filtro de calidad esencial de la estrategia**. Cuando $p \ge 0.07$, se admiten series no cointegradas que están en tendencia o deriva (random walk), las cuales no revierten a la media, alcanzan el stop $Z=3.5$ o el time-stop $H=24$, pagando comisiones taker dobles.
- **Veredicto / Prohibición**:
  - ⛔ **NO RELAJAR** el filtro ADF por encima de $p = 0.05$. El umbral $p \le 0.05$ es matemáticamente óptimo e innegociable para la preservación de capital.
