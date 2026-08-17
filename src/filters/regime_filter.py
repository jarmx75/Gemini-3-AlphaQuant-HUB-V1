"""
Regime Filter Module (Bear Market & Structural Decoupling Protection)
Protección contra colapsos sistémicos (FTX, Terra Luna, Bear Markets):
  - Pausa entradas si Bitcoin cae > 20% en los últimos 30 días (720 barras de 1h).
  - Pausa entradas si la correlación de Pearson rolling a 30 días del par es < 0.60.
"""

from typing import Tuple
import numpy as np
import pandas as pd

class RegimeFilter:
    """Filtro de Régimen Cuantitativo Institucional."""
    
    def __init__(self, btc_drop_threshold: float = -0.20, corr_threshold: float = 0.60, window_30d_bars: int = 720):
        self.btc_drop_threshold = btc_drop_threshold # -20%
        self.corr_threshold = corr_threshold         # 0.60
        self.w_30d = window_30d_bars                 # 30 días en velas de 1h = 720 velas

    def check_btc_regime(self, btc_prices_1h: np.ndarray) -> Tuple[bool, float, str]:
        """
        Verifica el retorno de BTC en los últimos 30 días (720 barras).
        Retorna:
            (is_allowed, btc_30d_return, reason)
        """
        if len(btc_prices_1h) < self.w_30d:
            # Si hay menos de 30d, calcular sobre el historial disponible
            ret_30d = (btc_prices_1h[-1] - btc_prices_1h[0]) / (btc_prices_1h[0] + 1e-9)
        else:
            p_now = btc_prices_1h[-1]
            p_past = btc_prices_1h[-self.w_30d]
            ret_30d = (p_now - p_past) / (p_past + 1e-9)
            
        if ret_30d <= self.btc_drop_threshold:
            return False, float(ret_30d), f"BTC Crash Alert: BTC {ret_30d*100:.1f}% en 30d (<= -20%)"
        return True, float(ret_30d), "BTC Regime OK"

    def check_pair_correlation_regime(self, y_prices_1h: np.ndarray, x_prices_1h: np.ndarray) -> Tuple[bool, float, str]:
        """
        Verifica la correlación de Pearson rolling de 30 días entre los dos activos.
        Retorna:
            (is_allowed, corr_30d, reason)
        """
        w = min(self.w_30d, len(y_prices_1h), len(x_prices_1h))
        if w < 30:
            return True, 1.0, "Insufficient bars for corr check"
            
        y_w = y_prices_1h[-w:]
        x_w = x_prices_1h[-w:]
        
        corr_mat = np.corrcoef(y_w, x_w)
        corr_val = float(corr_mat[0, 1]) if not np.isnan(corr_mat[0, 1]) else 0.0
        
        if corr_val < self.corr_threshold:
            return False, corr_val, f"Decoupling Alert: Corr 30d = {corr_val:.2f} (< {self.corr_threshold})"
        return True, corr_val, "Correlation Regime OK"

    def is_entry_allowed(
        self,
        btc_prices_1h: np.ndarray,
        y_prices_1h: np.ndarray,
        x_prices_1h: np.ndarray
    ) -> Tuple[bool, str]:
        """
        Evalúa ambas condiciones de régimen antes de autorizar una nueva entrada.
        """
        # 1. Comprobar régimen de BTC
        btc_ok, btc_ret, btc_reason = self.check_btc_regime(btc_prices_1h)
        if not btc_ok:
            return False, btc_reason
            
        # 2. Comprobar régimen de correlación del par
        corr_ok, corr_val, corr_reason = self.check_pair_correlation_regime(y_prices_1h, x_prices_1h)
        if not corr_ok:
            return False, corr_reason
            
        return True, f"Regime Permissive (BTC 30d: {btc_ret*100:+.1f}%, Corr 30d: {corr_val:.2f})"
