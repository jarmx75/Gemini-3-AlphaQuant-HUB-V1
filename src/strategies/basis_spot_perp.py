import pandas as pd
import numpy as np

class BasisSpotPerpStrategy:
    """
    Estrategia de convergencia de Basis entre Spot y Perpetual Futures.
    STRATEGY_FAMILY = BASIS_SPOT_PERP
    """
    
    def __init__(self, entry_z: float = 2.0, max_holding_bars: int = 72, basis_window: int = 72):
        self.entry_z = entry_z
        self.max_holding_bars = max_holding_bars
        self.basis_window = basis_window

    def compute_indicators(self, df_spot: pd.DataFrame, df_perp: pd.DataFrame) -> pd.DataFrame:
        """
        Mergea ambos DataFrames y calcula el z-score del basis.
        Se asume que los timestamps están alineados (frecuencia 1H).
        """
        # Rename closes to avoid collision
        df_spot = df_spot[['timestamp', 'close']].rename(columns={'close': 'spot_close'})
        df_perp = df_perp[['timestamp', 'close']].rename(columns={'close': 'perp_close'})
        
        # Merge on timestamp
        df = pd.merge(df_spot, df_perp, on='timestamp', how='inner').sort_values('timestamp').reset_index(drop=True)
        
        # Calcular basis = (perp - spot) / spot
        df['basis_pct'] = (df['perp_close'] - df['spot_close']) / df['spot_close']
        
        # Calcular Z-score usando una ventana móvil desplazada 1 vela para evitar look-ahead 
        # (aunque la ejecución será a la siguiente vela de todas formas)
        rolling_mean = df['basis_pct'].rolling(window=self.basis_window).mean()
        rolling_std = df['basis_pct'].rolling(window=self.basis_window).std()
        
        df['basis_z'] = (df['basis_pct'] - rolling_mean) / rolling_std
        
        return df
