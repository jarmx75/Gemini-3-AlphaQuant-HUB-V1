"""
Funding Contrarian 1H Strategy
STRATEGY_FAMILY = FUNDING_CONTRARIAN

Lógica:
- Universo: BTCUSDT, ETHUSDT.
- Velas OHLCV 1H + Funding Rate 8H.
- Alineación temporal estricta:
  - El funding publicado en T_funding (00:00, 08:00, 16:00 UTC) solo se utiliza en ese momento.
  - La señal se genera al conocer el funding y el cierre de la vela 1H de esa hora.
  - La entrada se ejecuta en la siguiente vela 1H (Open) sin look-ahead.
- Features:
  1) Funding Z-score (W=90 observaciones de 8h = 30 días).
  2) ATR(14) sobre 1H.
  3) Price Extension = (Close - SMA20) / ATR14.
- Señal:
  - Short: FundingZ >= threshold AND Price Extension >= extension_atr
  - Long: FundingZ <= -threshold AND Price Extension <= -extension_atr
- Salidas:
  - Reversión hacia SMA20.
  - Time-stop máximo de 8 velas (8h).
  - Stop de emergencia 3.0%.
- Cero RSI, MACD, volumen, OI ni taker imbalance.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

class FundingContrarian1H:
    """Motor de Trading Contrarian basado en Funding Rate."""
    
    def __init__(
        self,
        funding_z_threshold: float = 2.0,
        price_extension_atr: float = 0.5,
        funding_window: int = 90,
        mean_window: int = 20,
        atr_period: int = 14,
        max_holding_bars: int = 8,
        emergency_stop_pct: float = 0.03
    ):
        self.funding_z = funding_z_threshold
        self.ext_atr = price_extension_atr
        self.f_w = funding_window
        self.mean_w = mean_window
        self.atr_period = atr_period
        self.max_holding_bars = max_holding_bars
        self.emergency_stop_pct = emergency_stop_pct

    def prepare_dataset(self, df_ohlcv: pd.DataFrame, df_funding: pd.DataFrame) -> pd.DataFrame:
        """Fusiona OHLCV 1H y Funding Rate 8H con alineación temporal estricta."""
        df = df_ohlcv.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 1. Procesar Funding Rate
        dff = df_funding.copy()
        dff['fundingTime'] = pd.to_datetime(dff['fundingTime']).dt.round('1s')
        dff = dff.sort_values('fundingTime').drop_duplicates('fundingTime').reset_index(drop=True)
        
        # Calcular Funding Z-Score sobre la serie de 8h (shift(1) para no usar el funding actual en la media)
        f_mean = dff['fundingRate'].shift(1).rolling(self.f_w).mean()
        f_std = dff['fundingRate'].shift(1).rolling(self.f_w).std().replace(0, np.nan)
        dff['funding_z'] = ((dff['fundingRate'] - f_mean) / f_std).fillna(0.0)
        dff['is_funding_bar'] = True
        
        # 2. Alinear con OHLCV 1H (merge exacto en las velas de 00:00, 08:00, 16:00)
        dff = dff.rename(columns={'fundingTime': 'timestamp'})
        df = pd.merge(df, dff[['timestamp', 'fundingRate', 'funding_z', 'is_funding_bar']],
                      on='timestamp', how='left')
        df['is_funding_bar'] = df['is_funding_bar'].fillna(False)
        df['funding_z'] = df['funding_z'].fillna(0.0)
        
        # 3. ATR(14) sobre 1H (shift(1))
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['tr'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['atr'] = df['tr'].rolling(self.atr_period).mean().shift(1)
        
        # 4. SMA(20) y Extensión de Precio (shift(1))
        df['sma_exit'] = df['close'].shift(1).rolling(self.mean_w).mean()
        df['price_ext'] = ((df['close'].shift(1) - df['sma_exit']) / df['atr']).fillna(0.0)
        
        return df
