"""
Funding Momentum 1H Strategy
STRATEGY_FAMILY = FUNDING_MOMENTUM_1H

Lógica:
- Universo: BTCUSDT, ETHUSDT.
- Velas OHLCV 1H + Funding Rate 8H.
- Alineación temporal estricta:
  - El funding publicado en T_funding (00:00, 08:00, 16:00 UTC) solo se utiliza en ese momento.
  - La señal se evalúa en el cierre de 1H de esa hora.
  - La entrada se ejecuta en la siguiente vela 1H (Open) sin look-ahead.
- Features:
  1) Funding Z-score (W=90 observaciones de 8h = 30 días, shift(1)).
  2) Retorno de precio a N horas: R_N[t] = Close[t] / Close[t-N] - 1 (shift(1)).
- Señal:
  - Long: FundingZ >= threshold AND return_N > 0 (Funding alcista + Momentum alcista)
  - Short: FundingZ <= -threshold AND return_N < 0 (Funding bajista + Momentum bajista)
- Salidas:
  - Salida cuando Funding vuelve a neutralidad (<=0 para Long, >=0 para Short)
    O cuando el momentum de precio cambia de signo (<0 para Long, >0 para Short).
  - Time-stop máximo de 24 velas 1H (24h).
  - Stop de emergencia 3.0%.
- Cero RSI, MACD, ATR, OI, taker ni volumen.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

class FundingMomentum1H:
    """Motor de Trading de Momentum de Funding Rate 1H."""
    
    def __init__(
        self,
        funding_z_threshold: float = 1.0,
        momentum_hours: int = 12,
        funding_window: int = 90,
        max_holding_bars: int = 24,
        emergency_stop_pct: float = 0.03
    ):
        self.funding_z = funding_z_threshold
        self.mom_n = momentum_hours
        self.f_w = funding_window
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
        
        # Calcular Funding Z-Score sobre la serie de 8h (shift(1))
        f_mean = dff['fundingRate'].shift(1).rolling(self.f_w).mean()
        f_std = dff['fundingRate'].shift(1).rolling(self.f_w).std().replace(0, np.nan)
        dff['funding_z'] = ((dff['fundingRate'] - f_mean) / f_std).fillna(0.0)
        dff['is_funding_bar'] = True
        
        # 2. Alinear con OHLCV 1H
        dff = dff.rename(columns={'fundingTime': 'timestamp'})
        df = pd.merge(df, dff[['timestamp', 'fundingRate', 'funding_z', 'is_funding_bar']],
                      on='timestamp', how='left')
        df['is_funding_bar'] = df['is_funding_bar'].fillna(False)
        # Forward-fill el último Funding Z conocido para evaluación continua de salida
        df['funding_z_held'] = df['funding_z'].replace(0.0, np.nan).ffill().fillna(0.0)
        df['funding_z'] = df['funding_z'].fillna(0.0)
        
        # 3. Retorno de momentum a N horas (shift(1) estricto)
        df['mom_ret'] = df['close'].pct_change(self.mom_n).shift(1).fillna(0.0)
        
        return df
