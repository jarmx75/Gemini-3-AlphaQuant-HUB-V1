"""
Data Collector Module
Recolecta datos de mercado de exchanges usando CCXT.
Sin IA - determinista y eficiente para M2.
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
import logging
from typing import Optional, List
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollector:
    """Colector de datos de mercado usando CCXT."""
    
    def __init__(self, exchange_id: str = 'binance', sandbox: bool = True):
        """
        Inicializar colector de datos.
        
        Args:
            exchange_id: ID del exchange (binance, bybit, etc)
            sandbox: Usar sandbox/paper trading
        """
        self.exchange_id = exchange_id
        self.sandbox = sandbox
        
        # Configurar exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            'sandbox': sandbox,
        })
        
        logger.info(f"DataCollector inicializado para {exchange_id} (sandbox={sandbox})")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        since: Optional[int] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Obtener datos OHLCV (Open, High, Low, Close, Volume).
        
        Args:
            symbol: Par de trading (ej: 'BTC/USDT')
            timeframe: Timeframe (1m, 5m, 1h, 4h, 1d)
            since: Timestamp desde donde empezar
            limit: Número de velas a obtener
            
        Returns:
            DataFrame con datos OHLCV
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Obtenidos {len(df)} registros de {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo OHLCV de {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        """
        Obtener order book actual.
        
        Args:
            symbol: Par de trading
            limit: Profundidad del order book
            
        Returns:
            Dict con bids y asks
        """
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            logger.info(f"Order book obtenido para {symbol}")
            return order_book
        except Exception as e:
            logger.error(f"Error obteniendo order book de {symbol}: {e}")
            return {}
    
    def fetch_funding_rate(self, symbol: str) -> dict:
        """
        Obtener funding rate actual (para perpetual futures).
        
        Args:
            symbol: Par de trading
            
        Returns:
            Dict con información del funding rate
        """
        try:
            # CCXT tiene métodos específicos para funding rates
            if hasattr(self.exchange, 'fetch_funding_rate'):
                funding = self.exchange.fetch_funding_rate(symbol)
                logger.info(f"Funding rate obtenido para {symbol}: {funding}")
                return funding
            else:
                logger.warning(f"Exchange {self.exchange_id} no soporta fetch_funding_rate")
                return {}
        except Exception as e:
            logger.error(f"Error obteniendo funding rate de {symbol}: {e}")
            return {}
    
    def save_to_parquet(self, df: pd.DataFrame, path: str) -> bool:
        """
        Guardar DataFrame en formato Parquet (compresión eficiente).
        
        Args:
            df: DataFrame a guardar
            path: Ruta donde guardar
            
        Returns:
            True si exitoso, False si error
        """
        try:
            df.to_parquet(path, engine='pyarrow')
            logger.info(f"Datos guardados en {path} ({len(df)} registros)")
            return True
        except Exception as e:
            logger.error(f"Error guardando en Parquet: {e}")
            return False
    
    def load_from_parquet(self, path: str) -> pd.DataFrame:
        """
        Cargar DataFrame desde Parquet.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            DataFrame cargado
        """
        try:
            df = pd.read_parquet(path)
            logger.info(f"Datos cargados desde {path} ({len(df)} registros)")
            return df
        except Exception as e:
            logger.error(f"Error cargando desde Parquet: {e}")
            return pd.DataFrame()


class HistoricalDataDownloader:
    """Descargador de datos históricos."""
    
    def __init__(self, collector: DataCollector, output_dir: str = 'data/raw'):
        self.collector = collector
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download_historical_data(
        self,
        symbol: str,
        timeframe: str,
        days: int = 30,
        chunk_size: int = 1000
    ) -> str:
        """
        Descargar datos históricos en chunks.
        
        Args:
            symbol: Par de trading
            timeframe: Timeframe
            days: Días de datos históricos
            chunk_size: Tamaño de cada chunk
            
        Returns:
            Ruta del archivo guardado
        """
        all_data = []
        
        # Calcular timestamp inicial
        since = self.collector.exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
        
        logger.info(f"Descargando {days} días de datos para {symbol} ({timeframe})")
        
        while True:
            try:
                df = self.collector.fetch_ohlcv(symbol, timeframe, since, chunk_size)
                
                if df.empty:
                    break
                
                all_data.append(df)
                
                # Actualizar timestamp para el siguiente chunk
                since = int(df.index[-1].timestamp() * 1000) + 1
                
                # Rate limiting
                time.sleep(1)
                
                # Si obtuvimos menos datos que el límite, terminamos
                if len(df) < chunk_size:
                    break
                    
            except Exception as e:
                logger.error(f"Error en chunk: {e}")
                break
        
        if all_data:
            # Combinar todos los chunks
            final_df = pd.concat(all_data)
            final_df = final_df[~final_df.index.duplicated(keep='first')]
            final_df.sort_index(inplace=True)
            
            # Guardar en Parquet
            filename = f"{symbol.replace('/', '_')}_{timeframe}_{days}d.parquet"
            filepath = self.output_dir / filename
            
            self.collector.save_to_parquet(final_df, str(filepath))
            
            logger.info(f"Descarga completada: {len(final_df)} registros en {filepath}")
            return str(filepath)
        else:
            logger.error("No se pudieron obtener datos")
            return ""


def main():
    """Función principal para testing."""
    # Crear colector para Binance sandbox
    collector = DataCollector('binance', sandbox=True)
    
    # Descargar datos históricos de BTC/USDT
    downloader = HistoricalDataDownloader(collector)
    
    # Descargar 7 días de datos 1h
    filepath = downloader.download_historical_data(
        symbol='BTC/USDT',
        timeframe='1h',
        days=7
    )
    
    if filepath:
        # Cargar y verificar
        df = collector.load_from_parquet(filepath)
        print(f"\nResumen de datos descargados:")
        print(df.head())
        print(f"\nTotal registros: {len(df)}")
        print(f"Rango: {df.index.min()} a {df.index.max()}")


if __name__ == '__main__':
    main()
