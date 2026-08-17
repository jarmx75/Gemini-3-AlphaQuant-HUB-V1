#!/usr/bin/env python3
"""
Script para ejecutar backtests con datos reales de Binance.
"""

import sys
import pandas as pd
from pathlib import Path

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.grid_trading import GridTradingStrategy, create_grid_strategy_function
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_real_data(symbol: str, timeframe: str = '1h') -> pd.DataFrame:
    """
    Cargar datos reales descargados de Binance.
    
    Args:
        symbol: Símbolo (ej: 'BTC/USDT')
        timeframe: Timeframe
        
    Returns:
        DataFrame con datos OHLCV
    """
    filename = f"{symbol.replace('/', '_')}_{timeframe}_90d.parquet"
    filepath = Path('data/raw') / filename
    
    if not filepath.exists():
        logger.error(f"Archivo no encontrado: {filepath}")
        return pd.DataFrame()
    
    collector = DataCollector('binance', sandbox=False)
    df = collector.load_from_parquet(str(filepath))
    
    logger.info(f"Datos cargados: {symbol} - {len(df)} registros")
    logger.info(f"Rango: {df.index.min()} a {df.index.max()}")
    logger.info(f"Precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df


def run_grid_backtest_real_data(df: pd.DataFrame, symbol: str):
    """
    Ejecutar backtest de Grid Trading con datos reales.
    
    Args:
        df: DataFrame con datos OHLCV
        symbol: Símbolo del activo
    """
    logger.info(f"\nEjecutando backtest Grid Trading en {symbol}...")
    
    # Añadir indicadores
    df_with_indicators = add_all_indicators(df)
    
    # Crear estrategia de grid optimizada para datos reales
    grid_strategy = GridTradingStrategy(
        grid_size=0.01,       # 1% entre niveles (más amplio para datos reales)
        grid_levels=8,        # 8 niveles arriba y abajo
        position_size=0.001,  # Tamaño de posición
        atr_multiplier=1.0     # Ajuste moderado por volatilidad
    )
    
    strategy_func = create_grid_strategy_function(grid_strategy)
    
    # Ejecutar backtest
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.001,   # 0.1% por trade (fee estándar de Binance)
        slippage=0.0005   # 0.05% slippage
    )
    
    result = engine.run_backtest(
        data=df_with_indicators,
        strategy_func=strategy_func,
        strategy_name="Grid Trading (Real Data)",
        symbol=symbol
    )
    
    return result


def run_rsi_backtest_real_data(df: pd.DataFrame, symbol: str):
    """
    Ejecutar backtest de RSI + SMA con datos reales.
    
    Args:
        df: DataFrame con datos OHLCV
        symbol: Símbolo del activo
    """
    logger.info(f"\nEjecutando backtest RSI + SMA en {symbol}...")
    
    # Añadir indicadores
    df_with_indicators = add_all_indicators(df)
    
    # Estrategia RSI + SMA optimizada
    def rsi_sma_strategy(data: pd.DataFrame):
        """Estrategia optimizada para datos reales."""
        if len(data) < 50:
            return None
        
        latest = data.iloc[-1]
        
        # Condiciones más conservadoras
        rsi_oversold = latest['rsi'] < 25  # Más extremo
        rsi_overbought = latest['rsi'] > 75  # Más extremo
        sma_bullish = latest['sma_20'] > latest['sma_50']
        sma_bearish = latest['sma_20'] < latest['sma_50']
        
        if rsi_oversold and sma_bullish:
            return {'action': 'buy'}
        elif rsi_overbought and sma_bearish:
            return {'action': 'sell'}
        elif latest['rsi'] > 55:  # Take profit más conservador
            return {'action': 'close'}
        
        return None
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=df_with_indicators,
        strategy_func=rsi_sma_strategy,
        strategy_name="RSI + SMA (Real Data)",
        symbol=symbol
    )
    
    return result


def print_comparison(symbols_results: dict):
    """Imprimir comparación de resultados."""
    print("\n" + "="*80)
    print("COMPARACIÓN DE ESTRATEGIAS - DATOS REALES")
    print("="*80)
    
    for symbol, results in symbols_results.items():
        print(f"\n{symbol}:")
        print("-" * 80)
        print(f"{'Estrategia':<30} {'Trades':<8} {'Win Rate':<10} {'Retorno %':<12} {'Sharpe':<8} {'Max DD %':<10}")
        print("-" * 80)
        
        for strategy_name, result in results.items():
            return_pct = (result.total_pnl / result.initial_capital) * 100
            print(f"{strategy_name:<30} {result.total_trades:<8} {result.win_rate:<9.1f}% {return_pct:>11.2f}% {result.sharpe_ratio:>7.2f} {result.max_drawdown_pct:>9.2f}%")
    
    print("="*80)


def main():
    """Función principal."""
    print("="*80)
    print("BACKTESTING CON DATOS REALES DE BINANCE")
    print("="*80)
    print()
    
    # Símbolos a probar
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    
    # Resultados por símbolo
    symbols_results = {}
    
    for symbol in symbols:
        logger.info(f"\n{'='*60}")
        logger.info(f"Procesando {symbol}")
        logger.info(f"{'='*60}")
        
        # Cargar datos reales
        df = load_real_data(symbol)
        
        if df.empty:
            logger.warning(f"Saltando {symbol} - no hay datos")
            continue
        
        # Ejecutar backtests
        results = {}
        
        try:
            results['Grid Trading'] = run_grid_backtest_real_data(df, symbol)
        except Exception as e:
            logger.error(f"Error en Grid Trading para {symbol}: {e}")
        
        try:
            results['RSI + SMA'] = run_rsi_backtest_real_data(df, symbol)
        except Exception as e:
            logger.error(f"Error en RSI + SMA para {symbol}: {e}")
        
        symbols_results[symbol] = results
        
        # Imprimir resultados individuales
        for strategy_name, result in results.items():
            print(f"\n{symbol} - {strategy_name}:")
            print("-" * 60)
            print(f"Trades: {result.total_trades}")
            print(f"Win Rate: {result.win_rate:.1f}%")
            print(f"Total P&L: ${result.total_pnl:.2f}")
            print(f"Return: {(result.total_pnl / result.initial_capital) * 100:.2f}%")
            print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
    
    # Comparación final
    if symbols_results:
        print_comparison(symbols_results)
        
        # Guardar resultados
        results_dir = Path('backtests/results')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        summary_file = results_dir / f'real_data_summary_{timestamp}.txt'
        
        with open(summary_file, 'w') as f:
            f.write("BACKTEST RESULTS - REAL DATA\n")
            f.write("="*80 + "\n\n")
            
            for symbol, results in symbols_results.items():
                f.write(f"{symbol}\n")
                f.write("-"*80 + "\n")
                
                for strategy_name, result in results.items():
                    return_pct = (result.total_pnl / result.initial_capital) * 100
                    f.write(f"{strategy_name}:\n")
                    f.write(f"  Trades: {result.total_trades}\n")
                    f.write(f"  Win Rate: {result.win_rate:.1f}%\n")
                    f.write(f"  Return: {return_pct:.2f}%\n")
                    f.write(f"  Sharpe: {result.sharpe_ratio:.2f}\n")
                    f.write(f"  Max DD: {result.max_drawdown_pct:.2f}%\n")
                    f.write(f"  P&L: ${result.total_pnl:.2f}\n\n")
        
        logger.info(f"Resumen guardado en: {summary_file}")
    
    logger.info("Backtesting con datos reales completado")


if __name__ == '__main__':
    main()
