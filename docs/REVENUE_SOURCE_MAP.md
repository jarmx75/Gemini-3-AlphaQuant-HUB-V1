# Revenue Source Map (Track B — Non-Trading & Trading Revenue Engine)

**Fecha de Publicación**: 2026-08-21  
**Estado**: ACTIVE / VERIFIED CATALOG  
**Log JSON Maestro**: `logs/portfolio/revenue_opportunity_catalog.json`  

---

## 1. Visión General del Motor de Oportunidades No-Trading

Automaton opera con dos tracks paralelos de generación de valor:
- **TRACK A (Trading Alpha)**: Gestión cuantitativa de capital de portafolio descorrelacionado.
- **TRACK B (Non-Trading Revenue)**: Monetización directa de servicios, micro-SaaS, feeds de datos y APIs de inteligencia cuantitativa sin riesgo de mercado.

---

## 2. Taxonomía de las 8 Familias de Ingresos

1. **`AI_QUANT_SERVICES`**: Auditoría cuantitativa autónoma, verificación de backtests y reportes de sesgo.
2. **`MICRO_SAAS`**: Herramientas de software especializadas (ej. Cointegration Radar, Volatility Parity Dashboard).
3. **`DATA_PRODUCTS`**: Feeds de datos estructurados (ej. Alertas SEC Form 4 Insider Clusters, Inverse Vol Parity Weights).
4. **`API_PRODUCTS`**: REST API endpoints de verificación de sobreajuste y halteo de riesgo por tiempo de ejecución.
5. **`AUTOMATION_AS_A_SERVICE`**: Despliegue de runners de trading automatizados y watchdog cloud.
6. **`RESEARCH_INFORMATION_PRODUCTS`**: Publicaciones cuantitativas pagadas, análisis de factores y autopsias empíricas.
7. **`LEAD_GENERATION`**: Portal de comparación y recomendación de brokers y plataformas de trading.
8. **`TRADING_ALPHA`**: Retornos netos de mercado generados por el portafolio combinado.

---

## 3. Las TOP 3 Oportunidades Seleccionadas por EOS

$$\text{EOS} = \frac{\text{EconomicValue} \times \text{Evidence} \times \text{Automation} \times \text{Recurrence} \times \text{Speed} \times \text{CapitalEfficiency} \times \text{Feasibility} \times \text{StrategicFit}}{\text{Risk} \times \text{DistributionDifficulty} \times \text{RegulatoryBurden} \times \text{TimeToRevenue}}$$

### 🥇 #1. `OPP_01_QUANT_AUDIT_SAAS` (AI_QUANT_SERVICES)
- **EOS Score**: **25.92**
- **Problema**: Traders independientes y fondos pequeños carecen de herramientas automatizadas para auditar sesgos de lookahead y sobreajuste.
- **Solución**: Generador Micro-SaaS de Certificados de Auditoría Cuantitativa y Verificación de Backtest.
- **Monetización**: $49.00 USD por reporte de auditoría / $199/mes suscripción.
- **Tiempo a MVP**: 1 día (Construido en `src/economics/mvp_quant_audit_service.py`).
- **Tiempo a Primer Revenue**: 3 días.
- **Cliente Objetivo**: Traders algorítmicos independientes, prop traders y gestores cuantitativos.
- **Principal Riesgo**: Baja conversión en la capa gratuita.
- **Evidencia Faltante**: Tasa de conversión real de aterrizaje de usuarios piloto.

---

### 🥈 #2. `OPP_04_SEC_INSIDER_ALERT_FEED` (DATA_PRODUCTS)
- **EOS Score**: **21.60**
- **Problema**: Inversionistas swing se pierden las señales de compra de insiders Form 4 hasta que la acción ya ha subido un 10%.
- **Solución**: Canal de Alerta Telegram/Email en Tiempo Real de Compras en Mercado Abierto de Múltiples Insiders.
- **Monetización**: $39.00 USD / mes.
- **Tiempo a MVP**: 1 día.
- **Tiempo a Primer Revenue**: 3 días.
- **Cliente Objetivo**: Swing traders de acciones de EEUU e inversionistas de valor.
- **Principal Riesgo**: Fatiga de notificaciones en días de alto volumen de filings.
- **Evidencia Faltante**: Tasa de apertura de mensajes en prueba piloto.

---

### 🥉 #3. `OPP_03_COINTEGRATION_SCANNER_SAAS` (MICRO_SAAS)
- **EOS Score**: **18.23**
- **Problema**: Traders de arbitraje estadístico gastan horas escaneando manualmente valores $p$ de ADF y estabilidad de betas OLS.
- **Solución**: Dashboard Cointegration Radar de escaneo diario sobre 500+ pares sin lookahead.
- **Monetización**: $79.00 USD / mes.
- **Tiempo a MVP**: 2 días.
- **Tiempo a Primer Revenue**: 4 días.
- **Cliente Objetivo**: Traders de Pairs Trading Crypto y Equities.
- **Principal Riesgo**: Competencia con scripts de código abierto en Python.
- **Evidencia Faltante**: Disposición a pagar por interfaz gráfica en lugar de código propio.
