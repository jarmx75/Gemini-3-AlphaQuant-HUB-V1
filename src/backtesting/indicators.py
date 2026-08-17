"""
Technical Indicators Module
Indicadores técnicos básicos para análisis de mercado.
Sin IA - cálculos matemáticos deterministas.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional

class TechnicalIndicators:
    """Clase con indicadores técnicos estándar."""
    
    @staticmethod
    def sma(data: pd.Series, window: int) -> pd.Series:
        """
        Simple Moving Average.
        
        Args:
            data: Serie de precios
            window: Ventana del promedio
            
        Returns:
            Serie con SMA
        """
        return data.rolling(window=window).mean()
    
    @staticmethod
    def ema(data: pd.Series, window: int) -> pd.Series:
        """
        Exponential Moving Average.
        
        Args:
            data: Serie de precios
            window: Ventana del promedio
            
        Returns:
            Serie con EMA
        """
        return data.ewm(span=window, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, window: int = 14) -> pd.Series:
        """
        Relative Strength Index.
        
        Args:
            data: Serie de precios
            window: Ventana para cálculo (default 14)
            
        Returns:
            Serie con RSI (0-100)
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Moving Average Convergence Divergence.
        
        Args:
            data: Serie de precios
            fast: Período rápido (default 12)
            slow: Período lento (default 26)
            signal: Período de señal (default 9)
            
        Returns:
            Tuple (MACD line, Signal line, Histogram)
        """
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, window: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.
        
        Args:
            data: Serie de precios
            window: Ventana para SMA (default 20)
            std_dev: Desviaciones estándar (default 2)
            
        Returns:
            Tuple (Upper band, Middle band, Lower band)
        """
        sma = TechnicalIndicators.sma(data, window)
        std = data.rolling(window=window).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """
        Average True Range - medida de volatilidad.
        
        Args:
            high: Serie de precios máximos
            low: Serie de precios mínimos
            close: Serie de precios de cierre
            window: Ventana para cálculo (default 14)
            
        Returns:
            Serie con ATR
        """
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=window).mean()
        
        return atr
    
    @staticmethod
    def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, 
                            k_window: int = 14, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator.
        
        Args:
            high: Serie de precios máximos
            low: Serie de precios mínimos
            close: Serie de precios de cierre
            k_window: Ventana para %K (default 14)
            d_window: Ventana para %D (default 3)
            
        Returns:
            Tuple (%K, %D)
        """
        lowest_low = low.rolling(window=k_window).min()
        highest_high = high.rolling(window=k_window).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_window).mean()
        
        return k_percent, d_percent
    
    @staticmethod
    def volatility(data: pd.Series, window: int = 20) -> pd.Series:
        """
        Volatilidad histórica (desviación estándar de retornos).
        
        Args:
            data: Serie de precios
            window: Ventana para cálculo (default 20)
            
        Returns:
            Serie con volatilidad
        """
        returns = data.pct_change()
        volatility = returns.rolling(window=window).std() * np.sqrt(252)  # Annualizada
        
        return volatility
    
    @staticmethod
    def z_score(data: pd.Series, window: int = 20) -> pd.Series:
        """
        Z-Score - cuántas desviaciones estándar está un valor de su media.
        Útil para statistical arbitrage.
        
        Args:
            data: Serie de precios
            window: Ventana para cálculo (default 20)
            
        Returns:
            Serie con Z-Score
        """
        rolling_mean = data.rolling(window=window).mean()
        rolling_std = data.rolling(window=window).std()
        
        z_score = (data - rolling_mean) / rolling_std
        
        return z_score
    
    @staticmethod
    def correlation(series1: pd.Series, series2: pd.Series, window: int = 30) -> pd.Series:
        """
        Correlación rolling entre dos series.
        Útil para pairs trading.
        
        Args:
            series1: Primera serie de precios
            series2: Segunda serie de precios
            window: Ventana para cálculo (default 30)
            
        Returns:
            Serie con correlación
        """
        return series1.rolling(window=window).corr(series2)


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añadir todos los indicadores a un DataFrame OHLCV.
    
    Args:
        df: DataFrame con columnas open, high, low, close, volume
        
    Returns:
        DataFrame con indicadores añadidos
    """
    df = df.copy()
    
    # Moving averages
    df['sma_20'] = TechnicalIndicators.sma(df['close'], 20)
    df['sma_50'] = TechnicalIndicators.sma(df['close'], 50)
    df['ema_9'] = TechnicalIndicators.ema(df['close'], 9)
    df['ema_12'] = TechnicalIndicators.ema(df['close'], 12)
    df['ema_21'] = TechnicalIndicators.ema(df['close'], 21)
    df['ema_26'] = TechnicalIndicators.ema(df['close'], 26)
    df['ema_200'] = TechnicalIndicators.ema(df['close'], 200)
    
    # RSI
    df['rsi'] = TechnicalIndicators.rsi(df['close'], 14)
    
    # MACD
    macd, signal, hist = TechnicalIndicators.macd(df['close'])
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_histogram'] = hist
    
    # Bollinger Bands
    upper, middle, lower = TechnicalIndicators.bollinger_bands(df['close'])
    df['bb_upper'] = upper
    df['bb_middle'] = middle
    df['bb_lower'] = lower
    
    # ATR
    df['atr'] = TechnicalIndicators.atr(df['high'], df['low'], df['close'])
    
    # Stochastic
    k, d = TechnicalIndicators.stochastic_oscillator(df['high'], df['low'], df['close'])
    df['stoch_k'] = k
    df['stoch_d'] = d
    
    # Volatilidad
    df['volatility'] = TechnicalIndicators.volatility(df['close'])
    
    # Z-Score
    df['z_score'] = TechnicalIndicators.z_score(df['close'])
    
    return df


def main():
    """Función principal para testing."""
    import pandas as pd
    import numpy as np
    
    # Crear datos de prueba
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    
    # Simular movimiento de precio
    price = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price + np.random.randn(100) * 50,
        'high': price + np.abs(np.random.randn(100) * 100),
        'low': price - np.abs(np.random.randn(100) * 100),
        'close': price,
        'volume': np.random.randint(100, 1000, 100)
    })
    df.set_index('timestamp', inplace=True)
    
    # Añadir indicadores
    df_with_indicators = add_all_indicators(df)
    
    print("DataFrame con indicadores técnicos:")
    print(df_with_indicators.tail())
    
    print("\nEstadísticas de RSI:")
    print(df_with_indicators['rsi'].describe())
    
    print("\nEstadísticas de ATR:")
    print(df_with_indicators['atr'].describe())


if __name__ == '__main__':
    main()
