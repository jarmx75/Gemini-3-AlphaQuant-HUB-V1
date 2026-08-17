"""
Factory Generator (Token-Light & Fast)
Genera exactamente 5 variantes sistemáticas por lote sin crear indicadores nuevos:
- Parámetros: Rolling window (60, 90, 120), Z_entry (2.2, 2.5, 2.8), Z_stop (3.5, 4.0), Pares históricos.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import random

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
    """Generador ligero y determinista de variantes cuantitativas."""
    
    def __init__(self):
        self.available_pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        self.lookback_options = [60, 90, 120]
        self.z_entry_options = [2.2, 2.5, 2.8]
        self.z_stop_options = [3.5, 4.0]
        self.max_holding_options = [24, 36]
        
    def generate_batch(self, batch_size: int = 5) -> List[FactoryCandidate]:
        """Genera un lote de 5 variantes deterministas / combinatorias."""
        candidates = []
        combinations = []
        
        for w in self.lookback_options:
            for z_in in self.z_entry_options:
                for z_stop in self.z_stop_options:
                    for h in self.max_holding_options:
                        combinations.append((w, z_in, z_stop, h))
                        
        # Tomar 5 combinaciones pseudo-aleatorias pero reproducibles
        selected = random.sample(combinations, min(batch_size, len(combinations)))
        
        for i, (w, z_in, z_stop, h) in enumerate(selected, 1):
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
