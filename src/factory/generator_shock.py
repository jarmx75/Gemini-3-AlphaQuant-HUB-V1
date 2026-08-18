"""
Factory Generator for EVENT_SHOCK_REVERSAL_1H
Genera exactamente las 5 variantes solicitadas para Batch D:
1) return_z=2.0, volume_z=1.5
2) return_z=2.0, volume_z=2.0
3) return_z=2.5, volume_z=1.5
4) return_z=2.5, volume_z=2.0
5) return_z=3.0, volume_z=2.0
"""

from typing import List
from dataclasses import dataclass

@dataclass
class ShockCandidate:
    id: str
    family: str
    return_z: float
    volume_z: float
    max_holding_bars: int = 4

class ShockGenerator:
    """Generador de variantes para Event Shock Reversal 1H."""
    
    def __init__(self):
        self.family = "EVENT_SHOCK_REVERSAL_1H"
        self.variants = [
            (2.0, 1.5),
            (2.0, 2.0),
            (2.5, 1.5),
            (2.5, 2.0),
            (3.0, 2.0)
        ]
        
    def generate_batch(self) -> List[ShockCandidate]:
        candidates = []
        for r_z, v_z in self.variants:
            cand_id = f"Shock_R{r_z:.1f}_V{v_z:.1f}"
            candidates.append(ShockCandidate(
                id=cand_id,
                family=self.family,
                return_z=r_z,
                volume_z=v_z,
                max_holding_bars=4
            ))
        return candidates
