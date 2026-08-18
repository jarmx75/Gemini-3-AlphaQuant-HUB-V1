"""
Factory Validator for FUNDING_CONTRARIAN
Ejecuta backtesting Walk-Forward sobre BTCUSDT y ETHUSDT usando datos reales de Funding Rate:
- OHLCV 1H + Funding Rate 8H
- Train: 2022-2023, Test: 2024, Valid OOS: 2024-2026
- Fees: 0.16% round-trip sobre nocional de $300 USD
- Criterio de Supervivencia:
  Validation PF > 1.30 AND Max DD < 15.0% AND Trades > 100 AND Expectancy > 0.0
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from src.strategies.funding_contrarian import FundingContrarian1H
from src.factory.generator_funding import FundingCandidate

@dataclass
class FundingEvaluationResult:
    candidate_id: str
    family: str
    train_pf: float
    test_pf: float
    val_pf: float
    val_trades: int
    val_win_rate: float
    val_net_pnl: float
    val_expectancy: float
    val_max_dd_pct: float
    passed: bool
    verdict: str

class FundingValidator:
    """Validador Walk-Forward para Funding Contrarian."""
    
    def __init__(
        self,
        historical_ohlcv_dir: str = "data/historical",
        historical_derivatives_dir: str = "data/historical_derivatives"
    ):
        self.ohlcv_dir = Path(historical_ohlcv_dir)
        self.deriv_dir = Path(historical_derivatives_dir)
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        self.prepared_data = {}
        self.load_and_prepare()

    def load_and_prepare(self):
        """Carga y fusiona datasets de OHLCV y funding rates."""
        engine = FundingContrarian1H()
        for sym in self.symbols:
            ohlcv_file = self.ohlcv_dir / f"{sym}_1h_2022_2026.csv"
            funding_file = self.deriv_dir / f"{sym}_funding_rate_2022_2026.csv"
            
            if ohlcv_file.exists() and funding_file.exists():
                df_ohlcv = pd.read_csv(ohlcv_file)
                df_funding = pd.read_csv(funding_file)
                
                df_prepared = engine.prepare_dataset(df_ohlcv, df_funding)
                self.prepared_data[sym] = df_prepared

    def simulate_asset(
        self,
        df_prepared: pd.DataFrame,
        cand: FundingCandidate,
        notional: float = 300.0
    ) -> List[Dict[str, Any]]:
        opens = df_prepared['open'].values
        closes = df_prepared['close'].values
        is_funding = df_prepared['is_funding_bar'].values
        funding_z = df_prepared['funding_z'].values
        price_ext = df_prepared['price_ext'].values
        sma_exit = df_prepared['sma_exit'].values
        n = len(df_prepared)
        
        trades = []
        in_pos = False
        pos_side = None
        entry_price = 0.0
        entry_idx = 0
        
        start_idx = 100
        
        for t in range(start_idx, n):
            curr_open = opens[t]
            curr_close = closes[t]
            
            if not in_pos:
                # La señal solo se evalúa si en t-1 se publicó un funding rate
                if is_funding[t-1]:
                    prev_fz = funding_z[t-1]
                    prev_pe = price_ext[t-1]
                    
                    # 1. Señal SHORT: Funding extremadamente positivo + precio extendido arriba
                    if prev_fz >= cand.funding_z and prev_pe >= cand.price_extension_atr:
                        in_pos = True
                        pos_side = 'SHORT'
                        entry_price = curr_open
                        entry_idx = t
                    # 2. Señal LONG: Funding extremadamente negativo + precio extendido abajo
                    elif prev_fz <= -cand.funding_z and prev_pe <= -cand.price_extension_atr:
                        in_pos = True
                        pos_side = 'LONG'
                        entry_price = curr_open
                        entry_idx = t
            else:
                bars_held = t - entry_idx + 1
                exit_flag = False
                exit_price = curr_close
                exit_reason = ""
                prev_sma = sma_exit[t-1]
                
                if pos_side == 'LONG':
                    pnl_pct = (curr_close - entry_price) / entry_price
                    # Take Profit: Reversión hacia la media SMA20
                    if curr_close >= prev_sma:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Mean Reversion (SMA20)"
                    # Stop de Emergencia 3%
                    elif pnl_pct <= -0.03:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Emergency Stop 3%"
                    # Time-Stop (8 velas = 8h)
                    elif bars_held >= cand.max_holding_bars:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Time-Stop 8H"
                        
                    if exit_flag:
                        qty = notional / entry_price
                        gross_pnl = (exit_price - entry_price) * qty
                        fees = notional * 0.0016
                        net_pnl = gross_pnl - fees
                        trades.append({
                            'entry_idx': entry_idx,
                            'exit_idx': t,
                            'side': 'LONG',
                            'gross_pnl': gross_pnl,
                            'fees': fees,
                            'net_pnl': net_pnl,
                            'reason': exit_reason
                        })
                        in_pos = False
                        
                elif pos_side == 'SHORT':
                    pnl_pct = (entry_price - curr_close) / entry_price
                    # Take Profit: Reversión hacia la media SMA20
                    if curr_close <= prev_sma:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Mean Reversion (SMA20)"
                    # Stop de Emergencia 3%
                    elif pnl_pct <= -0.03:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Emergency Stop 3%"
                    # Time-Stop (8 velas = 8h)
                    elif bars_held >= cand.max_holding_bars:
                        exit_flag = True
                        exit_price = curr_close
                        exit_reason = "Time-Stop 8H"
                        
                    if exit_flag:
                        qty = notional / entry_price
                        gross_pnl = (entry_price - exit_price) * qty
                        fees = notional * 0.0016
                        net_pnl = gross_pnl - fees
                        trades.append({
                            'entry_idx': entry_idx,
                            'exit_idx': t,
                            'side': 'SHORT',
                            'gross_pnl': gross_pnl,
                            'fees': fees,
                            'net_pnl': net_pnl,
                            'reason': exit_reason
                        })
                        in_pos = False
                        
        return trades

    def evaluate_split(self, trades: List[Dict[str, Any]], initial_cap: float = 5000.0) -> Tuple[float, int, float, float, float, float]:
        if not trades:
            return 0.0, 0, 0.0, 0.0, 0.0, 0.0
            
        df = pd.DataFrame(trades)
        wins = df[df['net_pnl'] > 0]
        losses = df[df['net_pnl'] <= 0]
        
        gw = wins['net_pnl'].sum() if not wins.empty else 0.0
        gl = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
        pf = gw / gl
        wr = (len(wins) / len(df)) * 100.0
        net_pnl = df['net_pnl'].sum()
        exp = df['net_pnl'].mean()
        
        equity = initial_cap + df['net_pnl'].cumsum()
        peak = equity.cummax()
        max_dd_pct = ((peak - equity).max() / initial_cap) * 100.0
        
        return pf, len(df), wr, net_pnl, exp, max_dd_pct

    def validate_candidate(self, cand: FundingCandidate) -> FundingEvaluationResult:
        train_trades, test_trades, val_trades = [], [], []
        
        for sym, df_p in self.prepared_data.items():
            df_train = df_p[(df_p['timestamp'] >= '2022-01-01') & (df_p['timestamp'] < '2024-01-01')].reset_index(drop=True)
            df_test = df_p[(df_p['timestamp'] >= '2024-01-01') & (df_p['timestamp'] < '2025-01-01')].reset_index(drop=True)
            df_val = df_p[(df_p['timestamp'] >= '2024-01-01') & (df_p['timestamp'] <= '2026-08-16')].reset_index(drop=True)
            
            train_trades.extend(self.simulate_asset(df_train, cand))
            test_trades.extend(self.simulate_asset(df_test, cand))
            val_trades.extend(self.simulate_asset(df_val, cand))
            
        train_pf, _, _, _, _, _ = self.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = self.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = self.evaluate_split(val_trades)
        
        # Métrica de Supervivencia OOS: PF > 1.30 AND Max DD < 15.0% AND Trades > 100 AND Expectancy > 0.0
        passed = (val_pf > 1.30) and (val_dd < 15.0) and (val_cnt > 100) and (val_exp > 0.0)
        
        if passed:
            verdict = "PROMOTED_TO_PAPER (PF>1.3, DD<15%, Trades>100, Exp>0)"
        else:
            reasons = []
            if val_pf <= 1.30: reasons.append(f"PF={val_pf:.2f}<=1.30")
            if val_dd >= 15.0: reasons.append(f"DD={val_dd:.1f}%>=15%")
            if val_cnt <= 100: reasons.append(f"Trades={val_cnt}<=100")
            if val_exp <= 0.0: reasons.append(f"Exp=${val_exp:.2f}<=0")
            verdict = f"KILLED: {' | '.join(reasons)}"
            
        return FundingEvaluationResult(
            candidate_id=cand.id,
            family=cand.family,
            train_pf=train_pf,
            test_pf=test_pf,
            val_pf=val_pf,
            val_trades=val_cnt,
            val_win_rate=val_wr,
            val_net_pnl=val_net,
            val_expectancy=val_exp,
            val_max_dd_pct=val_dd,
            passed=passed,
            verdict=verdict
        )
