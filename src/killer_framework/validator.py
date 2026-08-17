"""
Validator Module: Motor de Validación Walk-Forward y Backtesting Riguroso
Aplica ventana móvil estricta (sin look-ahead bias), prueba de estacionariedad ADF
en cada paso, y deducción de costos reales de transacción (0.16% de comisiones por trade).
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from src.killer_framework.generator import StrategyCandidate

@dataclass
class ValidationReport:
    candidate_name: str
    period: str
    total_trades: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    max_drawdown_pct: float
    expectancy: float
    sharpe_ratio: float
    passed_filters: bool
    rejection_reason: str

class WalkForwardValidator:
    """Validador Walk-Forward sin sesgo de anticipación."""
    
    def __init__(self, fee_rate_per_leg: float = 0.0004):
        self.fee_roundtrip_total = fee_rate_per_leg * 4 # 0.04% x 2 patas x 2 aperturas/cierres = 0.16%
        
    def estimate_rolling_gamma(self, y: np.ndarray, x: np.ndarray) -> float:
        """Estima OLS gamma = Cov(x, y) / Var(x)."""
        cov = np.cov(x, y)[0, 1]
        var = np.var(x)
        if var == 0:
            return 1.0
        return float(cov / var)

    def test_spread_stationarity(self, spread: np.ndarray) -> Tuple[bool, float]:
        """Ejecuta Augmented Dickey-Fuller (ADF) sobre el spread residual."""
        try:
            res = adfuller(spread, autolag='AIC')
            p_val = float(res[1])
            return (p_val < 0.05, p_val)
        except:
            return (False, 1.0)

    def simulate_pair_strategy(
        self,
        df_y: pd.DataFrame,
        df_x: pd.DataFrame,
        candidate: StrategyCandidate,
        notional_per_leg: float = 150.0
    ) -> List[Dict[str, Any]]:
        """Simula la estrategia vela a vela sin look-ahead bias."""
        y_prices = df_y['close'].values
        x_prices = df_x['close'].values
        n = len(y_prices)
        
        trades = []
        in_pos = False
        pos_side = None
        entry_y = 0.0
        entry_x = 0.0
        entry_gamma = 1.0
        entry_idx = 0
        w = candidate.lookback_window
        
        for t in range(w, n):
            # Ventana estrictamente pasada [t-w : t]
            y_window = y_prices[t-w : t]
            x_window = x_prices[t-w : t]
            
            gamma = self.estimate_rolling_gamma(y_window, x_window)
            spread_window = y_window - gamma * x_window
            
            mean_s = np.mean(spread_window)
            std_s = np.std(spread_window)
            if std_s == 0:
                continue
                
            curr_y = y_prices[t]
            curr_x = x_prices[t]
            curr_spread = curr_y - gamma * curr_x
            z_score = (curr_spread - mean_s) / std_s
            
            if not in_pos:
                # Comprobar estacionariedad ADF
                is_stationary, p_val = self.test_spread_stationarity(spread_window)
                if not is_stationary:
                    continue
                    
                # Reglas de entrada con banda de histeresis para evitar stops inmediatos
                if candidate.z_entry_min <= z_score <= candidate.z_entry_max:
                    # Short Spread: Vender Y, Comprar X
                    in_pos = True
                    pos_side = 'SHORT_SPREAD'
                    entry_y, entry_x, entry_gamma = curr_y, curr_x, gamma
                    entry_idx = t
                elif -candidate.z_entry_max <= z_score <= -candidate.z_entry_min:
                    # Long Spread: Comprar Y, Vender X
                    in_pos = True
                    pos_side = 'LONG_SPREAD'
                    entry_y, entry_x, entry_gamma = curr_y, curr_x, gamma
                    entry_idx = t
            else:
                # Reglas de salida
                holding_periods = t - entry_idx
                exit_signal = False
                exit_reason = ""
                
                if pos_side == 'SHORT_SPREAD':
                    if z_score <= candidate.z_exit:
                        exit_signal = True
                        exit_reason = "Mean-Reverted (Target)"
                    elif z_score >= candidate.z_stop:
                        exit_signal = True
                        exit_reason = "Stop-Loss (Divergence)"
                elif pos_side == 'LONG_SPREAD':
                    if z_score >= -candidate.z_exit:
                        exit_signal = True
                        exit_reason = "Mean-Reverted (Target)"
                    elif z_score <= -candidate.z_stop:
                        exit_signal = True
                        exit_reason = "Stop-Loss (Divergence)"
                        
                if holding_periods >= candidate.half_life_max * 2:
                    exit_signal = True
                    exit_reason = "Time-Stop (Max Half-life)"
                    
                if exit_signal:
                    qty_y = notional_per_leg / entry_y
                    qty_x = (notional_per_leg * entry_gamma) / entry_x
                    
                    if pos_side == 'SHORT_SPREAD':
                        pnl_y = (entry_y - curr_y) * qty_y
                        pnl_x = (curr_x - entry_x) * qty_x
                    else:
                        pnl_y = (curr_y - entry_y) * qty_y
                        pnl_x = (entry_x - curr_x) * qty_x
                        
                    gross_pnl = pnl_y + pnl_x
                    total_notional_traded = (notional_per_leg + notional_per_leg * entry_gamma) * 2
                    fees = total_notional_traded * 0.0004 # 0.04% por lado
                    net_pnl = gross_pnl - fees
                    
                    trades.append({
                        'side': pos_side,
                        'entry_idx': entry_idx,
                        'exit_idx': t,
                        'holding_candles': holding_periods,
                        'gross_pnl': gross_pnl,
                        'fees': fees,
                        'net_pnl': net_pnl,
                        'reason': exit_reason
                    })
                    in_pos = False
                    
        return trades

    def evaluate_trades(self, trades: List[Dict[str, Any]], candidate_name: str, period_name: str) -> ValidationReport:
        """Calcula métricas institucionales cuantitativas sobre la serie de trades."""
        if not trades or len(trades) < 5:
            return ValidationReport(
                candidate_name=candidate_name,
                period=period_name,
                total_trades=len(trades),
                win_rate=0.0,
                profit_factor=0.0,
                net_pnl=0.0,
                max_drawdown_pct=0.0,
                expectancy=0.0,
                sharpe_ratio=0.0,
                passed_filters=False,
                rejection_reason="Insuficiente volumen de trades (<5)"
            )
            
        df = pd.DataFrame(trades)
        wins = df[df['net_pnl'] > 0]
        losses = df[df['net_pnl'] <= 0]
        
        total_trades = len(df)
        win_rate = (len(wins) / total_trades) * 100.0
        
        gross_profit = wins['net_pnl'].sum() if not wins.empty else 0.0
        gross_loss = abs(losses['net_pnl'].sum()) if not losses.empty else 1e-9
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        net_pnl = df['net_pnl'].sum()
        expectancy = df['net_pnl'].mean()
        
        # Max Drawdown
        equity_curve = df['net_pnl'].cumsum()
        peak = equity_curve.cummax()
        drawdown = peak - equity_curve
        max_dd_usd = drawdown.max()
        initial_capital = 4000.0
        max_dd_pct = (max_dd_usd / initial_capital) * 100.0
        
        # Sharpe Ratio anualizado (aproximado en 15m)
        returns = df['net_pnl']
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 96) if returns.std() > 0 else 0.0
        
        # Criterios del Killer: PF >= 1.1, Expectancy > 0, Max DD <= 15%
        passed = (profit_factor >= 1.1) and (expectancy > 0) and (max_dd_pct <= 15.0) and (total_trades >= 15)
        reason = "Aprobado" if passed else []
        if not passed:
            reasons = []
            if profit_factor < 1.1: reasons.append(f"PF={profit_factor:.2f} < 1.10")
            if expectancy <= 0: reasons.append(f"Expectancy={expectancy:.2f} <= 0")
            if max_dd_pct > 15.0: reasons.append(f"Max DD={max_dd_pct:.1f}% > 15%")
            if total_trades < 15: reasons.append(f"Trades={total_trades} < 15")
            reason = " | ".join(reasons)
            
        return ValidationReport(
            candidate_name=candidate_name,
            period=period_name,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            net_pnl=net_pnl,
            max_drawdown_pct=max_dd_pct,
            expectancy=expectancy,
            sharpe_ratio=sharpe,
            passed_filters=passed,
            rejection_reason=reason
        )
