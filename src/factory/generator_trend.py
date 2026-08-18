"""
Factory Generator for TREND_FOLLOWING_4H
Genera exactamente las 5 variantes solicitadas para Batch A:
1) N=20, k=2.0
2) N=20, k=2.5
3) N=30, k=2.5
4) N=40, k=2.5
5) N=40, k=3.0
"""

from typing import List
from dataclasses import dataclass

@dataclass
class TrendCandidate:
    id: str
    family: str
    n_breakout: int
    k_atr: float
    atr_period: int

class TrendGenerator:
    """Generador de variantes para Trend Following 4H."""
    
    def __init__(self):
        self.family = "TREND_FOLLOWING_4H"
        self.variants = [
            (20, 2.0),
            (20, 2.5),
            (30, 2.5),
            (40, 2.5),
            (40, 3.0)
        ]
        
    def generate_batch(self) -> List[TrendCandidate]:
        candidates = []
        for n, k in self.variants:
            cand_id = f"Trend_4H_N{n}_K{k:.1f}"
            candidates.append(TrendCandidate(
                id=cand_id,
                family=self.family,
                n_breakout=n,
                k_atr=k,
                atr_period=14
            ))
        return candidates
