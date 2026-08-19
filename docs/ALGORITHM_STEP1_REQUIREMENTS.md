# Algoritmo de 5 Pasos — Paso 1: Cuestionar Requisitos (Question Requirements)

> **"El primer paso es hacer que tus requerimientos sean menos tontos. Los requerimientos de todos son tontos hasta cierto punto, no importa cuán inteligentes sean. Especialmente los que provienen de personas inteligentes, porque nadie los cuestiona."** — Elon Musk

Este documento audita exhaustivamente cada requisito, proceso, archivo y mecanismo del proyecto Automaton, evaluando su justificación, costo operativo y necesidad estricta para **SECURITY**, **RESEARCH**, **PAPER**, **DEMO** y **REAL**.

---

## 1. Matriz de Auditoría de Requisitos del Sistema

| # | Requisito / Componente | Origen | Justificación / Evidencia | Costo Operativo / Tokens | ¿Es Esencial? (Área) | Veredicto Paso 1 |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **`PAPER_GATE = 100` trades cerrados** | Regla de supervivencia humana | El Teorema del Límite Central y la estimación robusta de Profit Factor en series temporales financieras con colas pesadas requieren $N \ge 100$ trades para reducir el error estándar del PF a $< \pm 0.15$. Evita promover sobreajustes (p-hacking) a cuentas con dinero real o demo. | Bajo en forward pasivo; alto en tiempo cronológico (~10 meses a ~9.7 trades/mes). | **SECURITY / DEMO / REAL** | **KEEP (Innegociable para seguridad)** |
| **2** | **3 Estrategias `PAPER_ACTIVE` concurrentes** | Mutaciones Batch 2 de Pairs Stat Arb | `Pairs_Stat_Arb_Base` y `Pairs_W90_Z2.5_S3.5_H24` tienen exactamente los mismos parámetros ($W=90, Z=2.5, S=3.5, H=24$). `Pairs_W90_Z2.4_S3.5_H24` tiene $Z=2.4$ (95% overlap). | Multiplica por 3x la evaluación de velas (9 evaluaciones por hora) y genera solapamiento casi total. | **RESEARCH / PAPER** | **KEEP en registro; DOCUMENTAR que económicamente son 1 sola estrategia con 2 variantes de vecindario** |
| **3** | **8 Loops y 8 Validadores separados en `src/factory/`** | Crecimiento incremental por cada batch (A a G) | Cada batch (Trend, Momentum, Volatility, Shock, Derivatives, Funding, Funding Momentum, Basis) copió y pegó un nuevo `loop_*.py` y `validator_*.py`. | Alto costo de mantenimiento (33 archivos en `src/factory/`), fragmentación y consumo de contexto en agentes. | **RESEARCH (Histórico)** | **TRIM / UNIFY: La evidencia ya está en `research_log.csv` y `RESEARCH_LEDGER.md`. Unificar el motor de generación para futuros batches.** |
| **4** | **`src/killer_framework/`** | Precursor legacy del Batch 1 | Código duplicado de `generator.py`, `killer.py`, `validator.py` previo a la creación de `src/factory/`. | Código muerto, riesgo de importaciones cruzadas obsoletas. | **NINGUNO (Obsoleto)** | **DELETE** |
| **5** | **Directorio raíz `factory/` (`factory/loop.py`)** | Wrapper temporal de 10 líneas | Redundancia pura que solo importa `src.factory.loop`. | Innecesario, confunde la estructura raíz. | **NINGUNO** | **DELETE** |
| **6** | **Módulos Legacy IQ Option (`iqoption_*.py`, `scratch/test_iq_*.py`)** | Fase inicial previa de opciones binarias | Automaton migró completamente a Binance Crypto Futures Stat Arb. IQ Option está 100% abandonado. | Ruido en el árbol de archivos, dependencias muertas. | **NINGUNO** | **DELETE** |
| **7** | **Runners Legacy descontinuados (`multi_asset_portfolio_runner.py`, `live_demo_runner.py`, `pairs_trading_live_runner.py`, `smart_portfolio_matrix.py`)** | Prototipos anteriores a la arquitectura modular v2 | Reemplazados por `pairs_trading_paper_runner.py` y `binance_client.py` + `order_manager.py`. | Riesgo de ejecución accidental de runners no sincronizados. | **NINGUNO** | **DELETE** |
| **8** | **Sistema de Memoria L0-L3 (`automaton_memory.db` + `preflight.py`)** | Hardening del Factory Loop | Evita repetir hipótesis rechazadas (`REJECTED`) en nuevos batches mediante consultas SQLite indexadas. | Muy bajo ($< 1\text{ms}$ por preflight). | **RESEARCH / MEMORY** | **KEEP (Protección obligatoria contra duplicación)** |
| **9** | **`RESEARCH_LEDGER.md`, `research_log.csv`, `dead_log.csv`** | Registro inmutable de hipótesis | Trazabilidad forense de cada batch, commit, variante y causa de muerte. | Cero costo computacional; almacenamiento textual mínimo. | **RESEARCH / AUDIT** | **KEEP (Evidencia inmutable)** |
| **10** | **`demo_readiness.py` vs `paper_gate_monitor.py`** | Auditoría inicial de paper trading | `paper_gate_monitor.py` supersedió completamente las funciones de `demo_readiness.py` agregando overlap, banderas de anomalía y monitoreo integral. | Duplicación de lógica de cálculo de métricas paper. | **PAPER / DEMO** | **MERGE: `demo_readiness.py` debe delegar o integrarse en `paper_gate_monitor.py`.** |
| **11** | **`DryRunBroker` y `demo_dry_run.py`** | Ensayo de ejecución offline | Valida idempotencia, reintentos, reconciliación y manejo de fallos sin conectar a red ni arriesgar órdenes. | Cero costo de red, ejecución local de tests en $< 0.1\text{s}$. | **SECURITY / EXECUTION** | **KEEP** |
| **12** | **Scripts temporales en `scratch/`** | Debugging puntual de sesiones pasadas | Scripts como `test_iq_*.py`, `diagnostico_*.py`, `audit_30h.py` ya cumplieron su propósito. | Contaminación del directorio scratch. | **NINGUNO** | **DELETE scripts obsoletos; KEEP scripts de reconciliación forense.** |
| **13** | **Políticas de Seguridad (`APPROVED=false`, `DEMO_ORDERS=0`, `REAL_ORDERS=0`)** | Principio de Máxima Prudencia | Garantiza que ningún agente o script pueda emitir órdenes de capital real de forma inadvertida. | Cero costo operativo. | **SECURITY (Innegociable)** | **KEEP** |

---

## 2. Conclusiones del Cuestionamiento de Requisitos

1. **Requisitos Innegociables de Seguridad**:
   - `APPROVED=false`, `DEMO_ORDERS=0`, `REAL_ORDERS=0`.
   - `PAPER_GATE = 100 trades` (estadísticamente fundamentado para evitar falsos descubrimientos en live).
   - `MemoryPreflight` como barrera previa a cualquier nuevo batch.
2. **Requisitos y Componentes que Deben Eliminarse**:
   - `src/killer_framework/` (100% redundante con `src/factory/`).
   - `factory/` raíz (wrapper redundante).
   - Módulos y scripts legacy de IQ Option y runners multi-asset descontinuados.
   - Scripts de scratch obsoletos que ya no se usan.
3. **Requisitos que Deben Fusionarse / Simplificarse**:
   - Unificar `demo_readiness.py` dentro de `paper_gate_monitor.py`.
   - Documentar la equivalencia de portafolio entre `Base`, `Z2.5` y `Z2.4` para evitar asunciones erróneas de diversificación.
