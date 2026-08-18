"""
Factory Validator for VOLATILITY_COMPRESSION_BREAKOUT
Ejecuta backtesting Walk-Forward sobre 6 activos en velas 4h agregadas en RAM:
- Activos: BTC, ETH, SOL, AVAX, LINK, DOT
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

from src.strategies.volatility_compression_breakout import VolatilityCompressionBreakout4H
from src.factory.generator_volatility import VolatilityCandidate

@dataclass
class VolatilityEvaluationResult:
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

class VolatilityValidator:
    """Validador Walk-Forward para Volatility Compression Breakout."""
    
    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
        self.cached_4h_data = {}
        self.load_and_resample()

    def load_and_resample(self):
        """Carga en RAM los CSVs de 1h y los agrega a 4h."""
        for sym in self.symbols:
            file_path = self.data_dir / f"{sym}_1h_2022_2026.csv"
            if file_path.exists():
                df_1h = pd.read_csv(file_path)
                df_4h = VolatilityCompressionBreakout4H.resample_1h_to_4h(df_1h)
                self.cached_4h_data[sym] = df_4h

    def simulate_asset(
        self,
        df_4h: pd.DataFrame,
        cand: VolatilityCandidate,
        notional: float = 300.0
    ) -> List[Dict[str, Any]]:
        strategy = VolatilityCompressionBreakout4H(
            compression_percentile=cand.compression_percentile,
            breakout_lookback=cand.breakout_lookback,
            k_atr=cand.k_atr
        )
        df = strategy.compute_indicators(df_4h)
        
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        hh = df['highest_high'].values
        ll = df['lowest_low'].values
        atr = df['atr'].values
        is_comp = df['is_compressed'].values
        n = len(df)
        
        trades = []
        in_pos = False
        pos_side = None
        entry_price = 0.0
        trailing_stop = 0.0
        entry_idx = 0
        
        start_idx = max(cand.breakout_lookback, 120) + 16
        
        for t in range(start_idx, n):
            prev_c = closes[t-1]
            prev_hh = hh[t-1]
            prev_ll = ll[t-1]
            prev_atr = atr[t-1]
            prev_comp = is_comp[t-1]
            
            if np.isnan(prev_hh) or np.isnan(prev_ll) or np.isnan(prev_atr) or prev_atr <= 0:
                continue
                
            curr_open = opens[t]
            curr_high = highs[t]
            curr_low = lows[t]
            
            if not in_pos:
                # Entrada solo si hubo compresión reciente y ocurre breakout
                if prev_comp and prev_c > prev_hh:
                    in_pos = True
                    pos_side = 'LONG'
                    entry_price = curr_open
                    trailing_stop = entry_price - (cand.k_atr * prev_atr)
                    entry_idx = t
                elif prev_comp and prev_c < prev_ll:
                    in_pos = True
                    pos_side = 'SHORT'
                    entry_price = curr_open
                    trailing_stop = entry_price + (cand.k_atr * prev_atr)
                    entry_idx = t
            else:
                exit_flag = False
                exit_price = curr_open
                exit_reason = ""
                
                if pos_side == 'LONG':
                    # Trailing stop update
                    trailing_stop = max(trailing_stop, curr_high - (cand.k_atr * prev_atr))
                    if curr_low <= trailing_stop:
                        exit_flag = True
                        exit_price = min(curr_open, trailing_stop) if curr_open < trailing_stop else trailing_stop
                        exit_reason = "Trailing Stop"
                    elif prev_c < prev_ll:
                        exit_flag = True
                        exit_price = curr_open
                        exit_reason = "Opposite Breakout"
                        
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
                    # Trailing stop update
                    trailing_stop = min(trailing_stop, curr_low + (cand.k_atr * prev_atr))
                    if curr_high >= trailing_stop:
                        exit_flag = True
                        exit_price = max(curr_open, trailing_stop) if curr_open > trailing_stop else trailing_stop
                        exit_reason = "Trailing Stop"
                    elif prev_c > prev_hh:
                        exit_flag = True
                        exit_price = curr_open
                        exit_reason = "Opposite Breakout"
                        
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

    def validate_candidate(self, cand: VolatilityCandidate) -> VolatilityEvaluationResult:
        train_trades, test_trades, val_trades = [], [], []
        
        for sym, df_4h in self.cached_4h_data.items():
            df_train = df_4h[(df_4h['timestamp'] >= '2022-01-01') & (df_4h['timestamp'] < '2024-01-01')].reset_index(drop=True)
            df_test = df_4h[(df_4h['timestamp'] >= '2024-01-01') & (df_4h['timestamp'] < '2025-01-01')].reset_index(drop=True)
            df_val = df_4h[(df_4h['timestamp'] >= '2024-01-01') & (df_4h['timestamp'] <= '2026-08-16')].reset_index(drop=True)
            
            train_trades.extend(self.simulate_asset(df_train, cand))
            test_trades.extend(self.simulate_asset(df_test, cand))
            val_trades.extend(self.simulate_asset(df_val, cand))
            
        train_pf, _, _, _, _, _ = self.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = self.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = self.evaluate_split(val_trades)
        
        # Métrica de Supervivencia: PF > 1.30 AND Max DD < 15.0% AND Trades > 100 AND Expectancy > 0.0
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
            
        return VolatilityEvaluationResult(
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
