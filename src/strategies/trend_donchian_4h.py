"""
Trend Following 4H Strategy (Donchian Breakout + ATR Trailing Stop)
STRATEGY_FAMILY = TREND_FOLLOWING_4H

Lógica:
- Agrega OHLCV 1h -> 4h en RAM.
- Long si Close > HighestHigh(N) de las N velas 4h anteriores.
- Short si Close < LowestLow(N) de las N velas 4h anteriores.
- Ejecución en la siguiente vela.
- Stop/trailing = k * ATR(14).
- Exit adicional por breakout contrario.
- Sin RSI, MACD, volumen ni otros filtros.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

class TrendDonchian4H:
    """Motor de Seguimiento de Tendencia Donchian 4H."""
    
    def __init__(self, n_breakout: int = 20, k_atr: float = 2.5, atr_period: int = 14):
        self.n = n_breakout
        self.k = k_atr
        self.atr_period = atr_period

    @staticmethod
    def resample_1h_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
        """Agrega velas 1h a 4h de forma determinista."""
        df = df_1h.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').set_index('timestamp')
        
        df_4h = df.resample('4h', closed='left', label='left').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        return df_4h

    def compute_indicators(self, df_4h: pd.DataFrame) -> pd.DataFrame:
        """Calcula Canales Donchian y ATR(14) sin sesgo de anticipación (shift(1))."""
        df = df_4h.copy()
        
        # Donchian Channels sobre las N velas anteriores (estrictamente shift(1))
        df['highest_high'] = df['high'].shift(1).rolling(self.n).max()
        df['lowest_low'] = df['low'].shift(1).rolling(self.n).min()
        
        # True Range y ATR(14)
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['tr'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['atr'] = df['tr'].rolling(self.atr_period).mean()
        
        return df
