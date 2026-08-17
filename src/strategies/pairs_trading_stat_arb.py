"""
Statistical Arbitrage & Cointegration Pairs Trading Engine (Hardened with RegimeFilter)
Filosofía Automaton:
  - Filtro de Régimen: Pausa entradas si BTC cae > 20% en 30d o correlación rolling 30d < 0.60.
  - Ventana móvil Rolling OLS (cero look-ahead bias).
  - Test de Cointegración Engle-Granger / ADF estricto (p < 0.05).
  - Entrada en Z >= 2.5 y Z <= 3.4.
  - Salida a la media (Z = 0.0), Stop Loss (Z = 3.5) y Time-Stop incondicional a 24h.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from src.filters.regime_filter import RegimeFilter

class PairsTradingStatArb:
    """Motor de Arbitraje Estadístico Blindado contra Bear Markets."""
    
    def __init__(
        self,
        lookback_window: int = 90,
        z_entry: float = 2.5,
        z_exit: float = 0.0,
        z_stop: float = 3.5,
        max_holding_bars: int = 24,
        adf_p_threshold: float = 0.05
    ):
        self.w = lookback_window
        self.z_entry = z_entry
        self.z_exit = z_exit
        self.z_stop = z_stop
        self.max_holding_bars = max_holding_bars
        self.adf_p_threshold = adf_p_threshold
        self.regime_filter = RegimeFilter(btc_drop_threshold=-0.20, corr_threshold=0.60, window_30d_bars=720)

    def calculate_rolling_gamma(self, y: np.ndarray, x: np.ndarray) -> float:
        """Calcula gamma OLS: Cov(x, y) / Var(x)."""
        cov = np.cov(x, y)[0, 1]
        var = np.var(x)
        if var == 0:
            return 1.0
        return float(cov / var)

    def test_stationarity(self, spread: np.ndarray) -> Tuple[bool, float]:
        """Ejecuta ADF test sobre el spread residual."""
        try:
            res = adfuller(spread, autolag='AIC')
            p_val = float(res[1])
            return (p_val < self.adf_p_threshold, p_val)
        except:
            return (False, 1.0)

    def calculate_spread_and_zscore(self, df_y: pd.DataFrame, df_x: pd.DataFrame) -> Dict[str, Any]:
        """Calcula el estado actual del spread sin sesgo de anticipación."""
        if len(df_y) < self.w or len(df_x) < self.w:
            return {'valid': False}
            
        y_all = df_y['close'].values
        x_all = df_x['close'].values
        
        y_hist = y_all[-self.w:]
        x_hist = x_all[-self.w:]
        
        gamma = self.calculate_rolling_gamma(y_hist, x_hist)
        spread_hist = y_hist - gamma * x_hist
        
        mean_s = float(np.mean(spread_hist))
        std_s = float(np.std(spread_hist))
        if std_s == 0:
            return {'valid': False}
            
        curr_y = float(y_all[-1])
        curr_x = float(x_all[-1])
        curr_spread = curr_y - gamma * curr_x
        z_score = (curr_spread - mean_s) / std_s
        
        is_stat, p_val = self.test_stationarity(spread_hist)
        
        return {
            'valid': True,
            'gamma': gamma,
            'z_score': z_score,
            'p_value': p_val,
            'is_stationary': is_stat,
            'curr_y': curr_y,
            'curr_x': curr_x,
            'mean_spread': mean_s,
            'std_spread': std_s
        }

    def generate_pair_signal(
        self,
        df_y: pd.DataFrame,
        df_x: pd.DataFrame,
        pair_name: str,
        df_btc: Optional[pd.DataFrame] = None,
        open_pos: Optional[Dict[str, Any]] = None,
        bars_held: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Genera señales con evaluación obligatoria de régimen antes de entrar."""
        data = self.calculate_spread_and_zscore(df_y, df_x)
        if not data.get('valid', False):
            return None
            
        z = data['z_score']
        gamma = data['gamma']
        is_stat = data['is_stationary']
        p_val = data['p_value']
        
        if open_pos is None:
            # 1. Filtro de Estacionariedad
            if not is_stat:
                return None
                
            # 2. Filtro de Régimen de Mercado (BTC -20% en 30d y Correlación Par < 0.60)
            btc_prices = df_btc['close'].values if df_btc is not None and not df_btc.empty else df_y['close'].values
            y_prices = df_y['close'].values
            x_prices = df_x['close'].values
            
            allowed, regime_reason = self.regime_filter.is_entry_allowed(btc_prices, y_prices, x_prices)
            if not allowed:
                return None
                
            # 3. Reglas de Entrada en Histeresis [2.5, 3.4]
            if self.z_entry <= z <= (self.z_entry + 0.9):
                return {
                    'action': 'OPEN_SHORT_SPREAD',
                    'pair': pair_name,
                    'z_score': z,
                    'gamma': gamma,
                    'p_value': p_val,
                    'reason': f"Overvalued Spread (Z={z:.2f} >= {self.z_entry}, p={p_val:.3f}) | {regime_reason}"
                }
            elif -(self.z_entry + 0.9) <= z <= -self.z_entry:
                return {
                    'action': 'OPEN_LONG_SPREAD',
                    'pair': pair_name,
                    'z_score': z,
                    'gamma': gamma,
                    'p_value': p_val,
                    'reason': f"Undervalued Spread (Z={z:.2f} <= -{self.z_entry}, p={p_val:.3f}) | {regime_reason}"
                }
        else:
            side = open_pos['side']
            
            # Time-Stop estricto a las 24 barras (24h)
            if bars_held >= self.max_holding_bars:
                return {'action': 'CLOSE_PAIR', 'z_score': z, 'reason': f"Time-Stop Enforcement (24h reached: {bars_held} bars)"}
                
            # Salidas por objetivo o Stop Loss
            if side == 'SHORT_SPREAD':
                if z <= self.z_exit:
                    return {'action': 'CLOSE_PAIR', 'z_score': z, 'reason': f"Target Mean-Reverted (Z={z:.2f} <= {self.z_exit})"}
                elif z >= self.z_stop:
                    return {'action': 'CLOSE_PAIR', 'z_score': z, 'reason': f"Divergence Stop-Loss (Z={z:.2f} >= {self.z_stop})"}
            elif side == 'LONG_SPREAD':
                if z >= -self.z_exit:
                    return {'action': 'CLOSE_PAIR', 'z_score': z, 'reason': f"Target Mean-Reverted (Z={z:.2f} >= -{self.z_exit})"}
                elif z <= -self.z_stop:
                    return {'action': 'CLOSE_PAIR', 'z_score': z, 'reason': f"Divergence Stop-Loss (Z={z:.2f} <= -{self.z_stop})"}
                    
        return None
