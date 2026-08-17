"""
Scientific Market Regime Filter Module (Kaufman Efficiency Ratio & Volatility Z-Score)
Clasifica matemáticamente el régimen del precio en TRENDING, RANGING o NEUTRAL.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class ScientificRegimeFilter:
    """Clasificador Cuantitativo de Régimen Estocástico de Mercado."""
    
    def __init__(self, er_period: int = 14, atr_period: int = 14):
        self.er_period = er_period
        self.atr_period = atr_period
        
    def calculate_efficiency_ratio(self, prices: pd.Series) -> float:
        """Calcula la Razón de Eficiencia de Kaufman (ER)."""
        if len(prices) < self.er_period + 1:
            return 0.5
            
        change = abs(prices.iloc[-1] - prices.iloc[-self.er_period - 1])
        volatility = (prices.diff().abs().iloc[-self.er_period:]).sum()
        
        if volatility == 0:
            return 0.0
            
        return float(change / volatility)

    def calculate_atr_zscore(self, df: pd.DataFrame) -> float:
        """Calcula el Z-Score de la volatilidad ATR."""
        if 'atr' not in df.columns or len(df) < 50:
            return 0.0
            
        atr_series = df['atr'].tail(50)
        mean_atr = atr_series.mean()
        std_atr = atr_series.std()
        
        if std_atr == 0:
            return 0.0
            
        latest_atr = atr_series.iloc[-1]
        return float((latest_atr - mean_atr) / std_atr)

    def detect_regime(self, df: pd.DataFrame) -> Tuple[str, Dict[str, float]]:
        """
        Determina el régimen del mercado.
        
        Returns:
            Tuple con ('TRENDING' | 'RANGING' | 'NEUTRAL', dict_metricas)
        """
        if len(df) < self.er_period + 5:
            return 'NEUTRAL', {'er': 0.5, 'z_atr': 0.0}
            
        close_prices = df['close']
        er = self.calculate_efficiency_ratio(close_prices)
        z_atr = self.calculate_atr_zscore(df)
        
        metrics = {'er': round(er, 4), 'z_atr': round(z_atr, 4)}
        
        if er >= 0.52:
            return 'TRENDING', metrics
        elif er <= 0.38:
            return 'RANGING', metrics
        else:
            return 'NEUTRAL', metrics
