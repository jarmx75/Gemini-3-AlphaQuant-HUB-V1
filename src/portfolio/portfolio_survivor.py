"""
Portfolio Survivor Evaluator (Phase 2 Economic Redesign)
Evaluates candidate strategies or factors for portfolio admission based on marginal risk/return contribution.

RELEASES HARD GATES:
- Sharpe improvement is tracked as a metric, NOT enforced as a +0.15 hard gate.
- Evaluates marginal expectancy, marginal drawdown, correlation, diversification ratio, and stress tests.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PortfolioSurvivorEvaluator:
    """
    Evaluator for Portfolio Survivor classification.
    """

    def __init__(self, max_marginal_dd_pct: float = 2.0, max_correlation: float = 0.30, fee_slippage_bps: float = 20.0):
        self.max_marginal_dd_pct = max_marginal_dd_pct
        self.max_correlation = max_correlation
        self.friction = fee_slippage_bps / 10000.0

    def evaluate_candidate(
        self,
        existing_portfolio_returns: pd.Series,
        candidate_returns: pd.Series,
        candidate_name: str = "Candidate_Strategy"
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate strategy against an existing portfolio.
        """
        common_idx = existing_portfolio_returns.index.intersection(candidate_returns.index)
        if len(common_idx) < 30:
            return {
                "candidate_name": candidate_name,
                "status": "REJECTED_INSUFFICIENT_DATA",
                "reason": "Fewer than 30 overlapping return periods."
            }

        port_ret = existing_portfolio_returns.loc[common_idx]
        cand_ret = candidate_returns.loc[common_idx]

        # 1. Existing Portfolio Metrics
        ann_ret_existing = float(port_ret.mean() * 252)
        ann_vol_existing = float(port_ret.std() * np.sqrt(252))
        cum_exp = (1 + port_ret).cumprod()
        dd_existing = abs(float(((cum_exp - cum_exp.cummax()) / cum_exp.cummax()).min())) * 100.0
        sharpe_existing = float((ann_ret_existing - 0.02) / ann_vol_existing) if ann_vol_existing > 0 else 0.0

        # 2. Combined Portfolio (Equal Weight / Risk Parity 80/20)
        combined_ret = 0.80 * port_ret + 0.20 * cand_ret
        ann_ret_combined = float(combined_ret.mean() * 252)
        ann_vol_combined = float(combined_ret.std() * np.sqrt(252))
        cum_comb = (1 + combined_ret).cumprod()
        dd_combined = abs(float(((cum_comb - cum_comb.cummax()) / cum_comb.cummax()).min())) * 100.0
        sharpe_combined = float((ann_ret_combined - 0.02) / ann_vol_combined) if ann_vol_combined > 0 else 0.0

        # 3. Marginal Contributions
        marginal_expectancy_pct = (ann_ret_combined - ann_ret_existing) * 100.0
        marginal_dd_pct = dd_combined - dd_existing
        sharpe_delta = sharpe_combined - sharpe_existing

        # 4. Correlation
        corr = float(port_ret.corr(cand_ret))

        # 5. Diversification Effect
        weighted_vols = 0.80 * ann_vol_existing + 0.20 * float(cand_ret.std() * np.sqrt(252))
        div_ratio_existing = 1.0
        div_ratio_combined = float(weighted_vols / ann_vol_combined) if ann_vol_combined > 0 else 1.0
        div_effect_positive = div_ratio_combined > div_ratio_existing

        # 6. Cost-Adjusted Expectancy
        cand_net_ret = cand_ret - self.friction
        cost_adjusted_exp_pct = float(cand_net_ret.mean() * 252 * 100.0)

        # 7. Stress Test (2x Volatility shock)
        stress_ret = 0.80 * port_ret + 0.20 * (cand_ret * 2.0)
        cum_stress = (1 + stress_ret).cumprod()
        stress_dd = abs(float(((cum_stress - cum_stress.cummax()) / cum_stress.cummax()).min())) * 100.0
        stress_test_pass = stress_dd < 25.0

        # Evaluation Decision
        survivor_checks = {
            "positive_marginal_expectancy": marginal_expectancy_pct > 0,
            "acceptable_marginal_dd": marginal_dd_pct <= self.max_marginal_dd_pct,
            "low_correlation": corr <= self.max_correlation,
            "positive_diversification_effect": div_effect_positive,
            "cost_adjusted_expectancy_positive": cost_adjusted_exp_pct > 0,
            "stress_test_passed": stress_test_pass
        }

        is_portfolio_survivor = all(survivor_checks.values())

        return {
            "candidate_name": candidate_name,
            "status": "PORTFOLIO_SURVIVOR" if is_portfolio_survivor else "REJECTED_PORTFOLIO_SURVIVOR",
            "eval_checks": survivor_checks,
            "metrics": {
                "correlation_with_portfolio": round(corr, 4),
                "marginal_expectancy_pct": round(marginal_expectancy_pct, 2),
                "marginal_dd_pct": round(marginal_dd_pct, 2),
                "sharpe_existing": round(sharpe_existing, 2),
                "sharpe_combined": round(sharpe_combined, 2),
                "sharpe_improvement_delta": round(sharpe_delta, 2),
                "diversification_ratio_combined": round(div_ratio_combined, 2),
                "cost_adjusted_expectancy_pct": round(cost_adjusted_exp_pct, 2),
                "stress_test_max_dd_pct": round(stress_dd, 2)
            }
        }
