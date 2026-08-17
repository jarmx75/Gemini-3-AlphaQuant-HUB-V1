"""
VWAP Z-Score Mean Reversion Strategy (Fee-Aware Positive Expectancy)
Estrategia cuantitativa de reversión a la media basada en Z-Score, VWAP y Profit Protector.
"""

import pandas as pd
from typing import Dict, Optional

class VWAPMeanReversionStrategy:
    """Estrategia de Reversión a la Media Z-Score de Alta Eficiencia."""
    
    def __init__(
        self,
        entry_z_score: float = 2.2,
        tp_z_score: float = 0.0,
        sl_z_score: float = 3.2,
        stop_loss_pct: float = 0.012,
        profit_lock_pct: float = 0.010
    ):
        self.entry_z_score = entry_z_score
        self.tp_z_score = tp_z_score
        self.sl_z_score = sl_z_score
        self.stop_loss_pct = stop_loss_pct
        self.profit_lock_pct = profit_lock_pct
        
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        if len(data) < 30:
            return None
            
        curr = data.iloc[-1]
        z = curr.get('z_score', 0.0)
        curr_price = curr['close']
        
        # 1. Gestión de Posiciones Abiertas
        if open_position is not None:
            side = open_position['side']
            entry_price = open_position['entry_price']
            
            if entry_price > 0:
                pnl_pct = ((curr_price - entry_price) / entry_price) if side == 'long' else ((entry_price - curr_price) / entry_price)
            else:
                pnl_pct = 0.0
            
            # --- 💎 PROFIT PROTECTOR EN REVERSIÓN ---
            if pnl_pct >= self.profit_lock_pct:
                if pnl_pct < (self.profit_lock_pct * 0.6):
                    return {'action': 'close', 'reason': 'VWAP Profit Protector Lock (+1.0%)'}
            
            if side == 'long':
                if curr['low'] <= entry_price * (1 - self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'VWAP Reversion SL (-1.2%)'}
                if z >= self.tp_z_score and pnl_pct >= 0.005:  # Garantizar al menos +0.5% neto
                    return {'action': 'close', 'reason': 'Mean Reached (Z-Score Exit)'}
            elif side == 'short':
                if curr['high'] >= entry_price * (1 + self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'VWAP Reversion SL (-1.2%)'}
                if z <= self.tp_z_score and pnl_pct >= 0.005:
                    return {'action': 'close', 'reason': 'Mean Reached (Z-Score Exit)'}
            return None

        # 2. Entradas por Desviación de Z-Score Calibrada (2.2 sigma)
        if z <= -self.entry_z_score:
            return {'action': 'buy', 'reason': 'Oversold Z-Score Deviation (Long)'}
        if z >= self.entry_z_score:
            return {'action': 'sell', 'reason': 'Overbought Z-Score Deviation (Short)'}
            
        return None

def create_vwap_reversion_function(strategy_instance: VWAPMeanReversionStrategy):
    def strategy_func(data: pd.DataFrame) -> Optional[Dict]:
        return strategy_instance.generate_signal(data)
    return strategy_func
