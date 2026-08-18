"""
Factory Generator for FUNDING_CONTRARIAN
Genera exactamente las 5 variantes solicitadas para Batch E:
1) funding_z=1.5, price_extension=0.5 ATR
2) funding_z=2.0, price_extension=0.5 ATR
3) funding_z=2.5, price_extension=0.5 ATR
4) funding_z=2.0, price_extension=1.0 ATR
5) funding_z=2.5, price_extension=1.0 ATR
"""

from typing import List
from dataclasses import dataclass

@dataclass
class FundingCandidate:
    id: str
    family: str
    funding_z: float
    price_extension_atr: float
    max_holding_bars: int = 8

class FundingGenerator:
    """Generador de variantes para Funding Contrarian."""
    
    def __init__(self):
        self.family = "FUNDING_CONTRARIAN"
        self.variants = [
            (1.5, 0.5),
            (2.0, 0.5),
            (2.5, 0.5),
            (2.0, 1.0),
            (2.5, 1.0)
        ]
        
    def generate_batch(self) -> List[FundingCandidate]:
        candidates = []
        for f_z, ext in self.variants:
            cand_id = f"Funding_Z{f_z:.1f}_Ext{ext:.1f}"
            candidates.append(FundingCandidate(
                id=cand_id,
                family=self.family,
                funding_z=f_z,
                price_extension_atr=ext,
                max_holding_bars=8
            ))
        return candidates
