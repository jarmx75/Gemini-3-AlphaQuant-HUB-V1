"""
Killer Engine: Aplica la filosofía estricta de supervivencia de Automaton.
Solo sobrevive lo que prueba edge cuantitativo real.
Reglas:
- Si PF < 1.1 o Expectancy <= 0 o Max DD > 15% -> MATA LA ESTRATEGIA Y REGISTRA AUTOPSIA.
- Solo clona y promueve a paper si PF > 1.3 en validación out-of-sample.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

from src.killer_framework.validator import ValidationReport

@dataclass
class StrategyStatus:
    name: str
    status: str # "ALIVE_PROMOTED" o "DEAD_KILLED"
    train_pf: float
    test_pf: float
    val_pf: float
    val_expectancy: float
    val_dd_pct: float
    kill_reason: str
    decision_time: str

class StrategyKiller:
    """Motor de Decisión y Ejecución de la Filosofía Automaton."""
    
    def __init__(self):
        self.strategy_registry: List[StrategyStatus] = []
        
    def evaluate_and_decide(
        self,
        candidate_name: str,
        train_report: ValidationReport,
        test_report: ValidationReport,
        val_report: ValidationReport
    ) -> StrategyStatus:
        """Evalúa el desempeño Walk-Forward y decide vida o muerte."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Comprobar fallos en cualquier etapa
        kill_reasons = []
        if not train_report.passed_filters:
            kill_reasons.append(f"Fallo en Train ({train_report.rejection_reason})")
        if not test_report.passed_filters:
            kill_reasons.append(f"Fallo en Test ({test_report.rejection_reason})")
        if not val_report.passed_filters:
            kill_reasons.append(f"Fallo en Validación ({val_report.rejection_reason})")
            
        if val_report.profit_factor < 1.1:
            kill_reasons.append(f"PF Validación={val_report.profit_factor:.2f} < 1.10")
        if val_report.expectancy <= 0:
            kill_reasons.append(f"Expectancy={val_report.expectancy:.2f} <= 0")
        if val_report.max_drawdown_pct > 15.0:
            kill_reasons.append(f"Max DD={val_report.max_drawdown_pct:.1f}% > 15.0%")
            
        # Decisión final
        if kill_reasons or val_report.profit_factor < 1.3:
            status_str = "DEAD_KILLED"
            reason_final = " | ".join(kill_reasons) if kill_reasons else f"PF={val_report.profit_factor:.2f} < 1.30 (Umbral de Clonación)"
        else:
            status_str = "ALIVE_PROMOTED"
            reason_final = "Superó todos los filtros walk-forward con PF > 1.30"
            
        strat_status = StrategyStatus(
            name=candidate_name,
            status=status_str,
            train_pf=train_report.profit_factor,
            test_pf=test_report.profit_factor,
            val_pf=val_report.profit_factor,
            val_expectancy=val_report.expectancy,
            val_dd_pct=val_report.max_drawdown_pct,
            kill_reason=reason_final,
            decision_time=now_str
        )
        self.strategy_registry.append(strat_status)
        return strat_status

    def render_dashboard(self) -> str:
        """Genera el Dashboard de Estrategias Vivas y Muertas."""
        df = pd.DataFrame([s.__dict__ for s in self.strategy_registry])
        return df.to_string(index=False)
