"""
Estrategia EMA Cross con Profit Protector y Gestión de Riesgo (ROWBOAT Port)
Estrategia basada en el bot ROWBOAT V51 para el motor de backtesting de DEVIN.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class EMACrossProtectorStrategy:
    """
    Estrategia Cuantitativa EMA Cross con filtro multitemporal, RSI y Profit Protector.
    """
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        ema_macro: int = 200,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        stop_loss_pct: float = 0.015,     # 1.5% Stop Loss inicial
        take_profit_pct: float = 0.035,    # 3.5% Take Profit objetivo
        proteccion_nivel1_pct: float = 0.012, # A los +1.2% asegura +0.4%
        proteccion_asegurar1_pct: float = 0.004,
        proteccion_nivel2_pct: float = 0.020, # A los +2.0% asegura +1.2%
        proteccion_asegurar2_pct: float = 0.012,
        cooldown_bars: int = 4            # Cooldown de 4 velas tras pérdida
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_macro = ema_macro
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.proteccion_nivel1_pct = proteccion_nivel1_pct
        self.proteccion_asegurar1_pct = proteccion_asegurar1_pct
        self.proteccion_nivel2_pct = proteccion_nivel2_pct
        self.proteccion_asegurar2_pct = proteccion_asegurar2_pct
        self.cooldown_bars = cooldown_bars
        
        self.last_loss_bar = {}  # {symbol: bar_index}
    
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        """
        Generar señal de trading para la barra actual.
        
        Args:
            data: DataFrame con OHLCV e indicadores (ema_9, ema_21, ema_200, rsi)
            open_position: Posición abierta actual si existe {'side', 'entry_price', 'highest_price', 'lowest_price', 'entry_bar'}
            
        Returns:
            Dict con {'action': 'buy'|'sell'|'close', 'reason': str} o None
        """
        if len(data) < max(self.ema_macro, self.rsi_period) + 2:
            return None
        
        curr = data.iloc[-1]
        prev = data.iloc[-2]
        curr_bar_idx = len(data) - 1
        symbol = curr.get('symbol', 'ASSET')
        
        # 1. Si hay posición abierta, gestionar TP/SL y Profit Protector
        if open_position is not None:
            side = open_position['side']
            entry_price = open_position['entry_price']
            high_price = open_position.get('highest_price', curr['high'])
            low_price = open_position.get('lowest_price', curr['low'])
            
            if side == 'long':
                # Calcular ganancias máximas alcanzadas
                pnl_pct_high = (high_price - entry_price) / entry_price
                pnl_pct_curr = (curr['close'] - entry_price) / entry_price
                
                # Check Stop Loss Inicial
                if curr['low'] <= entry_price * (1 - self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Stop Loss (-1.5%)'}
                
                # Check Take Profit Final
                if curr['high'] >= entry_price * (1 + self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Take Profit Final (+3.5%)'}
                
                # Profit Protector Nivel 2 (+2.0% -> asegura +1.2%)
                if pnl_pct_high >= self.proteccion_nivel2_pct:
                    if curr['close'] <= entry_price * (1 + self.proteccion_asegurar2_pct):
                        return {'action': 'close', 'reason': 'Profit Protector Nivel 2 (Locked +1.2%)'}
                        
                # Profit Protector Nivel 1 (+1.2% -> asegura +0.4%)
                elif pnl_pct_high >= self.proteccion_nivel1_pct:
                    if curr['close'] <= entry_price * (1 + self.proteccion_asegurar1_pct):
                        return {'action': 'close', 'reason': 'Profit Protector Nivel 1 (Locked +0.4%)'}
                
                # Señal inversa de salida (Cruce bajista EMA 9/21)
                if curr['ema_9'] < curr['ema_21'] and prev['ema_9'] >= prev['ema_21']:
                    return {'action': 'close', 'reason': 'EMA Cross Exit'}

            elif side == 'short':
                pnl_pct_low = (entry_price - low_price) / entry_price
                pnl_pct_curr = (entry_price - curr['close']) / entry_price
                
                # Check Stop Loss Inicial
                if curr['high'] >= entry_price * (1 + self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Stop Loss (-1.5%)'}
                
                # Check Take Profit Final
                if curr['low'] <= entry_price * (1 - self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Take Profit Final (+3.5%)'}
                
                # Profit Protector Nivel 2 (+2.0% -> asegura +1.2%)
                if pnl_pct_low >= self.proteccion_nivel2_pct:
                    if curr['close'] >= entry_price * (1 - self.proteccion_asegurar2_pct):
                        return {'action': 'close', 'reason': 'Profit Protector Nivel 2 (Locked +1.2%)'}
                        
                # Profit Protector Nivel 1 (+1.2% -> asegura +0.4%)
                elif pnl_pct_low >= self.proteccion_nivel1_pct:
                    if curr['close'] >= entry_price * (1 - self.proteccion_asegurar1_pct):
                        return {'action': 'close', 'reason': 'Profit Protector Nivel 1 (Locked +0.4%)'}
                
                # Señal inversa de salida (Cruce alcista EMA 9/21)
                if curr['ema_9'] > curr['ema_21'] and prev['ema_9'] <= prev['ema_21']:
                    return {'action': 'close', 'reason': 'EMA Cross Exit'}
                    
            return None

        # 2. Check Cooldown tras pérdida
        if symbol in self.last_loss_bar:
            if curr_bar_idx - self.last_loss_bar[symbol] < self.cooldown_bars:
                return None

        # 3. Evaluar Nuevas Entradas
        ema_fast_curr, ema_slow_curr = curr['ema_9'], curr['ema_21']
        ema_fast_prev, ema_slow_prev = prev['ema_9'], prev['ema_21']
        ema_macro = curr.get('ema_200', curr['close'])
        rsi = curr['rsi']
        
        # Filtros de Tendencia Macro
        macro_bullish = curr['close'] > ema_macro
        macro_bearish = curr['close'] < ema_macro
        
        # Condición LONG: Cruce Alcista EMA 9/21 + Tendencia Macro + RSI no sobrecomprado
        cruce_long = (ema_fast_prev <= ema_slow_prev) and (ema_fast_curr > ema_slow_curr)
        if cruce_long and macro_bullish and (rsi > 45) and (rsi < self.rsi_overbought):
            return {'action': 'buy', 'reason': 'EMA 9/21 Golden Cross + Macro Bullish'}
            
        # Condición SHORT: Cruce Bajista EMA 9/21 + Tendencia Macro + RSI no sobrevendido
        cruce_short = (ema_fast_prev >= ema_slow_prev) and (ema_fast_curr < ema_slow_curr)
        if cruce_short and macro_bearish and (rsi < 55) and (rsi > self.rsi_oversold):
            return {'action': 'sell', 'reason': 'EMA 9/21 Death Cross + Macro Bearish'}

        return None


def create_ema_cross_protector_function(strategy_instance: EMACrossProtectorStrategy):
    """
    Adapter para convertir la estrategia en una función compatible con BacktestEngine.
    """
    def strategy_func(data: pd.DataFrame) -> Optional[Dict]:
        return strategy_instance.generate_signal(data)
    return strategy_func
