#!/usr/bin/env python3
"""
Script para descargar datos históricos reales de Binance.
Descarga datos OHLCV públicos sin necesidad de API keys.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector, HistoricalDataDownloader
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_binance_historical_data(
    symbol: str = 'BTC/USDT',
    timeframe: str = '1h',
    days: int = 90,
    output_dir: str = 'data/raw'
) -> str:
    """
    Descargar datos históricos de Binance.
    
    Args:
        symbol: Par de trading (ej: 'BTC/USDT')
        timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        days: Días de datos históricos a descargar
        output_dir: Directorio donde guardar los datos
        
    Returns:
        Ruta del archivo descargado
    """
    logger.info(f"Descargando datos de {symbol} ({timeframe}) - últimos {days} días")
    
    # Crear colector (sin API keys para datos públicos)
    collector = DataCollector('binance', sandbox=False)
    
    # Crear downloader
    downloader = HistoricalDataDownloader(collector, output_dir=output_dir)
    
    # Descargar datos
    filepath = downloader.download_historical_data(
        symbol=symbol,
        timeframe=timeframe,
        days=days
    )
    
    if filepath:
        logger.info(f"Datos descargados exitosamente: {filepath}")
        
        # Verificar datos
        df = collector.load_from_parquet(filepath)
        logger.info(f"Registros descargados: {len(df)}")
        logger.info(f"Rango de fechas: {df.index.min()} a {df.index.max()}")
        logger.info(f"Rango de precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return filepath
    else:
        logger.error("Error descargando datos")
        return ""


def download_multiple_symbols(
    symbols: list,
    timeframe: str = '1h',
    days: int = 90
) -> dict:
    """
    Descargar datos de múltiples símbolos.
    
    Args:
        symbols: Lista de símbolos (ej: ['BTC/USDT', 'ETH/USDT'])
        timeframe: Timeframe
        days: Días de datos
        
    Returns:
        Dict con rutas de archivos descargados
    """
    results = {}
    
    for symbol in symbols:
        logger.info(f"\nProcesando {symbol}...")
        try:
            filepath = download_binance_historical_data(symbol, timeframe, days)
            results[symbol] = filepath
            
            # Pequeña pausa para respetar rate limits
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error descargando {symbol}: {e}")
            results[symbol] = ""
    
    return results


def main():
    """Función principal."""
    print("="*60)
    print("DESCARGA DE DATOS HISTÓRICOS DE BINANCE")
    print("="*60)
    print()
    
    # Configuración de 30 activos descorrelacionados
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'LTC/USDT',
        'WIF/USDT', 'LINK/USDT', 'AAVE/USDT', 'ADA/USDT', 'DOT/USDT',
        'POL/USDT', 'AVAX/USDT', 'ATOM/USDT', 'NEAR/USDT', 'INJ/USDT',
        'APT/USDT', 'SUI/USDT', 'PEPE/USDT', 'DOGE/USDT', 'SHIB/USDT',
        'OP/USDT', 'ARB/USDT', 'TIA/USDT', 'FET/USDT', 'FLOKI/USDT',
        'BNB/USDT', 'UNI/USDT', 'FIL/USDT', 'ETC/USDT'
    ]
    timeframes = ['1h']
    days = 90  # 3 meses de datos

    logger.info(f"Configuración:")
    logger.info(f"  Símbolos ({len(symbols)}): {symbols}")
    logger.info(f"  Timeframes: {timeframes}")
    logger.info(f"  Días: {days}")
    logger.info(f"  Directorio: data/raw")
    
    results = {}
    for tf in timeframes:
        logger.info(f"\n--- DESCARGANDO TIMEFRAME {tf} ---")
        tf_results = download_multiple_symbols(symbols, tf, days)
        results.update(tf_results)
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE DESCARGA")
    print("="*60)
    
    successful = sum(1 for filepath in results.values() if filepath)
    total = len(results)
    
    print(f"Exitosos: {successful}/{total}")
    print()
    
    for symbol, filepath in results.items():
        status = "✓" if filepath else "✗"
        print(f"{status} {symbol}: {filepath if filepath else 'FALLÓ'}")
    
    print("="*60)
    
    if successful > 0:
        logger.info("Descarga completada exitosamente")
        logger.info("Los datos están listos para backtesting")
    else:
        logger.error("No se pudo descargar ningún dato")


if __name__ == '__main__':
    main()
