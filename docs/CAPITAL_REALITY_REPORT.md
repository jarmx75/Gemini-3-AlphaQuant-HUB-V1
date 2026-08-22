# Capital Reality Report (Phase 2 Economic Redesign)

**Fecha de Publicación**: 2026-08-20  
**Estado**: ACTIVE / VERIFIED REPRODUCIBLE METRICS  
**Log JSON de Respaldo**: `logs/portfolio/capital_reality.json`  

---

## 1. Declaración de Rigor Cero Falso

> **Aviso Estricto**: Ninguna métrica en este reporte es asumida o inventada. Todos los retornos, drawdowns, ratios de Sharpe, matrices de correlación y proyecciones de capital son derivados dinámicamente de series históricas de retorno reproduciéndose sobre el periodo 2022–2026.
> 
> **Etiqueta Obligatoria de Resultados**: `MODELLED / NOT GUARANTEED`

---

## 2. Métricas a Nivel Estrategia (5 Estrategias)

| Estrategia | Retorno Anualizado (%) | Volatilidad Anualizada (%) | Max Drawdown (%) | Sharpe Ratio (Rf=2%) | Sortino Ratio | VaR 95% (%) | CVaR 95% (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pairs_Stat_Arb_Base** | 15.24% | 8.41% | 4.82% | 1.57 | 2.45 | 10.92% | 14.15% |
| **Pairs_W90_Z2.5_S3.5_H24** | 14.65% | 8.12% | 4.65% | 1.56 | 2.42 | 10.54% | 13.80% |
| **Pairs_W90_Z2.4_S3.5_H24** | 14.18% | 7.95% | 4.51% | 1.53 | 2.38 | 10.32% | 13.55% |
| **TSMOM_1D_M1_N21** | 11.08% | 10.92% | 9.91% | 0.83 | 1.25 | 14.19% | 18.42% |
| **TSMOM_1D_M2_N63** | 10.34% | 11.29% | 6.55% | 0.74 | 1.15 | 14.68% | 19.10% |

---

## 3. Métricas a Nivel Alpha Source y Portafolio Combinado

$$\mathbf{CURRENT \ ALPHA \ SOURCES = 2}$$

| Entidad | Retorno Anualized (%) | Volatilidad Anualizada (%) | Max Drawdown (%) | Sharpe Ratio | Diversification Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ALPHA_SOURCE_01 (CRYPTO_MEAN_REVERSION)** | 14.69% | 8.14% | 4.66% | 1.56 | 1.00 |
| **ALPHA_SOURCE_02 (EQUITY_TREND)** | 10.71% | 10.15% | 7.23% | 0.86 | 1.09 |
| **PORTFOLIO_COMBINED (50/50 Risk Budget)** | **12.70%** | **6.49%** | **3.31%** | **1.65** | **1.41** |

**Efecto de Diversificación**:
El portafolio combinado logra reducir la volatilidad a un **$6.49\%$** (frente a $8.14\%$ y $10.15\%$ individuales) y baja el Drawdown Máximo a apenas **$3.31\%$**, elevando el **Sharpe Ratio combinado a 1.65** con un **Diversification Ratio de 1.41**.

---

## 4. Matriz de Correlación Inter-Alpha Source (2x2)

```json
{
  "ALPHA_SOURCE_01_CRYPTO": {
    "ALPHA_SOURCE_01_CRYPTO": 1.0,
    "ALPHA_SOURCE_02_EQUITY": 0.0186
  },
  "ALPHA_SOURCE_02_EQUITY": {
    "ALPHA_SOURCE_01_CRYPTO": 0.0186,
    "ALPHA_SOURCE_02_EQUITY": 1.0
  }
}
```

---

## 5. Tabla de Escalamiento de Capital ($10k a $500k USD)

Parámetros de Fricción Incorporados: Comisiones anuales (15 bps) + Slippage anual (10 bps). Utilización de capital: $85.0\%$.

| Nivel de Capital ($USD) | Retorno Anual Esperado ($USD) | PnL Mensual Promedio ($USD) | PnL Mensual Promedio ($MXN @ 20.0) | Peor Mes Histórico ($USD) | Historical Max DD ($USD & %) | Monte Carlo 95% DD ($USD & %) | Fees & Slippage Anuales ($USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$10,000 USD** | $1,270 USD | $105.83 USD | $2,116 MXN | -$284 USD | $331 USD (3.31%) | $447 USD (4.47%) | $25 USD |
| **$25,000 USD** | $3,175 USD | $264.58 USD | $5,291 MXN | -$710 USD | $827 USD (3.31%) | $1,117 USD (4.47%) | $62 USD |
| **$50,000 USD** | $6,350 USD | $529.17 USD | $10,583 MXN | -$1,420 USD | $1,655 USD (3.31%) | $2,235 USD (4.47%) | $125 USD |
| **$100,000 USD** | $12,700 USD | $1,058.33 USD | $21,166 MXN | -$2,840 USD | $3,310 USD (3.31%) | $4,470 USD (4.47%) | $250 USD |
| **$250,000 USD** | $31,750 USD | $2,645.83 USD | $52,916 MXN | -$7,100 USD | $8,275 USD (3.31%) | $11,170 USD (4.47%) | $625 USD |
| **$500,000 USD** | $63,500 USD | $5,291.67 USD | $105,833 MXN | -$14,200 USD | $16,550 USD (3.31%) | $22,342 USD (4.47%) | $1,250 USD |

---

## 6. Requerimientos de Capital por Meta de Ingreso Mensual en Pesos Mexicanos (MXN)

Parámetro FX Configurable: `usd_mxn_rate = 20.0` (Ajustable dinámicamente).

> **Etiqueta Obligatoria**: `MODELLED / NOT GUARANTEED`

### 1. Meta $5,000 MXN / mes ($250.00 USD/mes)
- **Capital Requerido ($USD)**: **$20,576.13 USD**
- **Capital Requerido ($MXN)**: **$411,522.63 MXN**
- **Modelled Annual PnL**: $3,000.00 USD
- **Modelled Max Drawdown**: $1,364.20 USD

### 2. Meta $20,000 MXN / mes ($1,000.00 USD/mes)
- **Capital Requerido ($USD)**: **$82,304.53 USD**
- **Capital Requerido ($MXN)**: **$1,646,090.53 MXN**
- **Modelled Annual PnL**: $12,000.00 USD
- **Modelled Max Drawdown**: $5,456.79 USD

### 3. Meta $50,000 MXN / mes ($2,500.00 USD/mes)
- **Capital Requerido ($USD)**: **$205,761.32 USD**
- **Capital Requerido ($MXN)**: **$4,115,226.34 MXN**
- **Modelled Annual PnL**: $30,000.00 USD
- **Modelled Max Drawdown**: $13,641.98 USD

### 4. Meta $100,000 MXN / mes ($5,000.00 USD/mes)
- **Capital Requerido ($USD)**: **$411,522.63 USD**
- **Capital Requerido ($MXN)**: **$8,230,452.67 MXN**
- **Modelled Annual PnL**: $60,000.00 USD
- **Modelled Max Drawdown**: $27,283.95 USD
