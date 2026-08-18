"""
Volatility Compression Breakout Strategy (4H)
STRATEGY_FAMILY = VOLATILITY_COMPRESSION_BREAKOUT

Lógica:
- Agrega OHLCV 1h -> 4h en RAM.
- Calcula Bollinger Bandwidth (BBW) con ventana 20: (Upper - Lower) / SMA(20).
- Compression = BBW en percentil histórico rolling bajo (P=10, 15, 20 sobre 120 barras).
- Entrar Long si, tras compresión, Close > HighestHigh(B) de las B velas ANTERIORES (B=20 o 30).
- Entrar Short si, tras compresión, Close < LowestLow(B) de las B velas ANTERIORES.
- Ejecución en la siguiente vela 4h (open) sin look-ahead.
- Stop/trailing basado en k * ATR(14) (k=2.5) y salida adicional por breakout contrario.
- Sin RSI, MACD, volumen, funding ni OI.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

class VolatilityCompressionBreakout4H:
    """Motor de Rompimiento tras Compresión de Volatilidad 4H."""
    
    def __init__(
        self,
        compression_percentile: int = 15,
        breakout_lookback: int = 20,
        k_atr: float = 2.5,
        bb_window: int = 20,
        percentile_window: int = 120,
        atr_period: int = 14
    ):
        self.p_pct = compression_percentile
        self.b_lookback = breakout_lookback
        self.k_atr = k_atr
        self.bb_window = bb_window
        self.p_window = percentile_window
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
        """Calcula Bollinger Bandwidth, Percentil de Compresión, Breakout Donchian y ATR(14)."""
        df = df_4h.copy()
        
        # 1. Bollinger Bandwidth (BBW)
        sma = df['close'].rolling(self.bb_window).mean()
        std = df['close'].rolling(self.bb_window).std()
        upper = sma + 2.0 * std
        lower = sma - 2.0 * std
        df['bbw'] = ((upper - lower) / (sma + 1e-12)).fillna(0.0)
        
        # 2. Umbral de Compresión: Percentil rolling de BBW (shift(1) para evitar look-ahead)
        bbw_shifted = df['bbw'].shift(1)
        df['bbw_threshold'] = bbw_shifted.rolling(self.p_window).quantile(self.p_pct / 100.0)
        
        # Compresión activa si BBW previo estaba en o por debajo del percentil
        df['is_compressed'] = (bbw_shifted <= df['bbw_threshold']).rolling(3).max() == 1.0
        
        # 3. Canales Donchian de Breakout (shift(1) para las B velas anteriores)
        df['highest_high'] = df['high'].shift(1).rolling(self.b_lookback).max()
        df['lowest_low'] = df['low'].shift(1).rolling(self.b_lookback).min()
        
        # 4. True Range y ATR(14)
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['tr'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['atr'] = df['tr'].rolling(self.atr_period).mean()
        
        return df
