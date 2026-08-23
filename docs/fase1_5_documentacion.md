# Fase 1.5: Backtesting Engine y Estrategias

## Objetivo
Implementar motor de backtesting determinista y primera estrategia simple (Grid Trading) para validar el sistema sin IA.

## Componentes Implementados

### 1. Indicadores Técnicos (`src/backtesting/indicators.py`)

**Funcionalidades:**
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- Stochastic Oscillator
- Volatilidad histórica
- Z-Score (para statistical arbitrage)
- Correlación rolling (para pairs trading)

**Uso básico:**
```python
from src.backtesting.indicators import add_all_indicators

# Añadir todos los indicadores a un DataFrame OHLCV
df_with_indicators = add_all_indicators(df)
```

### 2. Motor de Backtesting (`src/backtesting/backtest_engine.py`)

**Funcionalidades:**
- Simulación de trades con fees y slippage realistas
- Gestión de posiciones (long/short)
- Cálculo de P&L en tiempo real
- Equity curve tracking
- Métricas de performance:
  - Win rate, Sharpe ratio, Max drawdown
  - Profit factor, Average win/loss
  - Total trades, P&L

**Clases principales:**
- `Trade`: Representación de un trade individual
- `BacktestResult`: Resultados completos del backtest
- `BacktestEngine`: Motor principal de simulación

**Uso básico:**
```python
from src.backtesting.backtest_engine import BacktestEngine

engine = BacktestEngine(initial_capital=10000, fee_rate=0.001)
result = engine.run_backtest(data, strategy_func, "Strategy Name", "BTC/USDT")
engine.print_results(result)
```

### 3. Estrategia Grid Trading (`src/strategies/grid_trading.py`)

**Funcionalidades:**
- Grid dinámico basado en volatilidad (ATR)
- Niveles de compra y venta automáticos
- Ajuste automático cuando el precio sale del rango
- Gestión de posiciones múltiples
- Take profit cuando el precio vuelve al centro

**Parámetros configurables:**
- `grid_size`: Distancia porcentual entre niveles (default 0.5%)
- `grid_levels`: Número de niveles arriba/abajo (default 10)
- `position_size`: Tamaño de posición por nivel
- `atr_multiplier`: Ajuste por volatilidad (default 0.5)

**Uso básico:**
```python
from src.strategies.grid_trading import GridTradingStrategy, create_grid_strategy_function

grid_strategy = GridTradingStrategy(
    grid_size=0.005,
    grid_levels=10,
    position_size=0.0005
)
strategy_func = create_grid_strategy_function(grid_strategy)
```

### 4. Script de Ejecución (`scripts/run_backtest.py`)

**Funcionalidades:**
- Generación de datos de prueba realistas
- Ejecución de backtests múltiples
- Comparación de estrategias
- Guardado automático de resultados
- Visualización de métricas

**Uso:**
```bash
python scripts/run_backtest.py
```

## Resultados de Pruebas

### Grid Trading Strategy (30 días)
```
Total Trades: 1
Win Rate: 100.00%
Total P&L: $210.33
Return: 2.10%
Max Drawdown: 0.00%
Sharpe Ratio: -0.04
```

### RSI + SMA Strategy (30 días)
```
Total Trades: 0
Win Rate: 0.00%
Total P&L: $0.00
Return: 0.00%
```

## Optimizaciones para M2 (8GB RAM)

1. **Cálculos vectorizados con NumPy/Pandas** - Eficiencia máxima
2. **Gestión de memoria en chunks** - Procesar datos por lotes
3. **Indicadores pre-calculados** - Evitar recálculos redundantes
4. **Logging controlado** - No saturar memoria con logs excesivos
5. **Resultados en disco** - Guardar en archivos, no solo en memoria

## Arquitectura del Sistema

```
Data Collection → Indicators → Strategy → Backtest Engine → Results
      ↓              ↓           ↓              ↓              ↓
   CCXT/Parquet    Technical   Grid/RSI     Simulation    Metrics
                  Analysis    Logic       with Fees    & Analysis
```

## Próximos Pasos

### Fase 2: Mejoras del Sistema
1. **Más estrategias:**
   - Statistical Arbitrage (pairs trading)
   - Funding Rate Arbitrage
   - Mean Reversion avanzado

2. **Optimización de parámetros:**
   - Grid search de parámetros
   - Walk-forward optimization
   - Análisis de robustez

3. **Conexión a datos reales:**
   - Descarga de datos históricos de Binance
   - Backtesting con datos reales
   - Validación de estrategias

### Fase 3: Paper Trading
1. **Conexión a Binance Testnet**
2. **Ejecución en tiempo real (sin riesgo)**
3. **Validación de estrategias en vivo**
4. **Ajustes basados en performance real**

## Notas Importantes

- Todo el código es determinista, sin IA por ahora
- Enfoque en simplicidad y verificabilidad (Método Karpathy)
- Sistema listo para integrar IA cuando se tenga DGX Spark
- Documentación completa para facilitar migración
- Estrategias optimizadas para mercados laterales (grid trading ideal)

## Consideraciones para Trading Real

Cuando migres a trading real (paper trading primero):

1. **API Keys de Binance:**
   - Usar Binance Futures Testnet para pruebas
   - Nunca usar keys de cuenta real con dinero

2. **Risk Management:**
   - Position sizing apropiado
   - Stop losses implementados
   - Límites diarios de pérdida

3. **Monitoreo:**
   - Dashboard en tiempo real
   - Alertas de errores
   - Logs completos de decisiones

4. **Mejores Prácticas:**
   - Empezar con capital muy pequeño
   - Validar extensivamente en paper trading
   - Escalar gradualmente
