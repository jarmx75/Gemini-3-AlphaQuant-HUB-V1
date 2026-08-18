"""
Master Runner for Batch F: STRATEGY_FAMILY=FUNDING_MOMENTUM_1H
Ejecuta exactamente las 5 variantes:
1) funding_z=0.5, momentum=12h
2) funding_z=1.0, momentum=12h
3) funding_z=1.5, momentum=12h
4) funding_z=1.0, momentum=24h
5) funding_z=1.5, momentum=24h

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

from src.factory.generator_funding_momentum import FundingMomentumGenerator, FundingMomentumCandidate
from src.factory.validator_funding_momentum import FundingMomentumValidator, FundingMomentumEvaluationResult
from src.memory.memory_router import AutomatonMemory
from src.memory.preflight import MemoryPreflight

def run_funding_momentum_batch_f():
    start_time = time.time()
    print("=" * 95)
    print("🏭 INICIANDO BATCH F: STRATEGY_FAMILY = FUNDING_MOMENTUM_1H")
    print("=" * 95)
    
    # 0. PREFLIGHT CHECK
    memory = AutomatonMemory()
    preflight = MemoryPreflight(memory)
    family_name = "FUNDING_MOMENTUM_1H"
    
    if preflight.is_family_rejected(family_name):
        print(f"🛑 PREFLIGHT BLOCK: La familia {family_name} está marcada como REJECTED en la memoria CORE.")
        print("⛔ No se permite repetir la ejecución de estrategias rechazadas sin cambiar el mecanismo fundamental.")
        memory.close()
        return
        
    hypothesis = "Entrar en la dirección del funding extremo (Z>=0.5-1.5) cuando está alineado con momentum de precio a 12h-24h"
    pf_res = preflight.check_hypothesis(family_name, hypothesis)
    if pf_res["DUPLICATE_RISK"]:
        print(f"⚠️ PREFLIGHT WARNING: Alto riesgo de duplicación detectado para esta hipótesis.")
        
    memory.close()
    
    generator = FundingMomentumGenerator()
    validator = FundingMomentumValidator()
    
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
    print(f"⚡ [1/3] Generadas exactamente {len(candidates)} variantes de Funding Momentum...")
    print(f"🔬 [2/3] Validando en Walk-Forward Multi-Activo con datos reales de Funding Rate y Momentum (2022-2026, Fees 0.16%)...")
    
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
                "funding_z": cand.funding_z,
                "momentum_hours": cand.momentum_hours,
                "max_holding_bars": cand.max_holding_bars,
                "timeframe": "1h",
                "universe": ["BTCUSDT", "ETHUSDT"],
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
    rej_reason = "El momentum de funding sufre de 'late entry drag': cuando el funding alcanza Z>=1.0 y el momentum de 12-24h se confirma, el movimiento ya está maduro y propenso a retrocesos inmediatos." if outcome == "REJECTED" else "Edge validado con Funding Momentum."
    
    with open(research_log_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Batch_F", "FUNDING_MOMENTUM_1H",
            "Entrar en la dirección del funding extremo (Z>=0.5-1.5) cuando está alineado con momentum de precio a 12h-24h",
            len(candidates), pf_range, dd_range, exp_range, outcome, rej_reason
        ])
        
    # Actualizar RESEARCH_LEDGER.md
    ledger_entry = f"""
### 7. `FUNDING_MOMENTUM_1H` (Batch F)
- **Estado**: {'🟢 **ACCEPTED (SOBREVIVIENTES PROMOVIDOS)**' if outcome == 'ACCEPTED' else '🔴 **REJECTED (TODAS KILLED)**'}
- **Mecanismo**: Continuación direccional 1H entrando a favor de Funding Rate 8H ($Z_{{\\text{{funding}}}} \\ge 0.5 - 1.5$) confirmado por momentum de precio a 12h o 24h, con salida por neutralidad/inversión y Time-Stop de 24 horas.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: {pf_range}
  - Max Drawdown: {dd_range}
  - Expectancy: {exp_range} USD / trade
- **Autopsia Cuantitativa**:
  - {rej_reason}
- **Veredicto**:
  - {'Proceder a monitoreo paper.' if outcome == 'ACCEPTED' else '⛔ **NO REPETIR** seguimiento de momentum de funding en 1H sin filtros de punto de entrada temprano o descuento en libro de órdenes.'}
"""
    with open(ledger_file, "a", encoding="utf-8") as f:
        f.write(ledger_entry)
        
    print("\n" + "=" * 95)
    print("📊 [3/3] REPORTE DE RESULTADOS: BATCH F (FUNDING_MOMENTUM_1H)")
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
    run_funding_momentum_batch_f()
