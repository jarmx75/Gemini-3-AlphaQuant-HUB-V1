#!/usr/bin/env python3
"""
Script principal para ejecutar backtests.
Combina data collection, indicadores y estrategias.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector, HistoricalDataDownloader
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.grid_trading import GridTradingStrategy, create_grid_strategy_function
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_data(days: int = 30) -> pd.DataFrame:
    """
    Generar datos de prueba para backtesting.
    Simula un mercado lateral con volatilidad realista.
    
    Args:
        days: Días de datos a generar
        
    Returns:
        DataFrame con datos OHLCV
    """
    logger.info(f"Generando {days} días de datos de prueba...")
    
    np.random.seed(42)
    periods = days * 24  # Datos horarios
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
    
    # Simular mercado lateral con más volatilidad para testing
    base_price = 50000
    noise = np.random.randn(periods) * 250  # Más volatilidad
    mean_reversion = -0.02 * np.cumsum(noise)  # Menor fuerza de retorno a la media
    trend = np.linspace(0, 3000, periods) * 0.3  # Ligera tendencia alcista
    
    # Añadir algunos movimientos más grandes para activar el grid
    big_moves = np.zeros(periods)
    for i in range(10, periods, 50):  # Cada 50 horas, un movimiento grande
        big_moves[i:i+5] = np.random.randn(5) * 500
    
    price = base_price + noise + mean_reversion + trend + big_moves
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price + np.random.randn(periods) * 50,
        'high': price + np.abs(np.random.randn(periods) * 150),
        'low': price - np.abs(np.random.randn(periods) * 150),
        'close': price,
        'volume': np.random.randint(100, 1000, periods)
    })
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Datos generados: {len(df)} registros")
    logger.info(f"Rango de precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df


def run_grid_trading_backtest(data: pd.DataFrame):
    """
    Ejecutar backtest de estrategia de Grid Trading.
    
    Args:
        data: DataFrame con datos OHLCV
    """
    logger.info("Iniciando backtest de Grid Trading...")
    
    # Añadir indicadores técnicos
    logger.info("Calculando indicadores técnicos...")
    data_with_indicators = add_all_indicators(data)
    
    # Crear estrategia de grid más agresiva para testing
    grid_strategy = GridTradingStrategy(
        grid_size=0.005,      # 0.5% entre niveles
        grid_levels=10,       # 10 niveles arriba y abajo
        position_size=0.0005,  # Tamaño de posición
        atr_multiplier=0.5     # Menor ajuste por volatilidad
    )
    
    # Crear función de estrategia compatible
    strategy_func = create_grid_strategy_function(grid_strategy)
    
    # Ejecutar backtest
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.001,   # 0.1% por trade
        slippage=0.0005   # 0.05% slippage
    )
    
    result = engine.run_backtest(
        data=data_with_indicators,
        strategy_func=strategy_func,
        strategy_name="Grid Trading Strategy",
        symbol="BTC/USDT"
    )
    
    # Imprimir resultados
    engine.print_results(result)
    
    # Guardar resultados
    results_dir = Path('backtests/results')
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / f'grid_trading_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    with open(results_file, 'w') as f:
        f.write(f"BACKTEST RESULTS: Grid Trading Strategy\n")
        f.write(f"="*50 + "\n")
        f.write(f"Symbol: {result.symbol}\n")
        f.write(f"Period: {result.start_date} to {result.end_date}\n")
        f.write(f"\nTrading Metrics:\n")
        f.write(f"  Total Trades: {result.total_trades}\n")
        f.write(f"  Winning Trades: {result.winning_trades}\n")
        f.write(f"  Losing Trades: {result.losing_trades}\n")
        f.write(f"  Win Rate: {result.win_rate:.2f}%\n")
        f.write(f"\nFinancial Metrics:\n")
        f.write(f"  Total P&L: ${result.total_pnl:.2f}\n")
        f.write(f"  Total Fees: ${result.total_fees:.2f}\n")
        f.write(f"  Final Capital: ${result.initial_capital + result.total_pnl:.2f}\n")
        f.write(f"  Return: {((result.total_pnl / result.initial_capital) * 100):.2f}%\n")
        f.write(f"\nRisk Metrics:\n")
        f.write(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%\n")
        f.write(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}\n")
        f.write(f"  Profit Factor: {result.profit_factor:.2f}\n")
    
    logger.info(f"Resultados guardados en: {results_file}")
    
    return result


def run_rsi_strategy_backtest(data: pd.DataFrame):
    """
    Ejecutar backtest de estrategia simple RSI + SMA.
    
    Args:
        data: DataFrame con datos OHLCV
    """
    logger.info("Iniciando backtest de RSI + SMA Strategy...")
    
    # Añadir indicadores
    data_with_indicators = add_all_indicators(data)
    
    # Definir estrategia
    def rsi_sma_strategy(data: pd.DataFrame):
        """Estrategia: RSI + SMA crossover."""
        if len(data) < 50:
            return None
        
        latest = data.iloc[-1]
        
        rsi_oversold = latest['rsi'] < 30
        rsi_overbought = latest['rsi'] > 70
        sma_bullish = latest['sma_20'] > latest['sma_50']
        sma_bearish = latest['sma_20'] < latest['sma_50']
        
        if rsi_oversold and sma_bullish:
            return {'action': 'buy'}
        elif rsi_overbought and sma_bearish:
            return {'action': 'sell'}
        elif latest['rsi'] > 50:
            return {'action': 'close'}
        
        return None
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=data_with_indicators,
        strategy_func=rsi_sma_strategy,
        strategy_name="RSI + SMA Strategy",
        symbol="BTC/USDT"
    )
    
    engine.print_results(result)
    
    return result


def main():
    """Función principal."""
    print("="*60)
    print("SISTEMA DE BACKTESTING - TRADING AUTÓNOMO")
    print("="*60)
    print()
    
    # Generar datos de prueba
    data = generate_test_data(days=30)
    
    # Ejecutar backtests
    print("\n--- Opción 1: Grid Trading Strategy ---")
    grid_result = run_grid_trading_backtest(data)
    
    print("\n--- Opción 2: RSI + SMA Strategy ---")
    rsi_result = run_rsi_strategy_backtest(data)
    
    # Comparación
    print("\n" + "="*60)
    print("COMPARACIÓN DE ESTRATEGIAS")
    print("="*60)
    print(f"{'Estrategia':<25} {'Retorno %':<12} {'Sharpe':<10} {'Max DD %':<12}")
    print("-"*60)
    print(f"{'Grid Trading':<25} {((grid_result.total_pnl / grid_result.initial_capital) * 100):>11.2f}% {grid_result.sharpe_ratio:>9.2f} {grid_result.max_drawdown_pct:>11.2f}%")
    print(f"{'RSI + SMA':<25} {((rsi_result.total_pnl / rsi_result.initial_capital) * 100):>11.2f}% {rsi_result.sharpe_ratio:>9.2f} {rsi_result.max_drawdown_pct:>11.2f}%")
    print("="*60)
    
    logger.info("Backtests completados exitosamente")


if __name__ == '__main__':
    main()
