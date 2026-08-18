"""
Factory Master Loop (1 Batch Execution)
Ejecuta exactamente 1 ciclo token-light:
1. Generate 5 variantes sistemáticas.
2. Validate 5 sobre datos multi-año en RAM.
3. Promote / Kill y actualiza registry.json / dead_log.csv.
4. Renderiza tabla resumen concisa.
"""

import sys
import time
from pathlib import Path
import pandas as pd

# Añadir raíz
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.factory.generator import FactoryGenerator
from src.factory.validator import FactoryValidator
from src.factory.killer import FactoryKiller
from src.memory.preflight import enforce_preflight

def run_factory_cycle(batch_size: int = 5):
    start_time = time.time()
    print("=" * 85)
    print("🏭 INICIANDO CICLO DE FÁBRICA AUTÓNOMA (AUTOMATON FACTORY - TOKEN OPTIMIZED)")
    print("=" * 85)
    
    # 0. PREFLIGHT CHECK
    family_name = "MEAN_REVERSION_1H"
    hypothesis = "Pairs trading estático con Z-score clásico de spread usando rolling window (z_entry=2, z_exit=0)"
    if not enforce_preflight(family_name, hypothesis):
        return
        
    generator = FactoryGenerator()
    validator = FactoryValidator()
    killer = FactoryKiller()
    
    print(f"⚡ [1/3] Generando {batch_size} variantes sistemáticas de Pairs Trading...")
    candidates = generator.generate_batch(batch_size=batch_size)
    
    results = []
    print(f"🔬 [2/3] Validando {len(candidates)} variantes en Walk-Forward (2022-2026)...")
    for cand in candidates:
        res = validator.validate_candidate(cand)
        action_data = killer.process_result(cand, res)
        results.append({
            "Candidata": cand.id,
            "Train PF": f"{res.train_pf:.2f}",
            "Test PF": f"{res.test_pf:.2f}",
            "Val PF": f"{res.val_pf:.2f}",
            "Trades Val": res.val_trades,
            "Win Rate": f"{res.val_win_rate:.1f}%",
            "Max DD": f"{res.val_max_dd_pct:.1f}%",
            "Acción / Veredicto": "🟢 PROMOVED" if res.passed else f"🔴 {res.verdict}"
        })
        
    print("\n" + "=" * 85)
    print("📊 [3/3] RESULTADOS DEL LOTE DE FÁBRICA (BATCH 5)")
    print("=" * 85)
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    
    elapsed = time.time() - start_time
    print("-" * 85)
    print(f"⏱️ Tiempo total de ciclo: {elapsed:.2f} segundos | Modo: PAPER EXCLUSIVO")
    print("📁 Registro de Vivas: src/factory/registry.json")
    print("📁 Registro de Muertas: src/factory/dead_log.csv")
    print("=" * 85 + "\n")

if __name__ == '__main__':
    run_factory_cycle(batch_size=5)
