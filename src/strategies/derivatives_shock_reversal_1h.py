"""
Derivatives Shock Reversal 1H Strategy (DERIVATIVES_SHOCK_REVERSAL)
STRATEGY_FAMILY = LIQUIDATION_DERIVATIVES_REVERSAL

Lógica:
- Universo: BTCUSDT, ETHUSDT.
- Velas 1H OHLCV + Open Interest 1H + Taker Flow 1H + Funding Rate 8H.
- Features:
  1) return_z: Z-score de retorno 1H (W=120).
  2) delta_OI_z: Z-score de cambio relativo de Open Interest (W=120).
  3) taker_z: Z-score de Taker Buy/Sell Volume Ratio (W=120).
  4) funding_z: Z-score de Funding Rate (W=120) como confirmación.
- Señal en t-1 ejecutada en open de t:
  - Long: Z_ret <= -return_z AND |Z_OI| >= OI_z AND Z_taker <= -taker_z AND Z_funding <= 0.0
  - Short: Z_ret >= return_z AND |Z_OI| >= OI_z AND Z_taker >= taker_z AND Z_funding >= 0.0
- Salidas: Reversión hacia SMA 20, Time-stop 4 velas (4h) y Stop de emergencia 3.0%.
- Cero look-ahead bias: Todas las variables se desfasan estrictamente con shift(1).
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

class DerivativesShockReversal1H:
    """Motor de Reversión tras Shock de Derivados (OI + Taker Flow + Funding)."""
    
    def __init__(
        self,
        return_z: float = 2.5,
        oi_z: float = 2.0,
        taker_z: float = 2.0,
        rolling_window: int = 120,
        mean_exit_window: int = 20,
        max_holding_bars: int = 4,
        emergency_stop_pct: float = 0.03
    ):
        self.return_z = return_z
        self.oi_z = oi_z
        self.taker_z = taker_z
        self.w = rolling_window
        self.mean_w = mean_exit_window
        self.max_holding_bars = max_holding_bars
        self.emergency_stop_pct = emergency_stop_pct

    def prepare_dataset(
        self,
        df_ohlcv: pd.DataFrame,
        df_metrics: pd.DataFrame,
        df_funding: pd.DataFrame
    ) -> pd.DataFrame:
        """Fusiona y alinea las series temporales sin sesgo de anticipación."""
        df = df_ohlcv.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 1. Alinear Métricas 1H (Open Interest & Taker Ratio)
        df_m = df_metrics.copy()
        df_m['create_time'] = pd.to_datetime(df_m['create_time'])
        df_m = df_m.rename(columns={'create_time': 'timestamp'}).sort_values('timestamp')
        
        df = pd.merge_asof(df, df_m[['timestamp', 'sum_open_interest', 'sum_taker_long_short_vol_ratio']],
                           on='timestamp', direction='backward')
        
        # 2. Alinear Funding Rate 8H (Forward-fill del último funding publicado)
        df_f = df_funding.copy()
        df_f['fundingTime'] = pd.to_datetime(df_f['fundingTime'])
        df_f = df_f.rename(columns={'fundingTime': 'timestamp'}).sort_values('timestamp')
        
        df = pd.merge_asof(df, df_f[['timestamp', 'fundingRate']],
                           on='timestamp', direction='backward')
        
        df['fundingRate'] = df['fundingRate'].fillna(0.0)
        df['sum_open_interest'] = df['sum_open_interest'].ffill()
        df['sum_taker_long_short_vol_ratio'] = df['sum_taker_long_short_vol_ratio'].fillna(1.0)
        
        # 3. Calcular Z-Scores sin look-ahead (shift(1) estricto)
        # Return Z
        df['ret'] = df['close'].pct_change()
        ret_m = df['ret'].shift(1).rolling(self.w).mean()
        ret_s = df['ret'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_ret'] = ((df['ret'] - ret_m) / ret_s).fillna(0.0)
        
        # Delta OI Z
        df['delta_oi'] = df['sum_open_interest'].pct_change()
        oi_m = df['delta_oi'].shift(1).rolling(self.w).mean()
        oi_s = df['delta_oi'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_oi'] = ((df['delta_oi'] - oi_m) / oi_s).fillna(0.0)
        
        # Taker Imbalance Z
        df['log_taker'] = np.log(df['sum_taker_long_short_vol_ratio'].clip(lower=0.01))
        taker_m = df['log_taker'].shift(1).rolling(self.w).mean()
        taker_s = df['log_taker'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_taker'] = ((df['log_taker'] - taker_m) / taker_s).fillna(0.0)
        
        # Funding Z
        fund_m = df['fundingRate'].shift(1).rolling(self.w).mean()
        fund_s = df['fundingRate'].shift(1).rolling(self.w).std().replace(0, np.nan)
        df['z_funding'] = ((df['fundingRate'] - fund_m) / fund_s).fillna(0.0)
        
        # Exit Reference (SMA 20 de close, shift(1))
        df['sma_exit'] = df['close'].shift(1).rolling(self.mean_w).mean()
        
        return df
