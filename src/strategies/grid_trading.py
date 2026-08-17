"""
Grid Trading Strategy Module
Estrategia de Grid Trading - ideal para mercados laterales.
Sin IA - reglas matemáticas deterministas.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GridLevel:
    """Nivel individual del grid."""
    price: float
    buy_order: bool = True  # True = orden de compra, False = orden de venta
    filled: bool = False
    order_id: Optional[str] = None


class GridTradingStrategy:
    """
    Estrategia de Grid Trading.
    
    Coloca una red de órdenes de compra y venta a intervalos regulares.
    Funciona mejor en mercados laterales (ranging).
    """
    
    def __init__(
        self,
        grid_size: float = 0.01,  # 1% entre niveles
        grid_levels: int = 10,    # Número de niveles arriba y abajo
        position_size: float = 0.001,  # Tamaño de posición por nivel
        atr_multiplier: float = 2.0,   # Multiplicador de ATR para ajustar grid
        atr_period: int = 14
    ):
        """
        Inicializar estrategia de grid trading.
        
        Args:
            grid_size: Distancia porcentual entre niveles (default 1%)
            grid_levels: Número de niveles arriba y abajo del precio actual
            position_size: Tamaño de posición en cada nivel
            atr_multiplier: Multiplicador de ATR para ajustar grid dinámicamente
            atr_period: Período para cálculo de ATR
        """
        self.grid_size = grid_size
        self.grid_levels = grid_levels
        self.position_size = position_size
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        
        self.grid_levels_list: List[GridLevel] = []
        self.current_price: Optional[float] = None
        self.upper_bound: Optional[float] = None
        self.lower_bound: Optional[float] = None
        
        self.position = 0.0  # Posición actual (positiva = long, negativa = short)
        self.average_entry: Optional[float] = None
        
        self.last_reinit_time: Optional[pd.Timestamp] = None
        self.reinit_cooldown = 24  # Horas entre re-inicializaciones
        
        logger.info(f"GridTradingStrategy inicializada: Grid Size={grid_size*100}%, Levels={grid_levels}")
    
    def initialize_grid(self, current_price: float, atr: float, current_time: Optional[pd.Timestamp] = None):
        """
        Inicializar grid basado en precio actual y volatilidad.
        
        Args:
            current_price: Precio actual del activo
            atr: Average True Range actual
            current_time: Timestamp actual para evitar re-inicializaciones muy frecuentes
        """
        # Verificar cooldown para evitar re-inicializaciones muy frecuentes
        if current_time is not None and self.last_reinit_time is not None:
            time_diff = (current_time - self.last_reinit_time).total_seconds() / 3600  # Horas
            if time_diff < self.reinit_cooldown:
                return  # Skip re-initialization
        
        self.current_price = current_price
        if current_time is not None:
            self.last_reinit_time = current_time
        
        # Ajustar grid size basado en volatilidad
        dynamic_grid_size = self.grid_size * (atr / current_price) * self.atr_multiplier
        
        # Calcular límites del grid
        self.upper_bound = current_price * (1 + (self.grid_levels * dynamic_grid_size))
        self.lower_bound = current_price * (1 - (self.grid_levels * dynamic_grid_size))
        
        # Crear niveles del grid
        self.grid_levels_list = []
        
        # Niveles de compra (abajo del precio actual)
        for i in range(1, self.grid_levels + 1):
            level_price = current_price * (1 - (i * dynamic_grid_size))
            self.grid_levels_list.append(GridLevel(price=level_price, buy_order=True))
        
        # Niveles de venta (arriba del precio actual)
        for i in range(1, self.grid_levels + 1):
            level_price = current_price * (1 + (i * dynamic_grid_size))
            self.grid_levels_list.append(GridLevel(price=level_price, buy_order=False))
        
        # Ordenar por precio
        self.grid_levels_list.sort(key=lambda x: x.price)
        
        # Solo loggear cambios significativos
        if self.current_price is None or abs(current_price - self.current_price) > (self.current_price * 0.01):
            logger.info(f"Grid inicializado: Rango ${self.lower_bound:.2f} - ${self.upper_bound:.2f}")
            logger.info(f"Niveles totales: {len(self.grid_levels_list)}")
    
    def generate_signal(self, data: pd.DataFrame, open_position: Optional[Dict] = None) -> Optional[Dict]:
        """
        Generar señal de trading basada en grid.
        
        Args:
            data: DataFrame con datos OHLCV + indicadores
            
        Returns:
            Dict con acción ('buy', 'sell', 'close')
        """
        if len(data) < self.atr_period:
            return None
        
        latest = data.iloc[-1]
        current_price = latest['close']
        atr = latest['atr']
        
        # Inicializar grid si no está inicializado
        if self.current_price is None:
            self.initialize_grid(current_price, atr, data.index[-1])
            return None
        
        # Verificar si el precio salió del rango del grid (con margen)
        margin = (self.upper_bound - self.lower_bound) * 0.1  # 10% de margen
        if current_price > (self.upper_bound + margin) or current_price < (self.lower_bound - margin):
            # Re-inicializar grid con nuevo centro solo si es necesario
            if abs(current_price - self.current_price) > (self.current_price * 0.05):  # 5% de cambio
                self.initialize_grid(current_price, atr, data.index[-1])
                return {'action': 'close'}
        
        # Verificar niveles del grid - ordenar por proximidad al precio actual
        sorted_levels = sorted(self.grid_levels_list, key=lambda x: abs(x.price - current_price))
        
        for level in sorted_levels:
            if not level.filled:
                # Verificar si el precio cruzó el nivel (con un pequeño margen)
                price_diff_pct = abs(current_price - level.price) / level.price
                
                if level.buy_order:
                    # Nivel de compra - verificar si precio está cerca o abajo del nivel
                    if current_price <= level.price * 1.001:  # 0.1% de margen
                        level.filled = True
                        return {
                            'action': 'buy',
                            'price': level.price,
                            'quantity': self.position_size,
                            'level': level.price
                        }
                else:
                    # Nivel de venta - verificar si precio está cerca o arriba del nivel
                    if current_price >= level.price * 0.999:  # 0.1% de margen
                        level.filled = True
                        return {
                            'action': 'sell',
                            'price': level.price,
                            'quantity': self.position_size,
                            'level': level.price
                        }
        
        # Lógica de toma de profit y stop loss
        if self.position != 0:
            # Calcular P&L no realizado
            unrealized_pnl = self._calculate_unrealized_pnl(current_price)
            
            # Tomar profit si el precio vuelve al centro del grid
            center_price = (self.upper_bound + self.lower_bound) / 2
            
            if self.position > 0 and current_price >= center_price:
                return {'action': 'close', 'reason': 'take_profit'}
            elif self.position < 0 and current_price <= center_price:
                return {'action': 'close', 'reason': 'take_profit'}
        
        return None
    
    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calcular P&L no realizado."""
        if self.position == 0 or self.average_entry is None:
            return 0.0
        
        if self.position > 0:
            return (current_price - self.average_entry) * self.position
        else:
            return (self.average_entry - current_price) * abs(self.position)
    
    def update_position(self, action: str, price: float, quantity: float):
        """
        Actualizar posición después de ejecutar orden.
        
        Args:
            action: 'buy' o 'sell'
            price: Precio de ejecución
            quantity: Cantidad ejecutada
        """
        if action == 'buy':
            if self.position == 0:
                self.position = quantity
                self.average_entry = price
            elif self.position > 0:
                # Añadir a posición long
                total_value = (self.position * self.average_entry) + (quantity * price)
                self.position += quantity
                self.average_entry = total_value / self.position
            else:
                # Reducir posición short
                self.position += quantity
                if self.position >= 0:
                    self.position = 0
                    self.average_entry = None
        
        elif action == 'sell':
            if self.position == 0:
                self.position = -quantity
                self.average_entry = price
            elif self.position < 0:
                # Añadir a posición short
                total_value = (abs(self.position) * self.average_entry) + (quantity * price)
                self.position -= quantity
                self.average_entry = total_value / abs(self.position)
            else:
                # Reducir posición long
                self.position -= quantity
                if self.position <= 0:
                    self.position = 0
                    self.average_entry = None
    
    def get_grid_status(self) -> Dict:
        """
        Obtener estado actual del grid.
        
        Returns:
            Dict con información del grid
        """
        filled_levels = sum(1 for level in self.grid_levels_list if level.filled)
        total_levels = len(self.grid_levels_list)
        
        return {
            'current_price': self.current_price,
            'upper_bound': self.upper_bound,
            'lower_bound': self.lower_bound,
            'grid_levels': total_levels,
            'filled_levels': filled_levels,
            'fill_rate': (filled_levels / total_levels * 100) if total_levels > 0 else 0,
            'current_position': self.position,
            'average_entry': self.average_entry
        }


