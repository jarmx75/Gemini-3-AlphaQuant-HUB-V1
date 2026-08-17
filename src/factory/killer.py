"""
Factory Killer & Paper Promotion Engine (With Human Approval Gate)
Filosofía Automaton:
  - Si pasa (PF>1.3, DD<15%, Trades>=100): Guarda en live_candidates/ y registra en registry.json.
  - Si falla: Borra código y registra causa en dead_log.csv (sin guardar código muerto).
  - Human Gate: NUNCA toca dinero real automáticamente. Requiere human_approval == 'APPROVED' manual.
"""

import os
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from src.factory.validator import FactoryEvaluationResult
from src.factory.generator import FactoryCandidate

class FactoryKiller:
    """Motor de Decisión y Control de Acceso Humano."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.factory_dir = self.base_dir / "src" / "factory"
        self.live_dir = self.base_dir / "src" / "strategies" / "live_candidates"
        self.registry_file = self.factory_dir / "registry.json"
        self.dead_log_file = self.factory_dir / "dead_log.csv"
        
        self.factory_dir.mkdir(parents=True, exist_ok=True)
        self.live_dir.mkdir(parents=True, exist_ok=True)
        self.init_files()

    def init_files(self):
        if not self.registry_file.exists():
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({"active_paper_strategies": [], "human_approved_real_strategies": []}, f, indent=2)
                
        if not self.dead_log_file.exists():
            with open(self.dead_log_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "candidate_id", "train_pf", "test_pf", "val_pf", "val_trades", "val_dd_pct", "kill_reason"])

    def process_result(self, cand: FactoryCandidate, res: FactoryEvaluationResult) -> Dict[str, Any]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if res.passed:
            # 🟢 PROMOVER A PAPER TRADING
            cand_config = {
                "id": cand.id,
                "lookback_window": cand.lookback_window,
                "z_entry": cand.z_entry,
                "z_exit": cand.z_exit,
                "z_stop": cand.z_stop,
                "max_holding_bars": cand.max_holding_bars,
                "eg_p_threshold": cand.eg_p_threshold,
                "adf_p_threshold": cand.adf_p_threshold,
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
            
            # Guardar archivo JSON de configuración en live_candidates/
            cand_file = self.live_dir / f"{cand.id}.json"
            with open(cand_file, "w", encoding="utf-8") as f:
                json.dump(cand_config, f, indent=2)
                
            # Actualizar registry.json
            with open(self.registry_file, "r", encoding="utf-8") as f:
                reg_data = json.load(f)
                
            # Evitar duplicados
            reg_data["active_paper_strategies"] = [
                s for s in reg_data.get("active_paper_strategies", []) if s["id"] != cand.id
            ]
            reg_data["active_paper_strategies"].append(cand_config)
            
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(reg_data, f, indent=2)
                
            return {"action": "PROMOTED_TO_PAPER", "id": cand.id, "details": cand_config}
        else:
            # 🔴 MATAR Y REGISTRAR EN DEAD_LOG.CSV (NO GUARDAR CÓDIGO MUERTO)
            with open(self.dead_log_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now_str, cand.id, f"{res.train_pf:.2f}", f"{res.test_pf:.2f}",
                    f"{res.val_pf:.2f}", res.val_trades, f"{res.val_max_dd_pct:.1f}", res.verdict
                ])
                
            # Asegurar que no exista en live_candidates
            cand_file = self.live_dir / f"{cand.id}.json"
            if cand_file.exists():
                cand_file.unlink()
                
            return {"action": "KILLED", "id": cand.id, "reason": res.verdict}
