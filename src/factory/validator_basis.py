from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

@dataclass
class BasisCandidate:
    id: str
    family: str
    entry_z: float
    max_holding_bars: int
    basis_window: int

@dataclass
class BasisEvaluationResult:
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

class BasisValidator:
    """Validador Walk-Forward para convergencia de Basis (Spot vs Perp)."""
    
    def __init__(self, data_dir: str = "data/historical", basis_dir: str = "data/historical_basis", deriv_dir: str = "data/historical_derivatives"):
        self.data_dir = Path(data_dir)
        self.basis_dir = Path(basis_dir)
        self.deriv_dir = Path(deriv_dir)
        self.cached_pairs = {}
        self.load_cache()

    def load_cache(self):
        """Carga y sincroniza los datos de Spot, Perpetual y Funding."""
        symbols = ['BTCUSDT', 'ETHUSDT']
        
        for sym in symbols:
            spot_file = self.data_dir / f"{sym}_1h_2022_2026.csv"
            perp_file = self.basis_dir / f"{sym}_1h_2022_2026.csv"
            funding_file = self.deriv_dir / f"{sym}_funding_rate_2022_2026.csv"
            
            if not spot_file.exists() or not perp_file.exists() or not funding_file.exists():
                print(f"⚠️ Faltan datos para {sym}, saltando...")
                continue
                
            df_spot = pd.read_csv(spot_file)[['timestamp', 'close']].rename(columns={'close': 'spot_close'})
            df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
            
            df_perp = pd.read_csv(perp_file)[['timestamp', 'close']].rename(columns={'close': 'perp_close'})
            df_perp['timestamp'] = pd.to_datetime(df_perp['timestamp'])
            
            df_fund = pd.read_csv(funding_file)[['fundingTime', 'fundingRate']].rename(columns={'fundingTime': 'timestamp', 'fundingRate': 'funding_rate'})
            df_fund['timestamp'] = pd.to_datetime(df_fund['timestamp'])
            
            # Inner join to ensure perfect sync
            df_merged = pd.merge(df_spot, df_perp, on='timestamp', how='inner').sort_values('timestamp').reset_index(drop=True)
            
            # Left join funding (not every 1H bar has funding, mostly 8H)
            df_merged = pd.merge(df_merged, df_fund, on='timestamp', how='left')
            df_merged['funding_rate'] = df_merged['funding_rate'].fillna(0.0)
            
            self.cached_pairs[sym] = df_merged

    def simulate_series(self, df_merged: pd.DataFrame, cand: BasisCandidate) -> List[Dict]:
        from src.strategies.basis_spot_perp import BasisSpotPerpStrategy
        
        strategy = BasisSpotPerpStrategy(cand.entry_z, cand.max_holding_bars, cand.basis_window)
        # Re-create spot/perp separation just for the compute function
        df_spot = df_merged[['timestamp', 'spot_close']].rename(columns={'spot_close': 'close'})
        df_perp = df_merged[['timestamp', 'perp_close']].rename(columns={'perp_close': 'close'})
        
        df_ind = strategy.compute_indicators(df_spot, df_perp)
        
        # Merge back funding rate
        df_ind = pd.merge(df_ind, df_merged[['timestamp', 'funding_rate']], on='timestamp', how='left')
        
        trades = []
        in_pos = False
        pos_side = None # 'SHORT_PERP' means LONG Spot, SHORT Perp. 'LONG_PERP' means SHORT Spot, LONG Perp
        
        entry_idx = 0
        entry_spot = 0.0
        entry_perp = 0.0
        acc_funding = 0.0
        
        fee_rate = 0.0008 # 0.08% per leg
        
        # Convert to arrays for speed
        basis_z = df_ind['basis_z'].values
        spot_close = df_ind['spot_close'].values
        perp_close = df_ind['perp_close'].values
        funding_rate = df_ind['funding_rate'].values
        
        n_bars = len(df_ind)
        
        for t in range(cand.basis_window + 1, n_bars - 1):
            curr_z = basis_z[t]
            
            if np.isnan(curr_z):
                continue
                
            # Funding is paid/received at exact funding timestamps if holding a position
            if in_pos:
                curr_funding = funding_rate[t]
                if curr_funding != 0.0:
                    # Si somos SHORT perp, recibimos funding si es positivo (cashflow > 0)
                    # Si somos LONG perp, pagamos funding si es positivo (cashflow < 0)
                    if pos_side == 'SHORT_PERP':
                        acc_funding += (1.0 * curr_funding)  # Recibimos
                    else:
                        acc_funding -= (1.0 * curr_funding)  # Pagamos
                        
            if not in_pos:
                if curr_z >= cand.entry_z:
                    in_pos = True
                    pos_side = 'SHORT_PERP'
                    entry_idx = t + 1
                    entry_spot = spot_close[t + 1]
                    entry_perp = perp_close[t + 1]
                    acc_funding = 0.0
                elif curr_z <= -cand.entry_z:
                    in_pos = True
                    pos_side = 'LONG_PERP'
                    entry_idx = t + 1
                    entry_spot = spot_close[t + 1]
                    entry_perp = perp_close[t + 1]
                    acc_funding = 0.0
            else:
                holding = t - entry_idx
                exit_flag = False
                
                if holding >= cand.max_holding_bars:
                    exit_flag = True
                elif pos_side == 'SHORT_PERP' and curr_z <= 0:
                    exit_flag = True
                elif pos_side == 'LONG_PERP' and curr_z >= 0:
                    exit_flag = True
                    
                if exit_flag:
                    exit_idx = t + 1
                    exit_spot = spot_close[exit_idx]
                    exit_perp = perp_close[exit_idx]
                    
                    # PnL % calculation
                    # Since nominal size is identical for both legs (e.g. 1 USD each leg, total 2 USD capital allocated):
                    if pos_side == 'SHORT_PERP':
                        pnl_spot = (exit_spot / entry_spot) - 1.0
                        pnl_perp = -1.0 * ((exit_perp / entry_perp) - 1.0)
                    else:
                        pnl_spot = -1.0 * ((exit_spot / entry_spot) - 1.0)
                        pnl_perp = (exit_perp / entry_perp) - 1.0
                        
                    # Total PnL is average of the two legs
                    gross_pnl_pct = (pnl_spot + pnl_perp) / 2.0
                    
                    # Fees: 0.08% entry spot, 0.08% exit spot, 0.08% entry perp, 0.08% exit perp
                    # Total fees applied to 1 capital equivalent = 0.0016
                    total_fee = 0.0016
                    
                    # Funding cashflow was relative to nominal. Since it's applied to 1 of 2 legs, 
                    # funding impact on total capital is acc_funding / 2
                    funding_impact = acc_funding / 2.0
                    
                    net_pnl_pct = gross_pnl_pct - total_fee + funding_impact
                    net_pnl_usd = net_pnl_pct * 1000.0 # assuming $1000 base capital
                    
                    trades.append({
                        'side': pos_side,
                        'entry_idx': entry_idx,
                        'exit_idx': exit_idx,
                        'holding': holding,
                        'net_pnl': net_pnl_usd
                    })
                    
                    in_pos = False
                    
        return trades

    def evaluate_split(self, trades: List[Dict], initial_cap: float = 10000.0) -> Tuple[float, int, float, float, float, float]:
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

    def validate_candidate(self, cand: BasisCandidate) -> BasisEvaluationResult:
        train_trades, test_trades, val_trades = [], [], []
        
        for sym, df_merged in self.cached_pairs.items():
            df_train = df_merged[(df_merged['timestamp'] >= '2022-01-01') & (df_merged['timestamp'] < '2024-01-01')].reset_index(drop=True)
            df_test = df_merged[(df_merged['timestamp'] >= '2024-01-01') & (df_merged['timestamp'] < '2025-01-01')].reset_index(drop=True)
            df_val = df_merged[(df_merged['timestamp'] >= '2024-01-01') & (df_merged['timestamp'] <= '2026-08-16')].reset_index(drop=True)
            
            if not df_train.empty:
                train_trades.extend(self.simulate_series(df_train, cand))
            if not df_test.empty:
                test_trades.extend(self.simulate_series(df_test, cand))
            if not df_val.empty:
                val_trades.extend(self.simulate_series(df_val, cand))
            
        train_pf, _, _, _, _, _ = self.evaluate_split(train_trades)
        test_pf, _, _, _, _, _ = self.evaluate_split(test_trades)
        val_pf, val_cnt, val_wr, val_net, val_exp, val_dd = self.evaluate_split(val_trades)
        
        # Métrica única de supervivencia (según USER): PF > 1.30, DD < 15.0%, Trades >= 100, Expectancy > 0
        passed = (val_pf > 1.30) and (val_dd < 15.0) and (val_cnt >= 100) and (val_exp > 0)
        
        if passed:
            verdict = "PROMOTED_TO_PAPER (PF>1.3, DD<15%, Trades>=100, Exp>0)"
        else:
            reasons = []
            if val_pf <= 1.30: reasons.append(f"PF={val_pf:.2f}<=1.30")
            if val_dd >= 15.0: reasons.append(f"DD={val_dd:.1f}%>=15%")
            if val_cnt < 100: reasons.append(f"Trades={val_cnt}<100")
            if val_exp <= 0: reasons.append(f"Exp={val_exp:.2f}<=0")
            verdict = " | ".join(reasons)
            
        return BasisEvaluationResult(
            candidate_id=cand.id,
            train_pf=train_pf, test_pf=test_pf, val_pf=val_pf,
            val_trades=val_cnt, val_win_rate=val_wr,
            val_net_pnl=val_net, val_expectancy=val_exp,
            val_max_dd_pct=val_dd, passed=passed, verdict=verdict
        )