def create_grid_strategy_function(grid_strategy: GridTradingStrategy):
    """
    Crear función de estrategia compatible con backtest engine.
    
    Args:
        grid_strategy: Instancia de GridTradingStrategy
        
    Returns:
        Función que puede ser usada en BacktestEngine
    """
    def strategy_function(data: pd.DataFrame) -> Optional[Dict]:
        return grid_strategy.generate_signal(data)
    
    return strategy_function


def main():
    """Función principal para testing."""
    from src.backtesting.indicators import add_all_indicators
    from src.backtesting.backtest_engine import BacktestEngine
    
    # Crear datos de prueba (mercado lateral)
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=2000, freq='1h')
    
    # Simular mercado lateral con algo de ruido
    base_price = 50000
    noise = np.random.randn(2000) * 100
    mean_reversion = -0.1 * np.cumsum(noise)  # Fuerza de retorno a la media
    price = base_price + noise + mean_reversion
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price + np.random.randn(2000) * 20,
        'high': price + np.abs(np.random.randn(2000) * 50),
        'low': price - np.abs(np.random.randn(2000) * 50),
        'close': price,
        'volume': np.random.randint(100, 1000, 2000)
    })
    df.set_index('timestamp', inplace=True)
    
    # Añadir indicadores
    df = add_all_indicators(df)
    
    # Crear estrategia de grid
    grid_strategy = GridTradingStrategy(
        grid_size=0.005,  # 0.5% entre niveles
        grid_levels=8,    # 8 niveles arriba y abajo
        position_size=0.0005,
        atr_multiplier=1.5
    )
    
    # Crear función de estrategia
    strategy_func = create_grid_strategy_function(grid_strategy)
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(df, strategy_func, "Grid Trading Strategy", "BTC/USDT")
    
    # Imprimir resultados
    engine.print_results(result)
    
    # Imprimir estado final del grid
    print("\nEstado final del grid:")
    grid_status = grid_strategy.get_grid_status()
    for key, value in grid_status.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
