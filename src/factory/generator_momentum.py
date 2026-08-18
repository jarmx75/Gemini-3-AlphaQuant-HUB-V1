"""
Factory Generator for CROSS_SECTIONAL_MOMENTUM_4H
Genera exactamente las 5 variantes solicitadas para Batch B:
1) N=6  (24h momentum)
2) N=12 (48h momentum)
3) N=24 (4 días momentum)
4) N=48 (8 días momentum)
5) N=72 (12 días momentum)
"""

from typing import List
from dataclasses import dataclass

@dataclass
class MomentumCandidate:
    id: str
    family: str
    n_lookback: int

class MomentumGenerator:
    """Generador de variantes para Cross-Sectional Momentum 4H."""
    
    def __init__(self):
        self.family = "CROSS_SECTIONAL_MOMENTUM_4H"
        self.lookback_options = [6, 12, 24, 48, 72]
        
    def generate_batch(self) -> List[MomentumCandidate]:
        candidates = []
        for n in self.lookback_options:
            cand_id = f"CS_Mom_4H_N{n}"
            candidates.append(MomentumCandidate(
                id=cand_id,
                family=self.family,
                n_lookback=n
            ))
        return candidates
