"""
Delta-Neutral Funding Rate Arbitrage Engine
Escanea y captura rendimientos pasivos libres de riesgo direccional explotando tasas de financiación extremas.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class FundingRateArbitrageScanner:
    """Escáner y Calculador Cuantitativo de Rendimiento por Funding Rate."""
    
    def __init__(self, min_annualized_rate_pct: float = 20.0):
        self.min_annualized_rate_pct = min_annualized_rate_pct
        
    def analyze_funding_rates(self, premium_index_data: List[Dict]) -> pd.DataFrame:
        """
        Procesa los datos de tasas de financiación de Binance Futures.
        
        Args:
            premium_index_data: Lista de dicts retornada por client.funding_rate o premium_index.
            
        Returns:
            pd.DataFrame ordenado por Tasa Anualizada (APR).
        """
        records = []
        for item in premium_index_data:
            symbol = item.get('symbol', '')
            if not symbol.endswith('USDT'):
                continue
                
            last_funding_rate = float(item.get('lastFundingRate', 0.0))
            mark_price = float(item.get('markPrice', 0.0))
            
            # Tasa cada 8h -> 3 pagos diarios -> 365 días
            daily_rate_pct = last_funding_rate * 3 * 100.0
            apr_pct = daily_rate_pct * 365.0
            
            records.append({
                'symbol': symbol,
                'mark_price': mark_price,
                'funding_rate_8h_pct': round(last_funding_rate * 100.0, 4),
                'daily_yield_pct': round(daily_rate_pct, 4),
                'apr_pct': round(apr_pct, 2),
                'next_funding_time': item.get('nextFundingTime', 0)
            })
            
        df = pd.DataFrame(records)
        if df.empty:
            return df
            
        return df.sort_values(by='apr_pct', ascending=False).reset_index(drop=True)

    def get_top_arbitrage_opportunities(self, df_funding: pd.DataFrame, top_n: int = 5) -> Dict[str, pd.DataFrame]:
        """
        Retorna las mejores oportunidades de arbitraje positivo (Long Spot/Short Perp) 
        y negativo (Long Perp/Short Benchmark).
        """
        if df_funding.empty:
            return {'positive_arbitrage': pd.DataFrame(), 'negative_arbitrage': pd.DataFrame()}
            
        pos_opps = df_funding[df_funding['apr_pct'] >= self.min_annualized_rate_pct].head(top_n)
        neg_opps = df_funding[df_funding['apr_pct'] <= -self.min_annualized_rate_pct].head(top_n)
        
        return {
            'positive_arbitrage': pos_opps,
            'negative_arbitrage': neg_opps
        }
