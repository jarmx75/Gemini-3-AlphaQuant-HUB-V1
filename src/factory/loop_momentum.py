"""
Master Runner for Batch B: STRATEGY_FAMILY=CROSS_SECTIONAL_MOMENTUM_4H
Ejecuta exactamente las 5 variantes:
1) N=6  (24h momentum)
2) N=12 (48h momentum)
3) N=24 (4 días momentum)
4) N=48 (8 días momentum)
5) N=72 (12 días momentum)

Reglas:
- 100% Paper Mode.
- NO modifica 'APPROVED' ni sobreescribe candidatos existentes en registry.json.
- Registra autopsias en dead_log.csv para las reprobadas.
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

from src.factory.generator_momentum import MomentumGenerator, MomentumCandidate
from src.factory.validator_momentum import MomentumValidator, MomentumEvaluationResult

def run_momentum_batch_b():
    start_time = time.time()
    print("=" * 95)
    print("🏭 INICIANDO BATCH B: STRATEGY_FAMILY = CROSS_SECTIONAL_MOMENTUM_4H")
    print("=" * 95)
    
    generator = MomentumGenerator()
    validator = MomentumValidator()
    
    factory_dir = Path("src/factory")
    live_dir = Path("src/strategies/live_candidates")
    registry_file = factory_dir / "registry.json"
    dead_log_file = factory_dir / "dead_log.csv"
    
    factory_dir.mkdir(parents=True, exist_ok=True)
    live_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar registry existente para NO alterar nada previo
    if registry_file.exists():
        with open(registry_file, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
    else:
        registry_data = {"active_paper_strategies": [], "human_approved_real_strategies": []}
        
    candidates = generator.generate_batch()
    print(f"⚡ [1/3] Generadas exactamente {len(candidates)} variantes de Cross-Sectional Momentum 4H...")
    print(f"🔬 [2/3] Validando en Walk-Forward Multi-Activo (2022-2026, Fees 0.16%)...")
    
    results = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for cand in candidates:
        res = validator.validate_candidate(cand)
        
        if res.passed:
            cand_config = {
                "id": cand.id,
                "family": cand.family,
                "n_lookback": cand.n_lookback,
                "timeframe": "4h",
                "universe": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"],
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
            
            # Guardar JSON de configuración
            cand_file = live_dir / f"{cand.id}.json"
            with open(cand_file, "w", encoding="utf-8") as f:
                json.dump(cand_config, f, indent=2)
                
            # Actualizar registry sin duplicar
            registry_data["active_paper_strategies"] = [
                s for s in registry_data.get("active_paper_strategies", []) if s.get("id") != cand.id
            ]
            registry_data["active_paper_strategies"].append(cand_config)
            status_text = "🟢 PAPER_ACTIVE"
        else:
            # Registrar en dead_log.csv
            with open(dead_log_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now_str, cand.id, f"{res.train_pf:.2f}", f"{res.test_pf:.2f}",
                    f"{res.val_pf:.2f}", res.val_trades, f"{res.val_max_dd_pct:.1f}", res.verdict
                ])
                
            # Eliminar archivo si existía previamente
            cand_file = live_dir / f"{cand.id}.json"
            if cand_file.exists():
                cand_file.unlink()
                
            status_text = f"🔴 KILLED ({res.verdict})"
            
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
        
    print("\n" + "=" * 95)
    print("📊 [3/3] REPORTE DE RESULTADOS: BATCH B (CROSS_SECTIONAL_MOMENTUM_4H)")
    print("=" * 95)
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    
    elapsed = time.time() - start_time
    print("-" * 95)
    print(f"⏱️ Tiempo total de validación: {elapsed:.2f} segundos | Modo: PAPER EXCLUSIVO")
    print(f"📁 Registro actualizado: {registry_file}")
    print(f"📁 Autopsias registradas: {dead_log_file}")
    print("=" * 95 + "\n")

if __name__ == '__main__':
    run_momentum_batch_b()
