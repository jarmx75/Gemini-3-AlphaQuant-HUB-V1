"""
Factory Generator for LIQUIDATION_DERIVATIVES_REVERSAL (DERIVATIVES_SHOCK_REVERSAL)
Genera exactamente las 5 variantes solicitadas para Batch D2:
1) return_z=2.0, OI_z=2.0, taker_z=2.0
2) return_z=2.5, OI_z=2.0, taker_z=2.0
3) return_z=2.5, OI_z=2.5, taker_z=2.0
4) return_z=3.0, OI_z=2.0, taker_z=2.5
5) return_z=3.0, OI_z=2.5, taker_z=2.5
"""

from typing import List
from dataclasses import dataclass

@dataclass
class DerivativesShockCandidate:
    id: str
    family: str
    return_z: float
    oi_z: float
    taker_z: float
    max_holding_bars: int = 4

class DerivativesShockGenerator:
    """Generador de variantes para Derivatives Shock Reversal."""
    
    def __init__(self):
        self.family = "LIQUIDATION_DERIVATIVES_REVERSAL"
        self.variants = [
            (2.0, 2.0, 2.0),
            (2.5, 2.0, 2.0),
            (2.5, 2.5, 2.0),
            (3.0, 2.0, 2.5),
            (3.0, 2.5, 2.5)
        ]
        
    def generate_batch(self) -> List[DerivativesShockCandidate]:
        candidates = []
        for r_z, oi_z, t_z in self.variants:
            cand_id = f"Deriv_Shock_R{r_z:.1f}_OI{oi_z:.1f}_T{t_z:.1f}"
            candidates.append(DerivativesShockCandidate(
                id=cand_id,
                family=self.family,
                return_z=r_z,
                oi_z=oi_z,
                taker_z=t_z,
                max_holding_bars=4
            ))
        return candidates
