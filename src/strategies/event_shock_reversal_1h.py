"""
Event Shock Reversal 1H Strategy (EVENT_SHOCK_PROXY)
STRATEGY_FAMILY = EVENT_SHOCK_REVERSAL_1H

Lógica:
- Usa velas OHLCV 1H existentes.
- Retorno 1-barra: R[t] = Close[t] / Close[t-1] - 1.
- Z-score rolling de retorno y Z-score rolling de volumen (ventana W=120).
- Long: Shock bajista extremo (Z_ret <= -return_z) + Volumen extremo (Z_vol >= volume_z).
- Short: Shock alcista extremo (Z_ret >= return_z) + Volumen extremo (Z_vol >= volume_z).
- Ejecución en la siguiente vela 1h (open) sin look-ahead bias.
- Salida por recuperación hacia la media (SMA 20) o Time-Stop máximo de 4 velas (4h).
- Sin RSI, MACD, ATR, Bollinger, funding ni OI.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

class EventShockReversal1H:
    """Motor de Reversión tras Shock de Evento (Proxy OHLCV 1H)."""
    
    def __init__(
        self,
        return_z_threshold: float = 2.0,
        volume_z_threshold: float = 1.5,
        rolling_window: int = 120,
        mean_exit_window: int = 20,
        max_holding_bars: int = 4
    ):
        self.return_z = return_z_threshold
        self.volume_z = volume_z_threshold
        self.w = rolling_window
        self.mean_w = mean_exit_window
        self.max_holding_bars = max_holding_bars

    def compute_indicators(self, df_1h: pd.DataFrame) -> pd.DataFrame:
        """Calcula Z-scores rolling de retorno y volumen sin sesgo de anticipación."""
        df = df_1h.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 1. Retorno de 1 barra
        df['ret'] = df['close'].pct_change()
        
        # 2. Rolling Z-Score de Retorno (shift(1) para medir distribución previa)
        ret_mean = df['ret'].shift(1).rolling(self.w).mean()
        ret_std = df['ret'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_ret'] = ((df['ret'] - ret_mean) / ret_std).fillna(0.0)
        
        # 3. Rolling Z-Score de Volumen (shift(1) para distribución previa)
        vol_mean = df['volume'].shift(1).rolling(self.w).mean()
        vol_std = df['volume'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_vol'] = ((df['volume'] - vol_mean) / vol_std).fillna(0.0)
        
        # 4. Media de salida (SMA 20 de close, shift(1))
        df['sma_exit'] = df['close'].shift(1).rolling(self.mean_w).mean()
        
        return df
