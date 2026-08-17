"""
Adaptive SuperTrend Volatility Trend Following Strategy
Estrategia seguidora de tendencia adaptativa por volatilidad.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdaptiveSuperTrendStrategy:
    """Estrategia SuperTrend Adaptativa."""
    
    def __init__(
        self,
        atr_period: int = 10,
        multiplier: float = 3.0,
        rsi_period: int = 14,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.05
    ):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.rsi_period = rsi_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        if len(data) < self.atr_period + 20:
            return None
            
        curr = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Calcular SuperTrend dinámico si no está precalculado
        high_low = (data['high'] + data['low']) / 2
        atr = data['atr'] if 'atr' in data.columns else (data['high'] - data['low']).rolling(self.atr_period).mean()
        
        upper_band = high_low + (self.multiplier * atr)
        lower_band = high_low - (self.multiplier * atr)
        
        # 1. Gestión de Posiciones Abiertas
        if open_position is not None:
            side = open_position['side']
            entry_price = open_position['entry_price']
            
            if side == 'long':
                if curr['low'] <= entry_price * (1 - self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'SuperTrend SL (-2%)'}
                if curr['high'] >= entry_price * (1 + self.take_profit_pct):
                    return {'action': 'close', 'reason': 'SuperTrend TP (+5%)'}
                if curr['close'] < lower_band.iloc[-1]:
                    return {'action': 'close', 'reason': 'SuperTrend Flip Exit'}
            elif side == 'short':
                if curr['high'] >= entry_price * (1 + self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'SuperTrend SL (-2%)'}
                if curr['low'] <= entry_price * (1 - self.take_profit_pct):
                    return {'action': 'close', 'reason': 'SuperTrend TP (+5%)'}
                if curr['close'] > upper_band.iloc[-1]:
                    return {'action': 'close', 'reason': 'SuperTrend Flip Exit'}
            return None
            
        # 2. Entradas
        rsi = curr.get('rsi', 50)
        cruce_alcista = (prev['close'] <= upper_band.iloc[-2]) and (curr['close'] > upper_band.iloc[-1])
        cruce_bajista = (prev['close'] >= lower_band.iloc[-2]) and (curr['close'] < lower_band.iloc[-1])
        
        if cruce_alcista and rsi > 50:
            return {'action': 'buy', 'reason': 'SuperTrend Bullish Breakout'}
        if cruce_bajista and rsi < 50:
            return {'action': 'sell', 'reason': 'SuperTrend Bearish Breakout'}
            
        return None


def create_supertrend_strategy_function(strategy_instance: AdaptiveSuperTrendStrategy):
    def strategy_func(data: pd.DataFrame) -> Optional[Dict]:
        return strategy_instance.generate_signal(data)
    return strategy_func
