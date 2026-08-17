#!/usr/bin/env python3
"""
Script para probar estrategias avanzadas con datos reales.
Funding Rate Arbitrage y Statistical Arbitrage.
"""

import sys
import pandas as pd
from pathlib import Path

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.funding_rate_arbitrage import FundingRateArbitrage, create_funding_strategy_function, simulate_funding_data
from src.strategies.statistical_arbitrage import StatisticalArbitrage, create_pairs_strategy_function
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_real_data(symbol: str) -> pd.DataFrame:
    """Cargar datos reales descargados."""
    filename = f"{symbol.replace('/', '_')}_1h_90d.parquet"
    filepath = Path('data/raw') / filename
    
    if not filepath.exists():
        logger.error(f"Archivo no encontrado: {filepath}")
        return pd.DataFrame()
    
    collector = DataCollector('binance', sandbox=False)
    df = collector.load_from_parquet(str(filepath))
    
    logger.info(f"Datos cargados: {symbol} - {len(df)} registros")
    return df


def test_funding_arbitrage(df: pd.DataFrame, symbol: str):
    """Probar estrategia de Funding Rate Arbitrage."""
    logger.info(f"\nTesting Funding Rate Arbitrage en {symbol}...")
    
    # Simular funding rates (ya que no tenemos datos reales)
    df_with_funding = simulate_funding_data(df)
    
    # Añadir indicadores
    df_with_indicators = add_all_indicators(df_with_funding)
    
    # Crear estrategia
    funding_strategy = FundingRateArbitrage(
        min_funding_rate=0.00005,  # 0.005% mínimo
        max_position_size=0.05,    # 5% del capital
        fee_rate=0.001,
        min_hold_time=8
    )
    
    strategy_func = create_funding_strategy_function(funding_strategy)
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=df_with_indicators,
        strategy_func=strategy_func,
        strategy_name="Funding Rate Arbitrage",
        symbol=symbol
    )
    
    return result


def test_statistical_arbitrage(df1: pd.DataFrame, df2: pd.DataFrame, symbol1: str, symbol2: str):
    """Probar estrategia de Statistical Arbitrage."""
    logger.info(f"\nTesting Statistical Arbitrage: {symbol1} / {symbol2}...")
    
    # Añadir indicadores
    df1_indicators = add_all_indicators(df1)
    df2_indicators = add_all_indicators(df2)
    
    # Crear estrategia
    pairs_strategy = StatisticalArbitrage(
        symbol1=symbol1,
        symbol2=symbol2,
        lookback_period=30,
        entry_threshold=2.0,
        exit_threshold=0.5,
        position_size=0.001
    )
    
    strategy_func = create_pairs_strategy_function(pairs_strategy, df2_indicators)
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=df1_indicators,
        strategy_func=strategy_func,
        strategy_name=f"Statistical Arbitrage ({symbol1}/{symbol2})",
        symbol=symbol1
    )
    
    return result


def main():
    """Función principal."""
    print("="*80)
    print("TESTING ESTRATEGIAS AVANZADAS - DATOS REALES")
    print("="*80)
    print()
    
    # Cargar datos reales
    btc_df = load_real_data('BTC/USDT')
    eth_df = load_real_data('ETH/USDT')
    bnb_df = load_real_data('BNB/USDT')
    
    if btc_df.empty or eth_df.empty:
        logger.error("No hay datos suficientes para testing")
        return
    
    results = {}
    
    # Probar Funding Rate Arbitrage
    try:
        logger.info("\n" + "="*60)
        logger.info("FUNDING RATE ARBITRAGE")
        logger.info("="*60)
        
        results['BTC_Funding'] = test_funding_arbitrage(btc_df, 'BTC/USDT')
        results['ETH_Funding'] = test_funding_arbitrage(eth_df, 'ETH/USDT')
        
    except Exception as e:
        logger.error(f"Error en Funding Rate Arbitrage: {e}")
    
    # Probar Statistical Arbitrage
    try:
        logger.info("\n" + "="*60)
        logger.info("STATISTICAL ARBITRAGE (PAIRS TRADING)")
        logger.info("="*60)
        
        results['BTC_ETH_Pairs'] = test_statistical_arbitrage(btc_df, eth_df, 'BTC/USDT', 'ETH/USDT')
        results['BTC_BNB_Pairs'] = test_statistical_arbitrage(btc_df, bnb_df, 'BTC/USDT', 'BNB/USDT')
        
    except Exception as e:
        logger.error(f"Error en Statistical Arbitrage: {e}")
    
    # Imprimir resumen
    print("\n" + "="*80)
    print("RESUMEN DE ESTRATEGIAS AVANZADAS")
    print("="*80)
    print(f"{'Estrategia':<35} {'Trades':<8} {'Win Rate':<10} {'Retorno %':<12} {'Sharpe':<8}")
    print("-"*80)
    
    for name, result in results.items():
        if result:
            return_pct = (result.total_pnl / result.initial_capital) * 100
            print(f"{name:<35} {result.total_trades:<8} {result.win_rate:<9.1f}% {return_pct:>11.2f}% {result.sharpe_ratio:>7.2f}")
    
    print("="*80)
    
    logger.info("Testing de estrategias avanzadas completado")


if __name__ == '__main__':
    main()
