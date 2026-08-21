# Dataset Manifest: Futures Term Structure / Carry (Batch N)

**Fecha de Auditoría**: 2026-08-20  
**Familia de Investigación**: `FUTURES_TERM_STRUCTURE_CARRY`  
**Resultado de Feasibility (Fase 0)**: `DATASET_UNAVAILABLE`  

---

## 1. Cobertura Requerida vs Disponible por Mercado

| Mercado | Símbolo | Tipo | Vencimientos Requeridos | Disponibilidad Pública Gratuita | Estado de Feasibility |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **WTI Crude Oil** | `CL` | Commodity Futures | Near ($F_{\text{near}}$) y Far ($F_{\text{far}}$) | Solo Contrato Continuo (`CL=F`) | 🛑 `UNAVAILABLE` |
| **Gold** | `GC` | Commodity Futures | Near ($F_{\text{near}}$) y Far ($F_{\text{far}}$) | Solo Contrato Continuo (`GC=F`) | 🛑 `UNAVAILABLE` |
| **Copper** | `HG` | Commodity Futures | Near ($F_{\text{near}}$) y Far ($F_{\text{far}}$) | Solo Contrato Continuo (`HG=F`) | 🛑 `UNAVAILABLE` |
| **Corn** | `ZC` | Commodity Futures | Near ($F_{\text{near}}$) y Far ($F_{\text{far}}$) | Solo Contrato Continuo (`ZC=F`) | 🛑 `UNAVAILABLE` |
| **EUR/USD Futures** | `6E` | FX Futures | Near ($F_{\text{near}}$) y Far ($F_{\text{far}}$) | Solo Contrato Continuo (`6E=F`) | 🛑 `UNAVAILABLE` |

---

## 2. Hallazgos y Restricciones Técnicas

1. **Ausencia de Vencimientos Simultáneos**:
   - Las fuentes de datos públicas y gratuitas (Yahoo Finance / `yfinance`, FRED, etc.) únicamente suministran series sintéticas de contrato continuo único (`CL=F`, `GC=F`, etc.).
   - Los contratos individuales deslistados (ej. `CLU24.NYM`, `CLZ24.NYM`) retornan `HTTP 404 Not Found` en feeds públicos.
2. **Imposibilidad de Construir Curva Explícita Sin Look-Ahead**:
   - Para calcular la curva de carry real $\text{carry} = \frac{F_{\text{near}} - F_{\text{far}}}{F_{\text{near}}}$ y el carry anualizado con días exactos hasta vencimiento, se requieren los precios de liquidación diarios de al menos 2 contratos activos en la misma fecha $t$.
   - **Regla Estricta**: No se permite aproximar el contrato $F_{\text{far}}$ utilizando la serie continua ni fabricar/inventar curvas sintéticas.
3. **Acceso Comercial Requerido**:
   - La obtención de datos históricos de vencimientos individuales para futuros de materias primas y divisas requiere suscripción comercial a CME DataMine, Refinitiv Tick History o Databento.

---

## 3. Veredicto Final

Batch N queda suspendido y registrado como **`REJECTED`** por `DATASET_UNAVAILABLE`.  
Ninguna estrategia fue ejecutada ni optimizada. No se modificaron parámetros ni estrategias activas en paper trading.
