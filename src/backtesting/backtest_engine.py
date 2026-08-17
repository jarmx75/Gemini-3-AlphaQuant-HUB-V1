"""
Backtesting Engine Module
Motor de backtesting determinista para simular estrategias de trading.
Sin IA - simulación basada en reglas matemáticas.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Representación de un trade."""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0.0
    fees: float = 0.0
    strategy: str = ""
    
    def calculate_pnl(self, exit_price: float, fee_rate: float = 0.001) -> float:
        """
        Calcular P&L del trade.
        
        Args:
            exit_price: Precio de salida
            fee_rate: Tasa de comisión (default 0.1%)
            
        Returns:
            P&L después de comisiones
        """
        if self.side == 'long':
            gross_pnl = (exit_price - self.entry_price) * self.quantity
        else:  # short
            gross_pnl = (self.entry_price - exit_price) * self.quantity
        
        # Calcular comisiones
        entry_fee = self.entry_price * self.quantity * fee_rate
        exit_fee = exit_price * self.quantity * fee_rate
        total_fees = entry_fee + exit_fee
        
        self.exit_price = exit_price
        self.fees = total_fees
        self.pnl = gross_pnl - total_fees
        
        return self.pnl


@dataclass
class BacktestResult:
    """Resultados del backtest."""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    
    # Métricas de performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    total_fees: float = 0.0
    
    # Métricas de riesgo
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Métricas adicionales
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Datos
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    
    def calculate_metrics(self, risk_free_rate: float = 0.02):
        """Calcular métricas derivadas."""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        if self.winning_trades > 0:
            winning_pnls = [t.pnl for t in self.trades if t.pnl > 0]
            self.average_win = np.mean(winning_pnls)
        
        if self.losing_trades > 0:
            losing_pnls = [t.pnl for t in self.trades if t.pnl < 0]
            self.average_loss = np.mean(losing_pnls)
        
        if self.losing_trades > 0 and self.average_loss != 0:
            gross_profit = sum([t.pnl for t in self.trades if t.pnl > 0])
            gross_loss = abs(sum([t.pnl for t in self.trades if t.pnl < 0]))
            self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Calcular Sharpe Ratio
        if len(self.equity_curve) > 1:
            returns = self.equity_curve.pct_change().dropna()
            if len(returns) > 1 and returns.std() > 0:
                # Factor de anualización aproximado para velas de 1h (~8760 periodos/año)
                ann_factor = np.sqrt(24 * 365) if len(returns) > 500 else np.sqrt(252)
                self.sharpe_ratio = ann_factor * (returns.mean() / returns.std())
        
        # Calcular Max Drawdown
        if len(self.equity_curve) > 1:
            equity = self.equity_curve
            running_max = equity.expanding().max()
            drawdown = (equity - running_max) / running_max
            min_dd = drawdown.min()
            self.max_drawdown_pct = abs(min_dd) * 100.0 if not np.isnan(min_dd) else 0.0
            self.max_drawdown = abs((equity - running_max).min()) if not np.isnan((equity - running_max).min()) else 0.0


