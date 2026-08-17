"""
Statistical Arbitrage (Pairs Trading) Strategy Module
Estrategia de arbitraje estadístico basada en cointegración.
Sin IA - reglas matemáticas deterministas.

Concepto:
- Identificar pares de activos que históricamente se mueven juntos (cointegrados)
- Cuando la relación se rompe (spread amplio), apostar a la reversión a la media
- Long del activo subvaluado + Short del activo sobrevaluado
- Delta neutral - no depende de la dirección del mercado
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PairPosition:
    """Posición de pairs trading."""
    symbol1: str
    symbol2: str
    entry_time: datetime
    symbol1_quantity: float
    symbol2_quantity: float
    symbol1_entry_price: float
    symbol2_entry_price: float
    entry_z_score: float
    status: str = 'open'  # 'open', 'closed'
    exit_time: Optional[datetime] = None
    total_pnl: float = 0.0
    fees_paid: float = 0.0


class StatisticalArbitrage:
    """
    Estrategia de Statistical Arbitrage (Pairs Trading).
    
    Concepto:
    1. Calcular spread entre dos activos cointegrados
    2. Calcular Z-Score del spread
    3. Si Z-Score > 2: Symbol2 sobrevaluado → Short Symbol2 / Long Symbol1
    4. Si Z-Score < -2: Symbol1 sobrevaluado → Short Symbol1 / Long Symbol2
    5. Cerrar cuando Z-Score vuelve a 0
    """
    
    def __init__(
        self,
        symbol1: str = 'BTC/USDT',
        symbol2: str = 'ETH/USDT',
        lookback_period: int = 30,    # Período para calcular spread
        entry_threshold: float = 2.0,  # Z-Score para entrar
        exit_threshold: float = 0.5,   # Z-Score para salir
        position_size: float = 0.001,  # Tamaño de posición
        fee_rate: float = 0.001       # 0.1% fee
    ):
        """
        Inicializar estrategia de statistical arbitrage.
        
        Args:
            symbol1: Primer símbolo del par
            symbol2: Segundo símbolo del par
            lookback_period: Período para cálculos estadísticos
            entry_threshold: Z-Score mínimo para abrir posición
            exit_threshold: Z-Score para cerrar posición
            position_size: Tamaño de posición
            fee_rate: Tasa de comisión
        """
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.position_size = position_size
        self.fee_rate = fee_rate
        
        self.positions: List[PairPosition] = []
        self.hedge_ratio: float = 1.0  # Ratio de hedge entre los activos
        
        logger.info(f"StatisticalArbitrage inicializada")
        logger.info(f"  Par: {symbol1} / {symbol2}")
        logger.info(f"  Entry threshold: {entry_threshold}")
        logger.info(f"  Exit threshold: {exit_threshold}")
    
    def calculate_spread(self, price1: pd.Series, price2: pd.Series) -> pd.Series:
        """
        Calcular spread entre dos series de precios (optimizado).
        
        Args:
            price1: Serie de precios del símbolo 1
            price2: Serie de precios del símbolo 2
            
        Returns:
            Serie con el spread
        """
        # Método optimizado: usar ratio simple en lugar de regresión rolling
        # Ratio = price1 / price2
        ratio = price1 / price2
        
        # Spread = ratio - media_moving(ratio)
        spread = ratio - ratio.rolling(window=self.lookback_period).mean()
        
        # Hedge ratio simple
        self.hedge_ratio = ratio.rolling(window=self.lookback_period).mean().iloc[-1]
        
        return spread
    
    def calculate_z_score(self, spread: pd.Series) -> pd.Series:
        """
        Calcular Z-Score del spread.
        
        Args:
            spread: Serie del spread
            
        Returns:
            Serie con Z-Score
        """
        rolling_mean = spread.rolling(window=self.lookback_period).mean()
        rolling_std = spread.rolling(window=self.lookback_period).std()
        
        z_score = (spread - rolling_mean) / rolling_std
        
        return z_score
    
    def generate_signal(self, data1: pd.DataFrame, data2: pd.DataFrame) -> Optional[Dict]:
        """
        Generar señal basada en Z-Score del spread.
        
        Args:
            data1: DataFrame del símbolo 1
            data2: DataFrame del símbolo 2
            
        Returns:
            Dict con acción ('long_spread', 'short_spread', 'close')
        """
        if len(data1) < self.lookback_period or len(data2) < self.lookback_period:
            return None
        
        # Calcular spread y Z-Score
        spread = self.calculate_spread(data1['close'], data2['close'])
        z_score = self.calculate_z_score(spread)
        
        current_z_score = z_score.iloc[-1]
        current_time = data1.index[-1]
        
        # Verificar posiciones abiertas para cerrar
        for position in self.positions:
            if position.status == 'open':
                # Cerrar si Z-Score vuelve cerca de 0
                if abs(current_z_score) < self.exit_threshold:
                    return {
                        'action': 'close',
                        'position_id': id(position),
                        'reason': 'z_score_reverted',
                        'current_z_score': current_z_score
                    }
        
        # Abrir nueva posición si no hay posiciones abiertas
        open_positions = [p for p in self.positions if p.status == 'open']
        if len(open_positions) == 0:
            # Z-Score alto → Symbol2 sobrevaluado → Short Symbol2 / Long Symbol1
            if current_z_score > self.entry_threshold:
                return {
                    'action': 'short_spread',  # Short symbol2, Long symbol1
                    'z_score': current_z_score,
                    'hedge_ratio': self.hedge_ratio,
                    'reason': 'high_z_score'
                }
            
            # Z-Score bajo → Symbol1 sobrevaluado → Short Symbol1 / Long Symbol2
            elif current_z_score < -self.entry_threshold:
                return {
                    'action': 'long_spread',  # Long symbol2, Short symbol1
                    'z_score': current_z_score,
                    'hedge_ratio': self.hedge_ratio,
                    'reason': 'low_z_score'
                }
        
        return None


def create_pairs_strategy_function(pairs_strategy: StatisticalArbitrage, data2: pd.DataFrame):
    """
    Crear función de estrategia compatible con backtest engine.
    
    Args:
        pairs_strategy: Instancia de StatisticalArbitrage
        data2: DataFrame del segundo símbolo
        
    Returns:
        Función que puede ser usada en BacktestEngine
    """
    def strategy_function(data1: pd.DataFrame) -> Optional[Dict]:
        return pairs_strategy.generate_signal(data1, data2)
    
    return strategy_function


def simulate_correlated_pair(base_df: pd.DataFrame, correlation: float = 0.8) -> pd.DataFrame:
    """
    Simular un par correlacionado para testing.
    
    Args:
        base_df: DataFrame base
        correlation: Correlación deseada
        
    Returns:
        DataFrame correlacionado
    """
    df = base_df.copy()
    
    # Generar precios correlacionados
    returns = df['close'].pct_change().fillna(0)
    
    np.random.seed(123)
    noise = np.random.randn(len(returns)) * np.sqrt(1 - correlation**2)
    correlated_returns = correlation * returns + np.sqrt(1 - correlation**2) * noise
    
    # Precio base diferente
    base_price = 3000
    prices = [base_price]
    
    for ret in correlated_returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    df['close'] = prices
    df['open'] = df['close'] * (1 + np.random.randn(len(df)) * 0.001)
    df['high'] = df['close'] * (1 + np.abs(np.random.randn(len(df)) * 0.002))
    df['low'] = df['close'] * (1 - np.abs(np.random.randn(len(df)) * 0.002))
    
    return df


def main():
    """Función principal para testing."""
    from src.backtesting.indicators import add_all_indicators
    from src.backtesting.backtest_engine import BacktestEngine
    
    # Generar datos de prueba para el par
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=2000, freq='1h')
    
    # Simular BTC
    base_price = 50000
    noise = np.random.randn(2000) * 200
    trend = np.linspace(0, 5000, 2000) * 0.3
    btc_price = base_price + noise + trend
    
    btc_df = pd.DataFrame({
        'timestamp': dates,
        'open': btc_price + np.random.randn(2000) * 50,
        'high': btc_price + np.abs(np.random.randn(2000) * 100),
        'low': btc_price - np.abs(np.random.randn(2000) * 100),
        'close': btc_price,
        'volume': np.random.randint(100, 1000, 2000)
    })
    btc_df.set_index('timestamp', inplace=True)
    
    # Simular ETH correlacionado
    eth_df = simulate_correlated_pair(btc_df, correlation=0.85)
    
    # Añadir indicadores
    btc_df = add_all_indicators(btc_df)
    eth_df = add_all_indicators(eth_df)
    
    # Crear estrategia de pairs trading
    pairs_strategy = StatisticalArbitrage(
        symbol1='BTC/USDT',
        symbol2='ETH/USDT',
        lookback_period=30,
        entry_threshold=2.0,
        exit_threshold=0.5,
        position_size=0.001
    )
    
    strategy_func = create_pairs_strategy_function(pairs_strategy, eth_df)
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(
        data=btc_df,
        strategy_func=strategy_func,
        strategy_name="Statistical Arbitrage (Pairs Trading)",
        symbol="BTC/USDT"
    )
    
    print("\nResultados Statistical Arbitrage:")
    print(f"Total Trades: {result.total_trades}")
    print(f"Win Rate: {result.win_rate:.1f}%")
    print(f"Total P&L: ${result.total_pnl:.2f}")
    print(f"Return: {(result.total_pnl / result.initial_capital) * 100:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Hedge Ratio final: {pairs_strategy.hedge_ratio:.4f}")


if __name__ == '__main__':
    main()
