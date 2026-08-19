# Algoritmo de 5 Pasos — Paso 3: Simplificación y Optimización (Simplify / Optimize)

> **"Simplifica y optimiza. El error más común es optimizar algo que no debería existir en primer lugar."** — Elon Musk

Tras eliminar los módulos redundantes y el código muerto en el Paso 2, este documento define la simplificación estructural de la arquitectura Automaton, garantizando una **única fuente de verdad por componente** y un flujo unidireccional estricto sin dependencias circulares.

---

## 1. Jerarquía de Arquitectura Unificada

```
DATA ──> STRATEGY ──> VALIDATOR ──> MEMORY ──> PAPER ──> RISK ──> EXECUTION
```

| Capa | Módulo Central / Única Fuente de Verdad | Responsabilidad Específica |
| :--- | :--- | :--- |
| **1. DATA** | `data/historical*/` | Datasets inmutables OHLCV y derivados (1H, 4H, Funding, Basis). |
| **2. STRATEGY** | `src/strategies/` | Modelos matemáticos puros sin lógica de broker ni red (`generate_pair_signal`). |
| **3. VALIDATOR** | `src/factory/validator.py` | Walk-forward train/test/val OOS riguroso y cálculo de métricas de supervivencia. |
| **4. MEMORY** | `src/memory/preflight.py` & `automaton_memory.db` | Barrera obligatoria contra duplicación de hipótesis `REJECTED` y registro inmutable L0-L3. |
| **5. PAPER** | `src/execution/pairs_trading_paper_runner.py` | Ejecución forward continua en tiempo real, persistencia de estado y watchdog de datos. |
| **6. MONITOR** | `src/execution/paper_gate_monitor.py` | Seguimiento del Paper Gate hacia 100 trades, solapamiento y banderas de anomalía. |
| **7. RISK** | `src/execution/risk_manager.py` | Control pre-trade (posición máxima, pérdida diaria, drawdown, cotizaciones obsoletas). |
| **8. EXECUTION** | `src/execution/binance_client.py` & `dry_run_broker.py` | Gestión de órdenes con idempotencia estricta por `clientOrderId` y reconciliación de estado. |

---

## 2. Simplificaciones Clave Implementadas

1. **Unificación de Modos de Ejecución**:
   - `ExecutionMode`: `PAPER` $\to$ `DRY_RUN` $\to$ `DEMO` $\to$ `REAL`.
   - Control de fallos estricto en [`src/execution/execution_config.py`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/src/execution/execution_config.py). `DRY_RUN` bloquea toda llamada a red.
2. **Unificación del Paper Gate**:
   - [`src/execution/paper_gate_monitor.py`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/src/execution/paper_gate_monitor.py) centraliza el cálculo de métricas, análisis de solapamiento y alertas operativas.
3. **Optimización de I/O en Paper Runner**:
   - El runner almacena el estado mínimo necesario (`open_positions_state.json`, `runner_health.json`) y actualiza el log persistente únicamente cuando ocurren eventos de entrada o salida.
4. **Aislamiento de Telemetría**:
   - Ensayos locales Dry-Run escriben exclusivamente a `logs/execution/dry_run/` en formato JSONL sin tocar los registros forward de `logs/paper/bitacora_pairs_trading_paper.csv`.