class BacktestEngine:
    """Motor de backtesting determinista."""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.001,  # 0.1% por trade
        slippage: float = 0.0005   # 0.05% slippage
    ):
        """
        Inicializar motor de backtesting.
        
        Args:
            initial_capital: Capital inicial
            fee_rate: Tasa de comisión por trade
            slippage: Slippage por trade
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.current_capital = initial_capital
        
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.open_positions: Dict[str, Trade] = {}
        
        logger.info(f"BacktestEngine inicializado: Capital=${initial_capital}, Fee={fee_rate*100}%")
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_func,
        strategy_name: str = "strategy",
        symbol: str = "BTC/USDT"
    ) -> BacktestResult:
        """
        Ejecutar backtest de una estrategia.
        
        Args:
            data: DataFrame con datos OHLCV + indicadores
            strategy_func: Función que genera señales (recibe df, retorna señales)
            strategy_name: Nombre de la estrategia
            symbol: Símbolo del activo
            
        Returns:
            BacktestResult con métricas
        """
        logger.info(f"Iniciando backtest: {strategy_name} en {symbol}")
        
        # Resetear estado
        self.trades = []
        self.equity_curve = []
        self.open_positions = {}
        self.current_capital = self.initial_capital
        
        # Ejecutar estrategia en cada punto de datos
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            current_candle = data.iloc[i]
            
            # Actualizar equity curve primero
            self._update_equity(current_candle['close'])
            
            # Generar señal
            signal = strategy_func(current_data)
            
            # Procesar señal
            if signal is not None:
                self._process_signal(signal, current_candle, strategy_name, symbol)
        
        # Cerrar posiciones abiertas al final
        self._close_all_positions(data.iloc[-1], strategy_name)
        
        # Calcular resultados
        result = BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=data.index.freq if hasattr(data.index, 'freq') else 'unknown',
            start_date=data.index[0],
            end_date=data.index[-1],
            initial_capital=self.initial_capital,
            trades=self.trades,
            equity_curve=pd.Series(self.equity_curve, index=data.index)
        )
        
        result.total_trades = len(self.trades)
        result.winning_trades = len([t for t in self.trades if t.pnl > 0])
        result.losing_trades = len([t for t in self.trades if t.pnl <= 0])
        result.total_pnl = sum([t.pnl for t in self.trades])
        result.total_fees = sum([t.fees for t in self.trades])
        
        result.calculate_metrics()
        
        logger.info(f"Backtest completado: {result.total_trades} trades, P&L=${result.total_pnl:.2f}")
        
        return result
    
    def _process_signal(self, signal: Dict, candle: pd.Series, strategy: str, symbol: str):
        """
        Procesar señal de trading.
        
        Args:
            signal: Dict con 'action' ('buy', 'sell', 'close')
            candle: Datos de la vela actual
            strategy: Nombre de la estrategia
            symbol: Símbolo del activo
        """
        action = signal.get('action')
        
        if action == 'buy' and symbol not in self.open_positions:
            # Abrir posición long
            price = candle['close'] * (1 + self.slippage)
            quantity = (self.current_capital * 0.95) / price  # Usar 95% del capital
            
            trade = Trade(
                entry_time=candle.name,
                exit_time=None,
                symbol=symbol,
                side='long',
                entry_price=price,
                exit_price=None,
                quantity=quantity,
                strategy=strategy
            )
            
            self.open_positions[symbol] = trade
            logger.debug(f"Long abierto: {symbol} @ {price:.2f}")
            
        elif action == 'sell' and symbol not in self.open_positions:
            # Abrir posición short
            price = candle['close'] * (1 - self.slippage)
            quantity = (self.current_capital * 0.95) / price
            
            trade = Trade(
                entry_time=candle.name,
                exit_time=None,
                symbol=symbol,
                side='short',
                entry_price=price,
                exit_price=None,
                quantity=quantity,
                strategy=strategy
            )
            
            self.open_positions[symbol] = trade
            logger.debug(f"Short abierto: {symbol} @ {price:.2f}")
            
        elif action == 'close' and symbol in self.open_positions:
            # Cerrar posición
            self._close_position(symbol, candle['close'], candle.name)
    
    def _close_position(self, symbol: str, exit_price: float, exit_time: datetime):
        """Cerrar posición específica."""
        if symbol in self.open_positions:
            trade = self.open_positions[symbol]
            
            # Aplicar slippage
            if trade.side == 'long':
                adjusted_exit_price = exit_price * (1 - self.slippage)
            else:
                adjusted_exit_price = exit_price * (1 + self.slippage)
            
            # Calcular P&L
            pnl = trade.calculate_pnl(adjusted_exit_price, self.fee_rate)
            trade.exit_time = exit_time
            
            self.current_capital += pnl
            self.trades.append(trade)
            del self.open_positions[symbol]
            
            logger.debug(f"Posición cerrada: {symbol} P&L=${pnl:.2f}")
    
    def _close_all_positions(self, last_candle: pd.Series, strategy: str):
        """Cerrar todas las posiciones abiertas."""
        for symbol in list(self.open_positions.keys()):
            self._close_position(symbol, last_candle['close'], last_candle.name)
    
    def _update_equity(self, current_price: float):
        """Actualizar curva de equity."""
        # Calcular valor de posiciones abiertas
        unrealized_pnl = 0.0
        for symbol, trade in self.open_positions.items():
            if trade.side == 'long':
                unrealized_pnl += (current_price - trade.entry_price) * trade.quantity
            else:
                unrealized_pnl += (trade.entry_price - current_price) * trade.quantity
        
        total_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append(total_equity)
    
    def print_results(self, result: BacktestResult):
        """Imprimir resultados del backtest."""
        print("\n" + "="*50)
        print(f"RESULTADOS BACKTEST: {result.strategy_name}")
        print("="*50)
        print(f"Símbolo: {result.symbol}")
        print(f"Período: {result.start_date} a {result.end_date}")
        print(f"\nMétricas de Trading:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Winning Trades: {result.winning_trades}")
        print(f"  Losing Trades: {result.losing_trades}")
        print(f"  Win Rate: {result.win_rate:.2f}%")
        print(f"\nMétricas Financieras:")
        print(f"  Total P&L: ${result.total_pnl:.2f}")
        print(f"  Total Fees: ${result.total_fees:.2f}")
        print(f"  Capital Final: ${result.initial_capital + result.total_pnl:.2f}")
        print(f"  Retorno: {((result.total_pnl / result.initial_capital) * 100):.2f}%")
        print(f"\nMétricas de Riesgo:")
        print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"\nPromedios:")
        print(f"  Average Win: ${result.average_win:.2f}")
        print(f"  Average Loss: ${result.average_loss:.2f}")
        print("="*50 + "\n")


def main():
    """Función principal para testing."""
    from src.backtesting.indicators import add_all_indicators
    
    # Crear datos de prueba
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1h')
    
    # Simular movimiento de precio con tendencia
    trend = np.linspace(0, 10000, 1000)
    noise = np.cumsum(np.random.randn(1000) * 50)
    price = 50000 + trend + noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price + np.random.randn(1000) * 30,
        'high': price + np.abs(np.random.randn(1000) * 80),
        'low': price - np.abs(np.random.randn(1000) * 80),
        'close': price,
        'volume': np.random.randint(100, 1000, 1000)
    })
    df.set_index('timestamp', inplace=True)
    
    # Añadir indicadores
    df = add_all_indicators(df)
    
    # Definir estrategia simple: RSI + SMA crossover
    def simple_strategy(data: pd.DataFrame) -> Optional[Dict]:
        """Estrategia simple: Comprar cuando RSI < 30 y SMA20 > SMA50."""
        if len(data) < 50:
            return None
        
        latest = data.iloc[-1]
        
        # Señales
        rsi_oversold = latest['rsi'] < 30
        rsi_overbought = latest['rsi'] > 70
        sma_bullish = latest['sma_20'] > latest['sma_50']
        sma_bearish = latest['sma_20'] < latest['sma_50']
        
        if rsi_oversold and sma_bullish:
            return {'action': 'buy'}
        elif rsi_overbought and sma_bearish:
            return {'action': 'sell'}
        elif latest['rsi'] > 50:  # Tomar profit
            return {'action': 'close'}
        
        return None
    
    # Ejecutar backtest
    engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
    result = engine.run_backtest(df, simple_strategy, "RSI_SMA_Strategy", "BTC/USDT")
    
    # Imprimir resultados
    engine.print_results(result)


if __name__ == '__main__':
    main()
