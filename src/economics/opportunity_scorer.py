"""
Economic Opportunity Scorer (Phase 2 Economic Redesign - Track B)
Calculates Economic Opportunity Score (EOS) across 8 non-trading & trading revenue families.
"""

from typing import Dict, Any


class OpportunityScorer:
    """
    Computes Economic Opportunity Score (EOS):
    (EconomicValue * Evidence * Automation * Recurrence * Speed * CapitalEfficiency * Feasibility * StrategicFit) /
    (Risk * DistributionDifficulty * RegulatoryBurden * TimeToRevenue)
    """

    def compute_eos(self, opp: Dict[str, Any]) -> float:
        # Numerator Factors (1-10)
        economic_value = float(opp.get("economic_value", 5.0))
        evidence = float(opp.get("evidence_strength", 5.0))
        automation = float(opp.get("automation_ratio", 0.5)) * 10.0  # Scale 0.0-1.0 to 0-10
        recurrence = float(opp.get("recurrence_score", 5.0))
        speed = float(opp.get("speed_to_mvp", 5.0))
        capital_eff = float(opp.get("capital_efficiency", 8.0))
        feasibility = float(opp.get("technical_feasibility", 8.0))
        strategic_fit = float(opp.get("strategic_fit", 8.0))

        num = (economic_value * evidence * automation * recurrence * speed * capital_eff * feasibility * strategic_fit)

        # Denominator Factors (1-10, clamped min 1.0)
        risk = max(1.0, float(opp.get("downside_risk", 3.0)))
        dist_diff = max(1.0, float(opp.get("distribution_difficulty", 4.0)))
        reg_burden = max(1.0, float(opp.get("regulatory_burden", 2.0)))
        time_to_rev = max(1.0, float(opp.get("time_to_first_revenue_days", 14.0)) / 2.0)  # Normalized

        denom = risk * dist_diff * reg_burden * time_to_rev

        eos = num / denom
        return round(float(eos), 2)
