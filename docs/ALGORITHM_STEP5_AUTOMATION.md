# Algoritmo de 5 Pasos — Paso 5: Automatización (Automate)

> **"El paso final es automatizar. Solo automatiza después de haber cuestionado los requisitos, eliminado las partes innecesarias, simplificado y acelerado el ciclo."** — Elon Musk

Este documento define las tareas repetitivas y verificadas que han sido automatizadas en el sistema Automaton, así como la delimitación estricta de decisiones críticas que **NUNCA** deben ser automatizadas.

---

## 1. Procesos Automatizados en Automaton

| Proceso Automatizado | Módulo Responsable | Descripción de la Automatización | Frecuencia / Trigger |
| :--- | :--- | :--- | :--- |
| **1. Memory Preflight** | `src/memory/preflight.py` | Consulta automática de memoria a largo plazo antes de generar variantes. Bloquea si la hipótesis fue previamente `REJECTED`. | Antes de cada batch de generación. |
| **2. Ingesta de Memoria** | `src/memory/ingest_research.py` | Extracción y persistencia automática de métricas atómicas L1 y escenas L2 en `automaton_memory.db`. | Tras finalizar autopsia de un batch. |
| **3. Paper Gate Monitoring** | `src/execution/paper_gate_monitor.py` | Cálculo automático de progreso hacia 100 trades, win rate, PF, DD, solapamiento y banderas de anomalía. | Condicional ante eventos o bajo demanda. |
| **4. Watchdog de Datos Obsoletos** | `pairs_trading_paper_runner.py` | Detención automática de nuevas aperturas si la latencia del mercado supera los $30\text{ minutos}$. | Cada ciclo de evaluación 1H. |
| **5. Reconciliación de Estado** | `src/execution/reconciliation.py` | Comparación automática de posiciones y órdenes locales vs broker tras cada orden enviada o cerrada. | Tras cada ejecución. |
| **6. Kill Switch Automático** | `src/execution/kill_switch.py` | Disparo automático del circuito de corte y cancelación de órdenes ante descuadres, pérdida diaria $\le -\$50$ o DD $\ge 10\%$. | Continuo. |
| **7. Persistencia y Recuperación** | `pairs_trading_paper_runner.py` | Guardado automático del estado de posiciones en `open_positions_state.json` y restauración tras reinicios. | Al abrir o cerrar posiciones. |

---

## 2. Límites Innegociables: Lo que NUNCA se Automatiza

Queda **estrictamente prohibido** automatizar las siguientes acciones bajo cualquier circunstancia:

1. ❌ **Escribir `APPROVED`**: La autorización de estrategias para Binance Demo o Real requiere **aprobación humana explícita y manual**.
2. ❌ **Promoción a REAL**: El paso de Paper a Demo/Real requiere el cumplimiento incondicional del Paper Gate ($\ge 100\text{ trades}$) y revisión manual de bitácora.
3. ❌ **Relajación de Filtros o Killer**: Ningún script puede relajar los umbrales de supervivencia ($PF > 1.30$, $DD < 12\%$, $Trades \ge 100$).
4. ❌ **Modificación de Parámetros de Estrategia**: Queda prohibido modificar hiperparámetros en caliente para forzar mayor frecuencia de trades.
5. ❌ **Descarga Indiscriminada de Datos**: Solo se descargan datasets históricos oficiales cuando una investigación formal lo justifique y esté previamente autorizada.
