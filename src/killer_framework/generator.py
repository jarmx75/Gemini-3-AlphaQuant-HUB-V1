"""
Generator Module: Genera variantes algorítmicas de arbitraje estadístico market-neutral
con parámetros dinámicos de ventana móvil (rolling OLS / Kalman), filtro ADF y bandas de histeresis.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np

@dataclass
class StrategyCandidate:
    name: str
    lookback_window: int
    z_entry_min: float
    z_entry_max: float
    z_exit: float
    z_stop: float
    adf_pvalue_threshold: float
    min_spread_hurdle_pct: float  # Umbral mínimo de beneficio para cubrir 0.16% de fees
    half_life_max: int            # Tiempo máximo de reversión a la media

class StrategyGenerator:
    """Generador de hipótesis y configuraciones cuantitativas."""
    
    @staticmethod
    def generate_candidate_variants() -> List[StrategyCandidate]:
        candidates = [
            StrategyCandidate(
                name="StatArb_Rolling_60_StrictADF",
                lookback_window=60,
                z_entry_min=2.0,
                z_entry_max=3.0,
                z_exit=0.2,
                z_stop=3.5,
                adf_pvalue_threshold=0.05,
                min_spread_hurdle_pct=0.0035, # 0.35%
                half_life_max=30
            ),
            StrategyCandidate(
                name="StatArb_Rolling_90_Adaptive",
                lookback_window=90,
                z_entry_min=2.1,
                z_entry_max=3.0,
                z_exit=0.25,
                z_stop=3.6,
                adf_pvalue_threshold=0.05,
                min_spread_hurdle_pct=0.0040, # 0.40%
                half_life_max=45
            ),
            StrategyCandidate(
                name="StatArb_Rolling_120_Robust",
                lookback_window=120,
                z_entry_min=2.2,
                z_entry_max=3.0,
                z_exit=0.3,
                z_stop=3.8,
                adf_pvalue_threshold=0.05,
                min_spread_hurdle_pct=0.0045, # 0.45%
                half_life_max=60
            )
        ]
        return candidates
