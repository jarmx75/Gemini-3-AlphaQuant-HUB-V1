"""
Cross-Sectional Momentum 4H Strategy
STRATEGY_FAMILY = CROSS_SECTIONAL_MOMENTUM_4H

Lógica:
- Universo fijo: BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT, LINKUSDT, DOTUSDT.
- Agrega OHLCV 1h -> 4h en RAM.
- En cada cierre 4h calcula retorno: R[t] = Close[t] / Close[t-N] - 1 para cada activo.
- Rankea los 6 activos por momentum.
- Long = #1 (Winner), Short = #6 (Loser), igual nocional.
- Ejecuta las posiciones en la siguiente vela 4h para evitar look-ahead bias.
- Rebalanceo cada 4h.
- Sin RSI, MACD, ATR ni volumen.
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

class CrossSectionalMomentum4H:
    """Motor de Momentum Transversal 4H."""
    
    def __init__(self, lookback_n: int = 12):
        self.n = lookback_n
        self.universe = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']

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

    def compute_momentum_table(self, dict_4h: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Construye una matriz alineada por timestamp con los retornos a N periodos de cada activo.
        """
        close_series = {}
        for sym in self.universe:
            if sym in dict_4h:
                df = dict_4h[sym].sort_values('timestamp').reset_index(drop=True)
                close_series[sym] = df.set_index('timestamp')['close']
                
        df_closes = pd.DataFrame(close_series).dropna().sort_index()
        
        # Retornos a N barras (4h): R[t] = Close[t] / Close[t-N] - 1
        df_returns = df_closes.pct_change(self.n).dropna()
        
        return df_closes, df_returns
