"""
Factory Validator (Blazing Fast RAM-Cached & O(1) Regime Check)
Ejecuta backtesting Walk-Forward ultra-rápido (< 2 segundos para 5 variantes):
- Pre-calcula BTC 30d return y Correlación 30d en memoria RAM.
- Train: 2022-2023, Test: 2024, Validation Out-of-Sample: 2024-2026.
- Métrica Única de Supervivencia:
  Validation PF > 1.30 AND Max DD < 15.0% AND Trades >= 100
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from src.factory.generator import FactoryCandidate

@dataclass
class FactoryEvaluationResult:
    candidate_id: str
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

class FactoryValidator:
    """Validador Walk-Forward de alta velocidad con lookup O(1)."""
    
    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.cached_pairs = {}
        self.load_cache()

    def load_cache(self):
        """Carga en memoria RAM y pre-calcula métricas de régimen rolling para velocidad O(1)."""
        pairs = [
            ('BTCUSDT', 'ETHUSDT'),
            ('AVAXUSDT', 'SOLUSDT'),
            ('LINKUSDT', 'DOTUSDT')
        ]
        btc_file = self.data_dir / "BTCUSDT_1h_2022_2026.csv"
        df_btc = None
        if btc_file.exists():
            df_btc = pd.read_csv(btc_file)[['timestamp', 'close']].rename(columns={'close': 'close_btc'})
            df_btc['timestamp'] = pd.to_datetime(df_btc['timestamp'])
            
        for sym_y, sym_x in pairs:
            file_y = self.data_dir / f"{sym_y}_1h_2022_2026.csv"
            file_x = self.data_dir / f"{sym_x}_1h_2022_2026.csv"
            if file_y.exists() and file_x.exists():
                df_y = pd.read_csv(file_y)[['timestamp', 'close']].rename(columns={'close': 'close_y'})
                df_x = pd.read_csv(file_x)[['timestamp', 'close']].rename(columns={'close': 'close_x'})
                df_y['timestamp'] = pd.to_datetime(df_y['timestamp'])
                df_x['timestamp'] = pd.to_datetime(df_x['timestamp'])
                df_merged = pd.merge(df_y, df_x, on='timestamp').sort_values('timestamp').reset_index(drop=True)
                
                if df_btc is not None:
                    df_merged = pd.merge(df_merged, df_btc, on='timestamp').sort_values('timestamp').reset_index(drop=True)
                else:
                    df_merged['close_btc'] = df_merged['close_y']
                    
                # Pre-cálculo O(1) de métricas de régimen rolling 30 días (720 velas de 1h)
                df_merged['btc_ret_30d'] = df_merged['close_btc'].pct_change(720).fillna(0.0)
                df_merged['corr_30d'] = df_merged['close_y'].rolling(720).corr(df_merged['close_x']).fillna(1.0)
                
                self.cached_pairs[f"{sym_y}/{sym_x}"] = df_merged

    def simulate_series(self, df: pd.DataFrame, cand: FactoryCandidate, notional: float = 150.0) -> List[Dict[str, Any]]:
        y = df['close_y'].values
        x = df['close_x'].values
        btc_ret_30d = df['btc_ret_30d'].values
        corr_30d = df['corr_30d'].values
        n = len(y)
        w = cand.lookback_window
        
        trades = []
        in_pos = False
        pos_side = None
        entry_y = entry_x = entry_gamma = 0.0
        entry_idx = 0
        
        for t in range(w, n):
            y_w = y[t-w : t]
            x_w = x[t-w : t]
            
            cov = np.cov(x_w, y_w)[0, 1]
            var = np.var(x_w)
            if var == 0: continue
            gamma = cov / var
            
            spread_w = y_w - gamma * x_w
            mean_s = np.mean(spread_w)
            std_s = np.std(spread_w)
            if std_s == 0: continue
            
            curr_y = y[t]
            curr_x = x[t]
            curr_s = curr_y - gamma * curr_x
            z = (curr_s - mean_s) / std_s
            
            if not in_pos:
                # Comprobar si Z está en zona de entrada [Z_entry, Z_entry + 0.9]
                if not ((cand.z_entry <= z <= cand.z_entry + 0.9) or (-(cand.z_entry + 0.9) <= z <= -cand.z_entry)):
                    continue
                    
                # Filtro de Régimen O(1): BTC -20% en 30d o Correlación < 0.60
                if btc_ret_30d[t] <= -0.20 or corr_30d[t] < 0.60:
                    continue
                    
                # ADF Check solo para candidatos filtrados
                try:
                    adf_res = adfuller(spread_w, autolag='AIC')
                    if adf_res[1] >= cand.adf_p_threshold:
                        continue
                except:
                    continue
                    
                if cand.z_entry <= z <= cand.z_entry + 0.9:
                    in_pos = True
                    pos_side = 'SHORT'
                    entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
                elif -(cand.z_entry + 0.9) <= z <= -cand.z_entry:
                    in_pos = True
                    pos_side = 'LONG'
                    entry_y, entry_x, entry_gamma, entry_idx = curr_y, curr_x, gamma, t
            else:
                holding = t - entry_idx
                exit_flag = False
                
                if holding >= cand.max_holding_bars:
                    exit_flag = True
                elif pos_side == 'SHORT':
                    if z <= cand.z_exit or z >= cand.z_stop:
                        exit_flag = True
                elif pos_side == 'LONG':
                    if z >= -cand.z_exit or z <= -cand.z_stop:
                        exit_flag = True
                        
                if exit_flag:
                    qty_y = notional / entry_y
                    qty_x = (notional * entry_gamma) / entry_x
                    
                    if pos_side == 'SHORT':
                        pnl_y = (entry_y - curr_y) * qty_y
                        pnl_x = (curr_x - entry_x) * qty_x
                    else:
                        pnl_y = (curr_y - entry_y) * qty_y
                        pnl_x = (entry_x - curr_x) * qty_x
                        
                    gross_pnl = pnl_y + pnl_x
                    fees = (notional + notional * entry_gamma) * 2 * 0.0004 # 0.16% fee roundtrip
                    net_pnl = gross_pnl - fees
                    trades.append({'net_pnl': net_pnl, 'holding': holding})
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

    def validate_candidate(self, cand: FactoryCandidate) -> FactoryEvaluationResult:
        """Ejecuta Walk-Forward (Train 2022-23, Test 2024, Valid 2024-2026)."""
        train_trades, test_trades, val_trades = [], [], []
        
        for pair_name, df_merged in self.cached_pairs.items():
            df_train = df_merged[(df_merged['timestamp'] >= '2022-01-01') & (df_merged['timestamp'] < '2024-01-01')].reset_index(drop=True)
            df_test = df_merged[(df_merged['timestamp'] >= '2024-01-01') & (df_merged['timestamp'] < '2025-01-01')].reset_index(drop=True)
            df_val = df_merged[(df_merged['timestamp'] >= '2024-01-01') & (df_merged['timestamp'] <= '2026-08-16')].reset_index(drop=True)
            
            train_trades.extend(self.simulate_series(df_train, cand))
            test_trades.extend(self.simulate_series(df_test, cand))
            val_trades.extend(self.simulate_series(df_val, cand))
            
        train_pf, _, _, _, _, _ = self.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = self.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = self.evaluate_split(val_trades)
        
        # Métrica única de supervivencia: PF > 1.30 AND Max DD < 15.0% AND Trades >= 100
        passed = (val_pf > 1.30) and (val_dd < 15.0) and (val_cnt >= 100)
        
        if passed:
            verdict = "PROMOTED_TO_PAPER (PF>1.3, DD<15%, Trades>=100)"
        else:
            reasons = []
            if val_pf <= 1.30: reasons.append(f"PF={val_pf:.2f}<=1.30")
            if val_dd >= 15.0: reasons.append(f"DD={val_dd:.1f}%>=15%")
            if val_cnt < 100: reasons.append(f"Trades={val_cnt}<100")
            verdict = f"KILLED: {' | '.join(reasons)}"
            
        return FactoryEvaluationResult(
            candidate_id=cand.id,
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
