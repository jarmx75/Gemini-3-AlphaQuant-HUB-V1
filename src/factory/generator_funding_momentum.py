"""
Factory Generator for FUNDING_MOMENTUM_1H
Genera exactamente las 5 variantes solicitadas para Batch F:
1) funding_z=0.5, momentum=12h
2) funding_z=1.0, momentum=12h
3) funding_z=1.5, momentum=12h
4) funding_z=1.0, momentum=24h
5) funding_z=1.5, momentum=24h
"""

from typing import List
from dataclasses import dataclass

@dataclass
class FundingMomentumCandidate:
    id: str
    family: str
    funding_z: float
    momentum_hours: int
    max_holding_bars: int = 24

class FundingMomentumGenerator:
    """Generador de variantes para Funding Momentum."""
    
    def __init__(self):
        self.family = "FUNDING_MOMENTUM_1H"
        self.variants = [
            (0.5, 12),
            (1.0, 12),
            (1.5, 12),
            (1.0, 24),
            (1.5, 24)
        ]
        
    def generate_batch(self) -> List[FundingMomentumCandidate]:
        candidates = []
        for f_z, m_h in self.variants:
            cand_id = f"FundingMom_Z{f_z:.1f}_M{m_h}"
            candidates.append(FundingMomentumCandidate(
                id=cand_id,
                family=self.family,
                funding_z=f_z,
                momentum_hours=m_h,
                max_holding_bars=24
            ))
        return candidates
