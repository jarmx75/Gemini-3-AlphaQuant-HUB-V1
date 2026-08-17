#!/usr/bin/env python3
"""
Script simplificado para probar estrategias avanzadas.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.funding_rate_arbitrage import FundingRateArbitrage, create_funding_strategy_function, simulate_funding_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_real_data(symbol: str) -> pd.DataFrame:
    """Cargar datos reales."""
    filename = f"{symbol.replace('/', '_')}_1h_90d.parquet"
    filepath = Path('data/raw') / filename
    
    if not filepath.exists():
        return pd.DataFrame()
    
    collector = DataCollector('binance', sandbox=False)
    return collector.load_from_parquet(str(filepath))


def test_funding_arbitrage(df: pd.DataFrame, symbol: str):
    """Probar Funding Rate Arbitrage."""
    logger.info(f"Testing Funding Rate Arbitrage en {symbol}...")
    
    # Usar solo los últimos 500 registros para testing rápido
    df = df.tail(500).copy()
    
    # Simular funding rates
    df_with_funding = simulate_funding_data(df)
    df_with_indicators = add_all_indicators(df_with_funding)
    
    # Estrategia muy agresiva para testing
    funding_strategy = FundingRateArbitrage(
        min_funding_rate=0.00001,  # Muy bajo para generar señales
        max_position_size=0.15,
        fee_rate=0.001,
        min_hold_time=2  # 2 horas mínimo
    )
    
    strategy_func = create_funding_strategy_function(funding_strategy)
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=df_with_indicators,
        strategy_func=strategy_func,
        strategy_name="Funding Rate Arbitrage",
        symbol=symbol
    )
    
    return result


def main():
    """Función principal."""
    print("="*60)
    print("TESTING ESTRATEGIAS AVANZADAS (SIMPLIFICADO)")
    print("="*60)
    
    # Cargar datos
    btc_df = load_real_data('BTC/USDT')
    
    if btc_df.empty:
        logger.error("No hay datos")
        return
    
    # Probar solo Funding Rate Arbitrage (más rápido)
    try:
        result = test_funding_arbitrage(btc_df, 'BTC/USDT')
        
        print(f"\nResultados Funding Rate Arbitrage:")
        print(f"Trades: {result.total_trades}")
        print(f"Win Rate: {result.win_rate:.1f}%")
        print(f"Return: {(result.total_pnl / result.initial_capital) * 100:.2f}%")
        print(f"Sharpe: {result.sharpe_ratio:.2f}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
