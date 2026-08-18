"""
Factory Validator for CROSS_SECTIONAL_MOMENTUM_4H
Ejecuta backtesting Walk-Forward para Momentum Transversal 4H:
- Universo: BTC, ETH, SOL, AVAX, LINK, DOT
- Long #1 (Winner), Short #6 (Loser) a N periodos de lookback
- Rebalanceo cada 4h con deducción de 0.16% de comisiones por rotación
- Train: 2022-2023, Test: 2024, Valid OOS: 2024-2026
- Criterio de Supervivencia:
  Validation PF > 1.30 AND Max DD < 15.0% AND Trades > 100 AND Expectancy > 0.0
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from src.strategies.cross_sectional_momentum_4h import CrossSectionalMomentum4H
from src.factory.generator_momentum import MomentumCandidate

@dataclass
class MomentumEvaluationResult:
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

class MomentumValidator:
    """Validador Walk-Forward para Momentum Transversal 4H."""
    
    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.universe = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
        self.cached_4h_data = {}
        self.load_and_resample()

    def load_and_resample(self):
        """Carga en RAM los CSVs de 1h y los agrega a 4h."""
        for sym in self.universe:
            file_path = self.data_dir / f"{sym}_1h_2022_2026.csv"
            if file_path.exists():
                df_1h = pd.read_csv(file_path)
                df_4h = CrossSectionalMomentum4H.resample_1h_to_4h(df_1h)
                self.cached_4h_data[sym] = df_4h

    def simulate_universe(
        self,
        df_closes: pd.DataFrame,
        cand: MomentumCandidate,
        notional_per_leg: float = 150.0
    ) -> List[Dict[str, Any]]:
        """
        Simula la estrategia Long #1 / Short #6 con rebalanceo en cada vela 4h.
        """
        n = cand.n_lookback
        timestamps = df_closes.index
        num_bars = len(df_closes)
        
        if num_bars <= n + 2:
            return []
            
        # Retornos a N barras: R[t] = Close[t] / Close[t-N] - 1
        returns_n = df_closes.pct_change(n)
        
        trades = []
        curr_long_sym = None
        curr_short_sym = None
        
        long_entry_price = 0.0
        long_entry_idx = 0
        long_accum_gross = 0.0
        
        short_entry_price = 0.0
        short_entry_idx = 0
        short_accum_gross = 0.0
        
        # Iterar a través de las barras (sin look-ahead)
        for t in range(n + 1, num_bars - 1):
            # Rankeo al cierre de la vela t
            rank_series = returns_n.iloc[t].dropna()
            if len(rank_series) < len(self.universe):
                continue
                
            sorted_assets = rank_series.sort_values(ascending=False)
            target_long_sym = sorted_assets.index[0]   # #1 Winner
            target_short_sym = sorted_assets.index[-1]  # #6 Loser
            
            # Retorno de la siguiente vela (t -> t+1)
            p_long_t = df_closes[target_long_sym].iloc[t]
            p_long_t1 = df_closes[target_long_sym].iloc[t+1]
            ret_long = (p_long_t1 - p_long_t) / p_long_t
            
            p_short_t = df_closes[target_short_sym].iloc[t]
            p_short_t1 = df_closes[target_short_sym].iloc[t+1]
            ret_short = - (p_short_t1 - p_short_t) / p_short_t
            
            gross_long_bar = notional_per_leg * ret_long
            gross_short_bar = notional_per_leg * ret_short
            
            # 1. Gestión de Pata LONG
            if curr_long_sym != target_long_sym:
                # Si teníamos una posición abierta previa, cerrarla y registrar el trade
                if curr_long_sym is not None:
                    fees = notional_per_leg * 0.0016 # 0.16% roundtrip
                    net_pnl = long_accum_gross - fees
                    trades.append({
                        'side': 'LONG',
                        'symbol': curr_long_sym,
                        'entry_time': timestamps[long_entry_idx],
                        'exit_time': timestamps[t],
                        'gross_pnl': long_accum_gross,
                        'fees': fees,
                        'net_pnl': net_pnl
                    })
                # Abrir nueva pata Long
                curr_long_sym = target_long_sym
                long_entry_price = p_long_t
                long_entry_idx = t
                long_accum_gross = gross_long_bar
            else:
                long_accum_gross += gross_long_bar
                
            # 2. Gestión de Pata SHORT
            if curr_short_sym != target_short_sym:
                # Si teníamos una posición abierta previa, cerrarla y registrar el trade
                if curr_short_sym is not None:
                    fees = notional_per_leg * 0.0016 # 0.16% roundtrip
                    net_pnl = short_accum_gross - fees
                    trades.append({
                        'side': 'SHORT',
                        'symbol': curr_short_sym,
                        'entry_time': timestamps[short_entry_idx],
                        'exit_time': timestamps[t],
                        'gross_pnl': short_accum_gross,
                        'fees': fees,
                        'net_pnl': net_pnl
                    })
                # Abrir nueva pata Short
                curr_short_sym = target_short_sym
                short_entry_price = p_short_t
                short_entry_idx = t
                short_accum_gross = gross_short_bar
            else:
                short_accum_gross += gross_short_bar
                
        # Cerrar posiciones finales si quedan abiertas
        if curr_long_sym is not None:
            fees = notional_per_leg * 0.0016
            trades.append({
                'side': 'LONG',
                'symbol': curr_long_sym,
                'entry_time': timestamps[long_entry_idx],
                'exit_time': timestamps[-1],
                'gross_pnl': long_accum_gross,
                'fees': fees,
                'net_pnl': long_accum_gross - fees
            })
            
        if curr_short_sym is not None:
            fees = notional_per_leg * 0.0016
            trades.append({
                'side': 'SHORT',
                'symbol': curr_short_sym,
                'entry_time': timestamps[short_entry_idx],
                'exit_time': timestamps[-1],
                'gross_pnl': short_accum_gross,
                'fees': fees,
                'net_pnl': short_accum_gross - fees
            })
            
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

    def validate_candidate(self, cand: MomentumCandidate) -> MomentumEvaluationResult:
        # Construir matriz de precios de cierre 4h alineados
        close_series = {}
        for sym in self.universe:
            if sym in self.cached_4h_data:
                df = self.cached_4h_data[sym]
                close_series[sym] = df.set_index('timestamp')['close']
                
        df_all_closes = pd.DataFrame(close_series).dropna().sort_index()
        
        # Splits
        df_train = df_all_closes[(df_all_closes.index >= '2022-01-01') & (df_all_closes.index < '2024-01-01')]
        df_test = df_all_closes[(df_all_closes.index >= '2024-01-01') & (df_all_closes.index < '2025-01-01')]
        df_val = df_all_closes[(df_all_closes.index >= '2024-01-01') & (df_all_closes.index <= '2026-08-16')]
        
        train_trades = self.simulate_universe(df_train, cand)
        test_trades = self.simulate_universe(df_test, cand)
        val_trades = self.simulate_universe(df_val, cand)
        
        train_pf, _, _, _, _, _ = self.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = self.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = self.evaluate_split(val_trades)
        
        # Métrica de Supervivencia OOS 2024-2026: PF > 1.30 AND Max DD < 15.0% AND Trades > 100 AND Expectancy > 0.0
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
            
        return MomentumEvaluationResult(
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
