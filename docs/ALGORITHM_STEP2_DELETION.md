# Algoritmo de 5 Pasos — Paso 2: Eliminación (Delete)

> **"Si no terminas agregando de vuelta al menos el 10% de lo que eliminaste, significa que no estás eliminando suficiente."** — Elon Musk

Este documento detalla la clasificación formal **DELETE**, **KEEP**, **MERGE** y **TRIM** de todos los componentes del sistema Automaton, verificando referencias antes de proceder a la eliminación física de código redundante.

---

## 1. Inventario de Acciones por Componente

### 🔴 DELETE (Eliminación Definitiva)
Los siguientes archivos y directorios representan código muerto, wrappers vacíos o módulos legacy obsoletos:

1. **Directorio `src/killer_framework/`**:
   - `src/killer_framework/generator.py` (código legacy de Batch 1)
   - `src/killer_framework/killer.py` (código legacy de Batch 1)
   - `src/killer_framework/validator.py` (código legacy de Batch 1)
   - *Justificación*: Supersedido al 100% por `src/factory/`.
2. **Directorio raíz `factory/`**:
   - `factory/loop.py`
   - *Justificación*: Wrapper redundante de 10 líneas.
3. **Módulos de Ejecución Legacy y Deprecados en `src/execution/`**:
   - `src/execution/iqoption_binary_bot.py` (broker de opciones binarias abandonado)
   - `src/execution/iqoption_live_runner.py` (broker de opciones binarias abandonado)
   - `src/execution/live_demo_runner.py` (runner legacy descontinuado)
   - `src/execution/multi_asset_portfolio_runner.py` (prototipo legacy descontinuado)
   - `src/execution/pairs_trading_live_runner.py` (supersedido por `pairs_trading_paper_runner.py`)
   - `src/execution/smart_portfolio_matrix.py` (prototipo legacy descontinuado)
4. **Scripts Temporales Obsoletos en `scratch/`**:
   - `scratch/test_iq_candles.py`, `scratch/test_iq_connect.py`, `scratch/test_iq_http.py`, `scratch/test_iq_quick.py`, `scratch/test_iq_real_order.py`
   - `scratch/diagnostico_iq_senales.py`, `scratch/diagnostico_profundo.py`
   - `scratch/audit_30h.py`, `scratch/clean_all_positions.py`, `scratch/auditoria_forense_exhaustiva.py`, `scratch/parameter_sweep_edge.py`
5. **Scripts Legacy en `scripts/`**:
   - `scripts/ejecutar_killer_framework.py` (hacía referencia a `killer_framework`)
   - `scripts/analisis_multimotor_avanzado.py`
   - `scripts/resumen_ejecucion_real.py`

---

### 🟡 MERGE (Fusión y Unificación)
- **`src/execution/demo_readiness.py` $\to$ `src/execution/paper_gate_monitor.py`**:
  - `demo_readiness.py` se refactoriza como un wrapper ligero y de compatibilidad que delega directamente en `PaperGateMonitor` para mantener intactas las firmas de importación en los tests existentes sin duplicar lógica de cálculo de métricas.

---

### 🟢 KEEP (Conservación Inmutable)
Bajo ninguna circunstancia se eliminan los siguientes elementos:

1. **Evidencia Histórica y Registro de Investigación**:
   - `src/factory/registry.json`
   - `src/factory/RESEARCH_LEDGER.md`
   - `src/factory/research_log.csv`
   - `src/factory/dead_log.csv`
2. **Sistema de Memoria L0-L3**:
   - `src/memory/automaton_memory.db`
   - `src/memory/preflight.py`, `memory_store.py`, `ingest_research.py`, `schemas.py`, etc.
3. **Estrategia PAPER_ACTIVE y Modelos de Investigación**:
   - `src/strategies/pairs_trading_stat_arb.py`
   - Estrategias de referencia de familias investigadas (Donchian, Momentum, Shock, Funding, Basis).
4. **Pipeline Modular de Ejecución v2**:
   - `src/execution/pairs_trading_paper_runner.py`
   - `src/execution/paper_gate_monitor.py`
   - `src/execution/dry_run_broker.py`
   - `src/execution/demo_dry_run.py`
   - `src/execution/execution_config.py`
   - `src/execution/binance_client.py`
   - `src/execution/order_manager.py`
   - `src/execution/position_manager.py`
   - `src/execution/risk_manager.py`
   - `src/execution/reconciliation.py`
   - `src/execution/kill_switch.py`
5. **Suite de Tests**:
   - `tests/` (los 45 tests unitarios e integrados).
6. **Datos Históricos**:
   - `data/historical/`
   - `data/historical_derivatives/`
   - `data/historical_basis/`

---

## 2. Verificación de Dependencias Previas al Borrado

Antes de ejecutar las eliminaciones:
- Se comprobó que `src/killer_framework` no es utilizado por ningún componente activo.
- Se verificó que `demo_readiness.py` mantiene retrocompatibilidad con `test_paper_runner_integration.py` y `binance_demo_runner.py`.
- Se aseguró que ninguna estrategia activa (`Pairs_Stat_Arb_Base`, `Pairs_W90_Z2.5_S3.5_H24`, `Pairs_W90_Z2.4_S3.5_H24`) dependa de archivos marcados para eliminación.
