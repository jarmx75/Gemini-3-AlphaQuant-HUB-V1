#!/usr/bin/env python3
"""
Suite Masiva de Backtesting Cuantitativo (30+ Activos x 5 Estrategias)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.grid_trading import GridTradingStrategy, create_grid_strategy_function
from src.strategies.ema_cross_protector import EMACrossProtectorStrategy, create_ema_cross_protector_function
from src.strategies.adaptive_supertrend import AdaptiveSuperTrendStrategy, create_supertrend_strategy_function
from src.strategies.trend_breakout import TrendBreakoutStrategy, create_breakout_strategy_function
from src.strategies.macd_scalper import MACDStochasticScalperStrategy, create_macd_scalper_function
from src.strategies.vwap_reversion import VWAPMeanReversionStrategy, create_vwap_reversion_function

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_symbol_data(symbol: str, timeframe: str = '1h') -> pd.DataFrame:
    filename = f"{symbol.replace('/', '_')}_{timeframe}_90d.parquet"
    filepath = Path('data/raw') / filename
    
    if not filepath.exists():
        return pd.DataFrame()
    
    collector = DataCollector('binance', sandbox=False)
    return collector.load_from_parquet(str(filepath))


def rsi_sma_strategy(data: pd.DataFrame):
    if len(data) < 50:
        return None
    latest = data.iloc[-1]
    
    rsi_oversold = latest['rsi'] < 25
    rsi_overbought = latest['rsi'] > 75
    sma_bullish = latest['sma_20'] > latest['sma_50']
    sma_bearish = latest['sma_20'] < latest['sma_50']
    
    if rsi_oversold and sma_bullish:
        return {'action': 'buy'}
    elif rsi_overbought and sma_bearish:
        return {'action': 'sell'}
    elif latest['rsi'] > 55:
        return {'action': 'close'}
    return None


def run_suite():
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'LTC/USDT',
        'WIF/USDT', 'LINK/USDT', 'AAVE/USDT', 'ADA/USDT', 'DOT/USDT',
        'POL/USDT', 'AVAX/USDT', 'ATOM/USDT', 'NEAR/USDT', 'INJ/USDT',
        'APT/USDT', 'SUI/USDT', 'PEPE/USDT', 'DOGE/USDT', 'SHIB/USDT',
        'OP/USDT', 'ARB/USDT', 'TIA/USDT', 'FET/USDT', 'FLOKI/USDT',
        'BNB/USDT', 'UNI/USDT', 'FIL/USDT', 'ETC/USDT'
    ]
    
    timeframes = ['1h']
    results_summary = []
    
    print("\n" + "="*90)
    print("🚀 INICIANDO SUITE MASIVA DE BACKTESTING (30+ ACTIVOS x 5 ESTRATEGIAS)")
    print("="*90)
    
    for tf in timeframes:
        for symbol in symbols:
            df = load_symbol_data(symbol, tf)
            if df.empty:
                continue
                
            logger.info(f"Evaluando {symbol} ({tf}) - {len(df)} barras")
            df_ind = add_all_indicators(df)
            df_ind['symbol'] = symbol
            
            engine = BacktestEngine(initial_capital=10000, fee_rate=0.0004, slippage=0.0005)
            
            # Definir estrategias
            strategies_to_test = {
                'EMA Cross + Protector': create_ema_cross_protector_function(EMACrossProtectorStrategy()),
                'Adaptive SuperTrend': create_supertrend_strategy_function(AdaptiveSuperTrendStrategy()),
                'Trend Breakout': create_breakout_strategy_function(TrendBreakoutStrategy()),
                'MACD Scalper': create_macd_scalper_function(MACDStochasticScalperStrategy()),
                'VWAP Reversion': create_vwap_reversion_function(VWAPMeanReversionStrategy()),
                'Grid Trading': create_grid_strategy_function(GridTradingStrategy(grid_size=0.012, grid_levels=8)),
                'RSI + SMA': rsi_sma_strategy
            }
            
            for strat_name, strat_func in strategies_to_test.items():
                r = engine.run_backtest(df_ind, strat_func, strat_name, symbol)
                ret_pct = (r.total_pnl / r.initial_capital) * 100.0
                daily_ret = ret_pct / 90.0
                max_dd = r.max_drawdown_pct
                calmar = (ret_pct / max_dd) if max_dd > 0 else (ret_pct / 1.0)
                
                results_summary.append({
                    'Symbol': symbol,
                    'Timeframe': tf,
                    'Strategy': strat_name,
                    'Trades': r.total_trades,
                    'WinRate%': round(r.win_rate, 1),
                    'TotalPnL': round(r.total_pnl, 2),
                    'Return%': round(ret_pct, 2),
                    'DailyAvg%': round(daily_ret, 2),
                    'Sharpe': round(r.sharpe_ratio, 2),
                    'MaxDD%': round(max_dd, 2),
                    'CalmarRatio': round(calmar, 2)
                })

    summary_df = pd.DataFrame(results_summary)
    if not summary_df.empty:
        summary_df.sort_values(by='CalmarRatio', ascending=False, inplace=True)
        
        print("\n" + "="*110)
        print("🏆 TOP RANKING DE ESTRATEGIAS (ORDENADO POR RATIO DE CALMAR: RETORNO / RIESGO)")
        print("="*110)
        print(summary_df.head(30).to_string(index=False))
        print("="*110)
        
        output_dir = Path('backtests/results')
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = output_dir / f"suite_masiva_results_{timestamp}.csv"
        summary_df.to_csv(csv_path, index=False)
        logger.info(f"Resultados completos guardados en: {csv_path}")

if __name__ == '__main__':
    run_suite()
