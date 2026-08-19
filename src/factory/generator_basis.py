from typing import List
from src.factory.validator_basis import BasisCandidate

class BasisGenerator:
    """Generador de variantes para la familia BASIS_SPOT_PERP."""
    
    def __init__(self):
        self.family = "BASIS_SPOT_PERP"
        
    def generate_batch(self) -> List[BasisCandidate]:
        """Genera exactamente las 5 variantes solicitadas."""
        variants = [
            (1.0,),
            (1.5,),
            (2.0,),
            (2.5,),
            (3.0,)
        ]
        
        candidates = []
        for z in variants:
            c = BasisCandidate(
                id=f"Basis_Z{z[0]}",
                family=self.family,
                entry_z=z[0],
                max_holding_bars=72,
                basis_window=72
            )
            candidates.append(c)
            
        return candidates
