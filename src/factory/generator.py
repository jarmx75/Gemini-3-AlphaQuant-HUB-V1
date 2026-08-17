"""
Factory Generator - Batch 2 (Intelligent Neighborhood Mutation)
Mutación inteligente refinada alrededor del modelo ganador (PF 1.60):
- Variantes:
  1. W90, Z2.5, S3.5, H24 (Baseline probado)
  2. W90, Z2.4, S3.5, H24 (Z más reactivo)
  3. W80, Z2.5, S3.5, H24 (Ventana más rápida)
  4. W100, Z2.5, S3.5, H24 (Ventana más suave)
  5. W90, Z2.6, S4.0, H24 (Stop más holgado)
"""

from typing import List
from dataclasses import dataclass

@dataclass
class FactoryCandidate:
    id: str
    lookback_window: int
    z_entry: float
    z_exit: float
    z_stop: float
    max_holding_bars: int
    eg_p_threshold: float
    adf_p_threshold: float
    pairs: List[tuple]

class FactoryGenerator:
    """Generador inteligente de variantes mutadas en el vecindario de edge."""
    
    def __init__(self):
        self.available_pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        
    def generate_batch(self, batch_size: int = 5) -> List[FactoryCandidate]:
        # Mutaciones sistemáticas solicitadas
        selected_presets = [
            (90, 2.5, 3.5, 24),
            (90, 2.4, 3.5, 24),
            (80, 2.5, 3.5, 24),
            (100, 2.5, 3.5, 24),
            (90, 2.6, 4.0, 24)
        ]
        
        candidates = []
        for w, z_in, z_stop, h in selected_presets[:batch_size]:
            cand_id = f"Pairs_W{w}_Z{z_in}_S{z_stop}_H{h}"
            candidates.append(FactoryCandidate(
                id=cand_id,
                lookback_window=w,
                z_entry=z_in,
                z_exit=0.0,
                z_stop=z_stop,
                max_holding_bars=h,
                eg_p_threshold=0.03,
                adf_p_threshold=0.05,
                pairs=self.available_pairs
            ))
            
        return candidates
