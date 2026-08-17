"""
Smart Portfolio Matrix Module (Top 1% Alpha Concentration Matrix)
Poda los activos de alta fricción negativa (WIF, ETC, XRP, ADA-Grid) y concentra el capital
en los generadores de Alpha con ratio de beneficio/fricción > 5.0 (AVAX, LINK, SUI, BNB, SOL, BTC, ARB, DOGE, FIL).
"""

import pandas as pd
from typing import Dict, Tuple, Optional
from src.strategies.scientific_regime_filter import ScientificRegimeFilter
from src.strategies.ema_cross_protector import EMACrossProtectorStrategy
from src.strategies.macd_scalper import MACDStochasticScalperStrategy
from src.strategies.vwap_reversion import VWAPMeanReversionStrategy

class SmartPortfolioMatrix:
    """Matriz Cuántica Optimizada de Alta Eficiencia y Baja Fricción."""
    
    def __init__(self):
        self.regime_filter = ScientificRegimeFilter(er_period=14, atr_period=14)
        
        # Estrategias calibradas para alta ganancia neta (Fee hurdle > 5x)
        self.trending_strategies = {
            'PRIMARY': ('EMA_Cross_Protector', EMACrossProtectorStrategy()),
            'SCALP': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.028, stop_loss_pct=0.011, profit_lock_pct=0.012))
        }
        
        self.ranging_strategies = {
            'PRIMARY': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5, tp_z_score=0.0, sl_z_score=3.5, stop_loss_pct=0.011, profit_lock_pct=0.012))
        }
        
        # Mapeo concentrado en los Top Generadores de Alpha
        self.primary_matrix = {
            'AVAXUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5, profit_lock_pct=0.012)),
            'LINKUSDT': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.028, stop_loss_pct=0.011)),
            'SUIUSDT': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.028, stop_loss_pct=0.011)),
            'BNBUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.4)),
            'SOLUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5)),
            'BTCUSDT': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.025, stop_loss_pct=0.010)),
            'DOGEUSDT': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.028, stop_loss_pct=0.011)),
            'ARBUSDT': ('MACD_Scalper', MACDStochasticScalperStrategy(take_profit_pct=0.028, stop_loss_pct=0.011)),
            'APTUSDT': ('EMA_Cross_Protector', EMACrossProtectorStrategy()),
            'FILUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5)),
            'NEARUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5)),
            'UNIUSDT': ('VWAP_Reversion', VWAPMeanReversionStrategy(entry_z_score=2.5)),
            'DOTUSDT': ('EMA_Cross_Protector', EMACrossProtectorStrategy()),
            'OPUSDT': ('EMA_Cross_Protector', EMACrossProtectorStrategy())
        }
        
    def get_strategy_for_symbol(self, symbol: str, df: Optional[pd.DataFrame] = None) -> Tuple[str, object]:
        """
        Selecciona dinámicamente la estrategia usando la Razón de Eficiencia ER si df está disponible.
        """
        formatted_symbol = symbol.replace('/', '').upper()
        
        if df is not None and len(df) >= 30:
            regime, metrics = self.regime_filter.detect_regime(df)
            
            if regime == 'RANGING':
                return self.ranging_strategies['PRIMARY']
                
            elif regime == 'TRENDING':
                if formatted_symbol in ['SUIUSDT', 'DOGEUSDT', 'BTCUSDT', 'ARBUSDT', 'LINKUSDT']:
                    return self.trending_strategies['SCALP']
                return self.trending_strategies['PRIMARY']
                
        # Estrategia primaria si no hay df o régimen neutral
        if formatted_symbol in self.primary_matrix:
            return self.primary_matrix[formatted_symbol]
            
        return ('EMA_Cross_Protector', EMACrossProtectorStrategy())
