import sys
import time
import json
import csv
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.factory.generator_basis import BasisGenerator
from src.factory.validator_basis import BasisValidator
from src.memory.preflight import enforce_preflight
from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType

def run_basis_batch_g():
    start_time = time.time()
    print("=" * 95)
    print("🏭 INICIANDO BATCH G: STRATEGY_FAMILY = BASIS_SPOT_PERP")
    print("=" * 95)
    
    # 0. PREFLIGHT CHECK
    family_name = "BASIS_SPOT_PERP"
    hypothesis = "Convergencia de Basis Spot vs Perpetual (Long barato, Short caro) para capturar delta-neutral reversion."
    
    if not enforce_preflight(family_name, hypothesis):
        return
        
    generator = BasisGenerator()
    validator = BasisValidator()
    
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
    print(f"⚡ [1/3] Generadas exactamente {len(candidates)} variantes de Basis Spot Perp...")
    print(f"🔬 [2/3] Validando en Walk-Forward Multi-Activo (2022-2026, Fees 0.16% + Funding)...")
    
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
                "entry_z": cand.entry_z,
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
    rej_reason = "El basis en mercados crypto modernos (2024+) se arbitra demasiado rápido y el costo de fees (0.16% roundtrip en dos patas) destruye el minúsculo yield antes de la reversión a la media." if outcome == "REJECTED" else "Edge delta-neutral validado absorbiendo ineficiencias transitorias entre spot y perpetuos."
    
    with open(research_log_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Batch_G", "BASIS_SPOT_PERP",
            "Convergencia de basis (Spot vs Perp) delta neutral con entry Z=1.0-3.0",
            len(candidates), pf_range, dd_range, exp_range, outcome, rej_reason
        ])
        
    # Actualizar RESEARCH_LEDGER.md
    ledger_entry = f"""
### 8. `BASIS_SPOT_PERP` (Batch G)
- **Estado**: {'🟢 **ACCEPTED (SOBREVIVIENTES PROMOVIDOS)**' if outcome == 'ACCEPTED' else '🔴 **REJECTED (TODAS KILLED)**'}
- **Mecanismo**: Posición delta-neutral. Si Z-Score del Basis (Perp - Spot) >= Umbral, Long Spot + Short Perp. Salida al cruzar media.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: {pf_range}
  - Max Drawdown: {dd_range}
  - Expectancy: {exp_range} USD / trade
- **Autopsia Cuantitativa**:
  - {rej_reason}
- **Veredicto**:
  - {'Proceder a monitoreo paper (Mínimo 100 trades de validación real-forward).' if outcome == 'ACCEPTED' else '⛔ **NO REPETIR** arbitraje estadístico de basis en timeframes intradiarios donde las comisiones conjuntas superan el spread.'}
"""
    with open(ledger_file, "a", encoding="utf-8") as f:
        f.write(ledger_entry)

    # Memoria Automaton (Ingesta al L0/L1)
    memory = AutomatonMemory()
    mem_id = memory.write(
        memory_type=MemoryType.ATOMIC,
        family=family_name,
        batch_id="Batch_G",
        claim_text=f"Batch G completado. Outcome: {outcome}. Reason: {rej_reason}",
        source_path="src/factory/loop_basis.py",
        source_commit="HEAD",
        tags=[family_name, "basis_convergence", "delta_neutral", f"{outcome}_CONSTRAINT"]
    )
    if outcome == "REJECTED":
        memory.write(
            memory_type=MemoryType.CORE,
            family=family_name,
            batch_id="Batch_G",
            claim_text=f"Rule: Family {family_name} is REJECTED.",
            source_path="src/factory/loop_basis.py",
            source_commit="HEAD",
            tags=["RULE", "REJECTED_CONSTRAINT"]
        )
    memory.close()
        
    print("\n" + "=" * 95)
    print("📊 [3/3] REPORTE DE RESULTADOS: BATCH G (BASIS_SPOT_PERP)")
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
    run_basis_batch_g()
