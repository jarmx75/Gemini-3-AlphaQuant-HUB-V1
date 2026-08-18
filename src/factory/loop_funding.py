"""
Master Runner for Batch E: STRATEGY_FAMILY=FUNDING_CONTRARIAN
Ejecuta exactamente las 5 variantes:
1) funding_z=1.5, price_extension=0.5 ATR
2) funding_z=2.0, price_extension=0.5 ATR
3) funding_z=2.5, price_extension=0.5 ATR
4) funding_z=2.0, price_extension=1.0 ATR
5) funding_z=2.5, price_extension=1.0 ATR

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

from src.factory.generator_funding import FundingGenerator, FundingCandidate
from src.factory.validator_funding import FundingValidator, FundingEvaluationResult
from src.memory.preflight import enforce_preflight

def run_funding_batch_e():
    start_time = time.time()
    print("=" * 95)
    print("🏭 INICIANDO BATCH E: STRATEGY_FAMILY = FUNDING_CONTRARIAN")
    print("=" * 95)
    
    # 0. PREFLIGHT CHECK
    family_name = "FUNDING_CONTRARIAN"
    hypothesis = "Funding rate extremo (Z>=1.5-2.5) y extensión de precio (0.5-1.0 ATR) señala posicionamiento saturado y precede reversión media"
    
    if not enforce_preflight(family_name, hypothesis):
        return
        
    generator = FundingGenerator()
    validator = FundingValidator()
    
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
    print(f"⚡ [1/3] Generadas exactamente {len(candidates)} variantes de Funding Contrarian...")
    print(f"🔬 [2/3] Validando en Walk-Forward Multi-Activo con datos reales de Funding Rate (2022-2026, Fees 0.16%)...")
    
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
                "price_extension_atr": cand.price_extension_atr,
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
        
    # Actualizar research_log.csv (reemplazando DATASET_UNAVAILABLE previo por resultados reales)
    outcome = "ACCEPTED" if survivors_count > 0 else "REJECTED"
    pf_range = f"{min(val_pfs):.2f} - {max(val_pfs):.2f}"
    dd_range = f"{min(val_dds):.1f}% - {max(val_dds):.1f}%"
    exp_range = f"${min(val_exps):+.2f} a ${max(val_exps):+.2f}"
    rej_reason = "El funding rate extremo actúa como señal de persistencia de régimen en lugar de agotamiento inmediato a 8h; los mercados pueden mantener funding extremo durante días en rallies y caídas fuertes." if outcome == "REJECTED" else "Edge validado con Funding Rate real."
    
    # Leer research_log.csv y actualizar Batch_E
    if research_log_file.exists():
        df_rlog = pd.read_csv(research_log_file)
        df_rlog = df_rlog[df_rlog['batch_id'] != 'Batch_E']
    else:
        df_rlog = pd.DataFrame(columns=['batch_id', 'family', 'hypothesis', 'variants_tested', 'val_pf_range', 'val_dd_range', 'val_exp_range', 'outcome', 'rejection_reason'])
        
    new_row = {
        'batch_id': 'Batch_E',
        'family': 'FUNDING_CONTRARIAN',
        'hypothesis': 'Funding rate extremo (Z>=1.5-2.5) y extensión de precio (0.5-1.0 ATR) señala posicionamiento saturado y precede reversión media',
        'variants_tested': len(candidates),
        'val_pf_range': pf_range,
        'val_dd_range': dd_range,
        'val_exp_range': exp_range,
        'outcome': outcome,
        'rejection_reason': rej_reason
    }
    df_rlog = pd.concat([df_rlog, pd.DataFrame([new_row])], ignore_index=True)
    df_rlog.to_csv(research_log_file, index=False)
        
    # Actualizar RESEARCH_LEDGER.md
    with open(ledger_file, "r", encoding="utf-8") as f:
        ledger_content = f.read()
        
    updated_section_5 = f"""### 5. `FUNDING_CONTRARIAN` (Batch E)
- **Estado**: {'🟢 **ACCEPTED (SOBREVIVIENTES PROMOVIDOS)**' if outcome == 'ACCEPTED' else '🔴 **REJECTED (TODAS KILLED)**'}
- **Mecanismo**: Reversión media 1H hacia SMA 20 tras publicación de Funding Rate 8H extremo ($Z_{{\\text{{funding}}}} \\ge 1.5 - 2.5$) y extensión de precio ($0.5 - 1.0 \\times \\text{{ATR}}$), con Time-Stop de 8 horas y Stop de emergencia del 3.0%.
- **Rango de Resultados Out-of-Sample (2024 - 2026)**:
  - Profit Factor: {pf_range}
  - Max Drawdown: {dd_range}
  - Expectancy: {exp_range} USD / trade
- **Autopsia Cuantitativa**:
  - {rej_reason}
- **Veredicto**:
  - {'Proceder a monitoreo paper.' if outcome == 'ACCEPTED' else '⛔ **NO REPETIR** reversión ciega de funding rates extremos en 8H sin filtros de agotamiento de volumen o ruptura de estructura de tendencia.'}
"""
    # Reemplazar la sección 5
    if "### 5. `FUNDING_CONTRARIAN`" in ledger_content:
        parts = ledger_content.split("### 5. `FUNDING_CONTRARIAN`")
        header_and_before = parts[0]
        after_parts = parts[1].split("### 6.")
        remaining = "\n### 6." + after_parts[1] if len(after_parts) > 1 else ""
        ledger_content = header_and_before + updated_section_5 + remaining
    else:
        ledger_content += "\n" + updated_section_5
        
    with open(ledger_file, "w", encoding="utf-8") as f:
        f.write(ledger_content)
        
    print("\n" + "=" * 95)
    print("📊 [3/3] REPORTE DE RESULTADOS: BATCH E (FUNDING_CONTRARIAN)")
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
    run_funding_batch_e()
