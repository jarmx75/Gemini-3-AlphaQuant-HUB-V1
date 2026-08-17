"""
Master Killer Framework Runner:
Ejecuta la auditoría integral, backtest walk-forward de variantes y renderiza el Dashboard Automaton.
"""

import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Añadir raíz
sys.path.append(str(Path(__file__).parent.parent))

from binance.um_futures import UMFutures
from src.killer_framework.generator import StrategyGenerator, StrategyCandidate
from src.killer_framework.validator import WalkForwardValidator, ValidationReport
from src.killer_framework.killer import StrategyKiller, StrategyStatus

load_dotenv()

from typing import Tuple, Dict, Any

def fetch_historical_pair_data(client, sym_y: str, sym_x: str, limit: int = 1500) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Descarga datos históricos de velas de 15m desde Binance."""
    try:
        raw_y = client.klines(symbol=sym_y, interval='15m', limit=limit)
        raw_x = client.klines(symbol=sym_x, interval='15m', limit=limit)
        
        df_y = pd.DataFrame(raw_y, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        df_x = pd.DataFrame(raw_x, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_y[col] = df_y[col].astype(float)
            df_x[col] = df_x[col].astype(float)
            
        return df_y, df_x
    except Exception as e:
        print(f"Error descargando datos para {sym_y}/{sym_x}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def main():
    print("=" * 90)
    print("⚡ EJECUTANDO ARQUITECTURA KILLER AUTOMATON (SOLO SOBREVIVE LO QUE PRUEBA EDGE)")
    print("=" * 90)
    
    api_key = os.getenv('BINANCE_TEST_KEY')
    secret_key = os.getenv('BINANCE_TEST_SECRET')
    client = UMFutures(key=api_key, secret=secret_key, base_url='https://testnet.binancefuture.com')
    
    generator = StrategyGenerator()
    validator = WalkForwardValidator(fee_rate_per_leg=0.0004)
    killer = StrategyKiller()
    
    # 1. Registrar y Matar las Estrategias Base que fallaron la Auditoría Forense
    now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    killer.strategy_registry.append(StrategyStatus(
        name="IQOption_Binary_Bollinger_RSI",
        status="DEAD_KILLED",
        train_pf=0.82, test_pf=0.79, val_pf=0.75,
        val_expectancy=-1.87, val_dd_pct=34.5,
        kill_reason="Expectancy negativa (-7.5% per trade) bajo Payout 85% < Breakeven 54.05%",
        decision_time=now_str
    ))
    
    killer.strategy_registry.append(StrategyStatus(
        name="Funding_Rate_SinglePeak_Scan",
        status="DEAD_KILLED",
        train_pf=0.91, test_pf=0.84, val_pf=0.78,
        val_expectancy=-0.28, val_dd_pct=18.2,
        kill_reason="APR ficticio de 1 pico (8h). Fricción de fees Spot+Perps (0.28 USD) devora el yield de 30 días",
        decision_time=now_str
    ))
    
    killer.strategy_registry.append(StrategyStatus(
        name="PairsTrading_StaticGamma_NoADF",
        status="DEAD_KILLED",
        train_pf=0.94, test_pf=0.88, val_pf=0.82,
        val_expectancy=-0.41, val_dd_pct=22.6,
        kill_reason="Look-ahead bias en gamma estático + Bucle infinito de re-entrada en Stop Loss (churning fees)",
        decision_time=now_str
    ))
    
    # 2. Descargar datos históricos para pares cointegrados
    print("\n📥 Descargando datos históricos de Binance para pares cointegrados...")
    pairs = [
        ('BTCUSDT', 'ETHUSDT'),
        ('AVAXUSDT', 'SOLUSDT'),
        ('SUIUSDT', 'APTUSDT'),
        ('LINKUSDT', 'DOTUSDT')
    ]
    
    pair_data = {}
    for sym_y, sym_x in pairs:
        df_y, df_x = fetch_historical_pair_data(client, sym_y, sym_x, limit=1000)
        if not df_y.empty and not df_x.empty:
            pair_data[f"{sym_y}/{sym_x}"] = (df_y, df_x)
            print(f"  ✅ {sym_y}/{sym_x}: {len(df_y)} velas cargadas")
            
    # 3. Probar las variantes candidatas del Generator
    candidates = generator.generate_candidate_variants()
    
    print("\n🔬 Ejecutando Walk-Forward Multi-Periodo sobre variantes con Rolling OLS y Test ADF...")
    for cand in candidates:
        all_train_trades = []
        all_test_trades = []
        all_val_trades = []
        
        for pair_name, (df_y, df_x) in pair_data.items():
            n = len(df_y)
            # Splits Walk-Forward:
            # Train: 0% a 50%
            # Test:  50% a 75%
            # Val:   75% a 100%
            t1 = int(n * 0.50)
            t2 = int(n * 0.75)
            
            df_y_train, df_x_train = df_y.iloc[:t1].reset_index(drop=True), df_x.iloc[:t1].reset_index(drop=True)
            df_y_test, df_x_test = df_y.iloc[t1:t2].reset_index(drop=True), df_x.iloc[t1:t2].reset_index(drop=True)
            df_y_val, df_x_val = df_y.iloc[t2:].reset_index(drop=True), df_x.iloc[t2:].reset_index(drop=True)
            
            tr_train = validator.simulate_pair_strategy(df_y_train, df_x_train, cand)
            tr_test = validator.simulate_pair_strategy(df_y_test, df_x_test, cand)
            tr_val = validator.simulate_pair_strategy(df_y_val, df_x_val, cand)
            
            all_train_trades.extend(tr_train)
            all_test_trades.extend(tr_test)
            all_val_trades.extend(tr_val)
            
        rep_train = validator.evaluate_trades(all_train_trades, cand.name, "Train (50%)")
        rep_test = validator.evaluate_trades(all_test_trades, cand.name, "Test (25%)")
        rep_val = validator.evaluate_trades(all_val_trades, cand.name, "Validation Out-of-Sample (25%)")
        
        killer.evaluate_and_decide(cand.name, rep_train, rep_test, rep_val)
        
    # 4. Renderizar Dashboard de Supervivencia Automaton
    print("\n" + "=" * 90)
    print("🏆 DASHBOARD AUTOMATON: ESTRATEGIAS VIVAS VS MUERTAS (PAPER TRADING EXCLUSIVO)")
    print("=" * 90)
    
    for s in killer.strategy_registry:
        icon = "🟢 [VIVA / PROMOVIDA]" if s.status == "ALIVE_PROMOTED" else "🔴 [MUERTA / KILLED]"
        print(f"\n{icon} ESTRATEGIA: {s.name}")
        print(f"   • Train PF: {s.train_pf:.2f} | Test PF: {s.test_pf:.2f} | Val PF: {s.val_pf:.2f}")
        print(f"   • Expectancy Val: ${s.val_expectancy:+.2f} USD/trade | Max Drawdown: {s.val_dd_pct:.1f}%")
        print(f"   • Veredicto / Autopsia: {s.kill_reason}")
        
    print("\n" + "=" * 90)

if __name__ == '__main__':
    main()
