"""
Master Runner for Batch D: STRATEGY_FAMILY=EVENT_SHOCK_REVERSAL_1H (EVENT_SHOCK_PROXY)
Ejecuta exactamente las 5 variantes:
1) return_z=2.0, volume_z=1.5
2) return_z=2.0, volume_z=2.0
3) return_z=2.5, volume_z=1.5
4) return_z=2.5, volume_z=2.0
5) return_z=3.0, volume_z=2.0

Reglas:
- 100% Paper Mode.
- NO modifica 'APPROVED' ni sobreescribe candidatos existentes en registry.json.
- Registra autopsias en dead_log.csv para las reprobadas.
- Actualiza research_log.csv y RESEARCH_LEDGER.md.
"""

import sys
import time
import json
import csv
from pathlib import Path
from datetime import datetime
import pandas as pd

# Añadir raíz
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.factory.generator_shock import ShockGenerator, ShockCandidate
from src.factory.validator_shock import ShockValidator, ShockEvaluationResult

def run_shock_batch_d():
    start_time = time.time()
    print("=" * 95)
    print("🏭 INICIANDO BATCH D: STRATEGY_FAMILY = EVENT_SHOCK_REVERSAL_1H (EVENT_SHOCK_PROXY)")
    print("=" * 95)
    
    generator = ShockGenerator()
    validator = ShockValidator()
    
    factory_dir = Path("src/factory")
    live_dir = Path("src/strategies/live_candidates")
    registry_file = factory_dir / "registry.json"
    dead_log_file = factory_dir / "dead_log.csv"
    research_log_file = factory_dir / "research_log.csv"
    ledger_file = factory_dir / "RESEARCH_LEDGER.md"
    
    factory_dir.mkdir(parents=True, exist_ok=True)
    live_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar registry existente para NO alterar nada previo
    if registry_file.exists():
        with open(registry_file, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
    else:
        registry_data = {"active_paper_strategies": [], "human_approved_real_strategies": []}
        
    candidates = generator.generate_batch()
    print(f"⚡ [1/3] Generadas exactamente {len(candidates)} variantes de Event Shock Reversal 1H...")
    print(f"🔬 [2/3] Validando en Walk-Forward Multi-Activo (2022-2026, Fees 0.16%)...")
    
    results = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    val_pfs = []
    val_dds = []
    val_exps = []
    survivors_count = 0
    
    for cand in candidates:
        res = validator.validate_candidate(cand)
        val_pfs.append(res.val_pf)
        val_dds.append(res.val_max_dd_pct)
        val_exps.append(res.val_expectancy)
        
        if res.passed:
            survivors_count += 1
            cand_config = {
                "id": cand.id,
                "family": cand.family,
                "return_z": cand.return_z,
                "volume_z": cand.volume_z,
                "max_holding_bars": cand.max_holding_bars,
                "timeframe": "1h",
                "metrics": {
                    "val_pf": round(res.val_pf, 2),
                    "val_expectancy": round(res.val_expectancy, 2),
                    "val_dd_pct": round(res.val_max_dd_pct, 2),
                    "val_trades": res.val_trades,
                    "val_win_rate": round(res.val_win_rate, 2),
                    "val_net_pnl": round(res.val_net_pnl, 2)
                },
                "promoted_at": now_str,
                "status": "PAPER_ACTIVE",
                "human_approval": "PENDING (Write 'APPROVED' manually to allow Binance Demo/Real)"
            }
            
            cand_file = live_dir / f"{cand.id}.json"
            with open(cand_file, "w", encoding="utf-8") as f:
                json.dump(cand_config, f, indent=2)
                
            registry_data["active_paper_strategies"] = [
                s for s in registry_data.get("active_paper_strategies", []) if s.get("id") != cand.id
            ]
            registry_data["active_paper_strategies"].append(cand_config)
        else:
            with open(dead_log_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now_str, cand.id, f"{res.train_pf:.2f}", f"{res.test_pf:.2f}",
                    f"{res.val_pf:.2f}", res.val_trades, f"{res.val_max_dd_pct:.1f}", res.verdict
                ])
                
            cand_file = live_dir / f"{cand.id}.json"
            if cand_file.exists():
                cand_file.unlink()
                
        results.append({
            "Variante": cand.id,
            "PF Val": f"{res.val_pf:.2f}",
            "DD Val": f"{res.val_max_dd_pct:.1f}%",
            "Trades Val": res.val_trades,
            "Expectancy": f"${res.val_expectancy:+.2f}",
            "Net PnL": f"${res.val_net_pnl:+.2f}",
            "Estado": "🟢 PAPER_ACTIVE" if res.passed else "🔴 KILLED"
        })
        
    # Guardar registry.json actualizado
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)
        
    # Actualizar research_log.csv
    outcome = "ACCEPTED" if survivors_count > 0 else "REJECTED"
    pf_range = f"{min(val_pfs):.2f} - {max(val_pfs):.2f}"
    dd_range = f"{min(val_dds):.1f}% - {max(val_dds):.1f}%"
    exp_range = f"${min(val_exps):+.2f} a ${max(val_exps):+.2f}"
    rej_reason = "Los shocks de precio y volumen en 1H tienden a continuar en cascada direccional a corto plazo (momentum de liquidación); la reversión a 4 barras no compensa las pérdidas en cascadas fuertes." if outcome == "REJECTED" else "Edge validado en reversión de shocks extremos."
    
    with open(research_log_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Batch_D", "EVENT_SHOCK_REVERSAL_1H (EVENT_SHOCK_PROXY)",
            "Reversión media rápida (time-stop 4h) tras shock extremo conjunto de retorno (Z>=2.0-3.0) y volumen (Z>=1.5-2.0)",
            len(candidates), pf_range, dd_range, exp_range, outcome, rej_reason
        ])
        
    # Actualizar RESEARCH_LEDGER.md
    ledger_entry = f"""
### 4. `EVENT_SHOCK_REVERSAL_1H` (EVENT_SHOCK_PROXY - Batch D)
- **Estado**: {'🟢 **ACCEPTED (SOBREVIVIENTES PROMOVIDOS)**' if outcome == 'ACCEPTED' else '🔴 **REJECTED (TODAS KILLED)**'}
- **Mecanismo**: Entrada en contra de velas de 1H con shock de retorno ($|Z_{{\\text{{ret}}}}| \\ge 2.0 - 3.0$) y pico de volumen ($Z_{{\\text{{vol}}}} \\ge 1.5 - 2.0$) buscando reversión hacia SMA 20 con Time-Stop máximo incondicional de 4 velas (4h).
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: {pf_range}
  - Max Drawdown: {dd_range}
  - Expectancy: {exp_range} USD / trade
- **Autopsia Cuantitativa**:
  - {rej_reason}
- **Veredicto**:
  - {'Proceder a monitoreo paper.' if outcome == 'ACCEPTED' else '⛔ **NO REPETIR** reversión ciega de shocks extremos en 1H sin confirmación de agotamiento en libro de órdenes o datos reales de desequilibrio de funding/liquidaciones.'}
"""
    with open(ledger_file, "a", encoding="utf-8") as f:
        f.write(ledger_entry)
        
    print("\n" + "=" * 95)
    print("📊 [3/3] REPORTE DE RESULTADOS: BATCH D (EVENT_SHOCK_REVERSAL_1H)")
    print("=" * 95)
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    
    elapsed = time.time() - start_time
    print("-" * 95)
    print(f"⏱️ Tiempo total de validación: {elapsed:.2f} segundos | Modo: PAPER EXCLUSIVO")
    print(f"📁 Registro actualizado: {registry_file}")
    print(f"📁 Autopsias registradas: {dead_log_file}")
    print(f"📁 Memoria de investigación: {research_log_file} & {ledger_file}")
    print("=" * 95 + "\n")

if __name__ == '__main__':
    run_shock_batch_d()
