"""
MACD Stochastic High Speed Scalper Strategy (Fee-Aware Positive Expectancy)
Estrategia de scalping rápido basada en impulso del histograma MACD, oscilador Estocástico y Profit Protector.
"""

import pandas as pd
from typing import Dict, Optional

class MACDStochasticScalperStrategy:
    """Scalper rápido basado en aceleración del histograma MACD y Estocástico."""
    
    def __init__(
        self,
        stop_loss_pct: float = 0.011,
        take_profit_pct: float = 0.028,
        profit_lock_pct: float = 0.012
    ):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.profit_lock_pct = profit_lock_pct
        
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        if len(data) < 30:
            return None
            
        curr = data.iloc[-1]
        prev = data.iloc[-2]
        curr_price = curr['close']
        
        # 1. Posiciones Abiertas
        if open_position is not None:
            side = open_position['side']
            entry_price = open_position['entry_price']
            
            pnl_pct = ((curr_price - entry_price) / entry_price) if (entry_price > 0 and side == 'long') else (((entry_price - curr_price) / entry_price) if entry_price > 0 else 0.0)
            
            # --- 💎 PROFIT PROTECTOR TÁCTICO AL +1.2% ---
            if pnl_pct >= self.profit_lock_pct:
                if pnl_pct < (self.profit_lock_pct * 0.6):
                    return {'action': 'close', 'reason': 'MACD Profit Protector Lock (+1.2%)'}
            
            if side == 'long':
                if curr['low'] <= entry_price * (1 - self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Scalper SL (-1.1%)'}
                if curr['high'] >= entry_price * (1 + self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Scalper TP (+2.8%)'}
                # Salida por sobrecompra estocástica solo si cubre comisiones (al menos +0.4% neto)
                if curr.get('stoch_k', 50) > 80 and pnl_pct >= 0.004:
                    return {'action': 'close', 'reason': 'Scalper Overbought Exit'}
            elif side == 'short':
                if curr['high'] >= entry_price * (1 + self.stop_loss_pct):
                    return {'action': 'close', 'reason': 'Scalper SL (-1.1%)'}
                if curr['low'] <= entry_price * (1 - self.take_profit_pct):
                    return {'action': 'close', 'reason': 'Scalper TP (+2.8%)'}
                if curr.get('stoch_k', 50) < 20 and pnl_pct >= 0.004:
                    return {'action': 'close', 'reason': 'Scalper Oversold Exit'}
            return None

        # 2. Entradas por Impulso y Cruce Estocástico
        macd_hist_curr = curr.get('macd_histogram', 0)
        macd_hist_prev = prev.get('macd_histogram', 0)
        stoch_k = curr.get('stoch_k', 50)
        stoch_d = curr.get('stoch_d', 50)
        
        # Long: MACD Histogram acelera a positivo y Stoch %K cruza por encima de %D en zona baja (<45)
        long_cond = (macd_hist_prev < 0) and (macd_hist_curr > 0) and (stoch_k > stoch_d) and (stoch_k < 45)
        if long_cond:
            return {'action': 'buy', 'reason': 'MACD Scalp Acceleration Long'}
            
        # Short: MACD Histogram acelera a negativo y Stoch %K cruza por debajo de %D en zona alta (>55)
        short_cond = (macd_hist_prev > 0) and (macd_hist_curr < 0) and (stoch_k < stoch_d) and (stoch_k > 55)
        if short_cond:
            return {'action': 'sell', 'reason': 'MACD Scalp Acceleration Short'}
            
        return None

def create_macd_scalper_function(strategy_instance: MACDStochasticScalperStrategy):
    def strategy_func(data: pd.DataFrame) -> Optional[Dict]:
        return strategy_instance.generate_signal(data)
    return strategy_func
