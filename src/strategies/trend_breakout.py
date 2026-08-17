"""
Trend Momentum Breakout Strategy (Donchian / Keltner Channels + Profit Protector)
Estrategia de ruptura de rangos con filtro de momentum, volumen y protección de ganancias.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

class TrendBreakoutStrategy:
    """Estrategia de Ruptura de Canal Donchian con Profit Protector."""
    
    def __init__(
        self,
        lookback: int = 20,
        stop_loss_pct: float = 0.012,    # Stop loss apretado del 1.2%
        take_profit_pct: float = 0.035,   # Take profit del 3.5%
        profit_lock_pct: float = 0.008   # Profit Protector al +0.8%
    ):
        self.lookback = lookback
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.profit_lock_pct = profit_lock_pct
        
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        if len(data) < self.lookback + 5:
            return None
            
        curr = data.iloc[-1]
        past = data.iloc[-self.lookback-1:-1]
        
        upper_channel = past['high'].max()
        lower_channel = past['low'].min()
        
        # 1. Gestión de Posiciones Abiertas
        if open_position is not None:
            side = open_position['side']
            entry_price = open_position['entry_price']
            curr_price = curr['close']
            
            pnl_pct = ((curr_price - entry_price) / entry_price) if side == 'long' else ((entry_price - curr_price) / entry_price)
            
            # --- 💎 PROFIT PROTECTOR TÁCTICO ---
            if pnl_pct >= self.profit_lock_pct:
                # Si se logró +0.8% de ganancia y comienza a retroceder al 0.3%, cerrar con ganancia neta
                if pnl_pct < (self.profit_lock_pct * 0.5):
                    return {'action': 'close', 'reason': 'Breakout Profit Protector Lock'}
            
            if side == 'long':
                if curr['low'] <= entry_price * (1 - self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Breakout SL (1.2%)'}
                if curr['high'] >= entry_price * (1 + self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Breakout TP (3.5%)'}
                if curr['close'] < past['low'].tail(5).min():
                    return {'action': 'close', 'reason': 'Donchian Fast Exit'}
            elif side == 'short':
                if curr['high'] >= entry_price * (1 + self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Breakout SL (1.2%)'}
                if curr['low'] <= entry_price * (1 - self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Breakout TP (3.5%)'}
                if curr['close'] > past['high'].tail(5).max():
                    return {'action': 'close', 'reason': 'Donchian Fast Exit'}
            return None

        # 2. Señales de Entrada con Filtro de Volumen Fuerte (1.5x)
        vol_avg = past['volume'].mean()
        high_vol = curr['volume'] > vol_avg * 1.5
        
        if curr['close'] > upper_channel and high_vol:
            return {'action': 'buy', 'reason': 'Donchian Upper Breakout + High Volume'}
        if curr['close'] < lower_channel and high_vol:
            return {'action': 'sell', 'reason': 'Donchian Lower Breakout + High Volume'}
            
        return None

def create_breakout_strategy_function(strategy_instance: TrendBreakoutStrategy):
    def strategy_func(data: pd.DataFrame) -> Optional[Dict]:
        return strategy_instance.generate_signal(data)
    return strategy_func
