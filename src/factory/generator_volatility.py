"""
Factory Generator for VOLATILITY_COMPRESSION_BREAKOUT
Genera exactamente las 5 variantes solicitadas para Batch C:
1) compression percentile=10, breakout=20
2) compression percentile=15, breakout=20
3) compression percentile=20, breakout=20
4) compression percentile=15, breakout=30
5) compression percentile=20, breakout=30
"""

from typing import List
from dataclasses import dataclass

@dataclass
class VolatilityCandidate:
    id: str
    family: str
    compression_percentile: int
    breakout_lookback: int
    k_atr: float

class VolatilityGenerator:
    """Generador de variantes para Volatility Compression Breakout."""
    
    def __init__(self):
        self.family = "VOLATILITY_COMPRESSION_BREAKOUT"
        self.variants = [
            (10, 20),
            (15, 20),
            (20, 20),
            (15, 30),
            (20, 30)
        ]
        
    def generate_batch(self) -> List[VolatilityCandidate]:
        candidates = []
        for p, b in self.variants:
            cand_id = f"Vol_Comp_P{p}_B{b}"
            candidates.append(VolatilityCandidate(
                id=cand_id,
                family=self.family,
                compression_percentile=p,
                breakout_lookback=b,
                k_atr=2.5
            ))
        return candidates
