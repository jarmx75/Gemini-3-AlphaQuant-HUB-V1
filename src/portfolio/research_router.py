"""
Autonomous Research Router & ResearchScore Ranker (Phase 2 Economic Redesign)
Evaluates candidate research hypotheses against 6 Hard Gates and ranks valid candidates by ResearchScore.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResearchRouter:
    """
    Autonomous Research Router with Hard Gates and Quantitative ResearchScore Ranking.
    """

    def calculate_research_score(
        self,
        novelty: float,              # 1-10
        data_availability: float,    # 1-10
        economic_plausibility: float,# 1-10
        expected_frequency: float,   # 1-10
        diversification_value: float,# 1-10
        research_cost: float         # 1-10
    ) -> float:
        """
        Calculates ResearchScore formula:
        (Novelty * DataAvailability * EconomicPlausibility * ExpectedFrequency * DiversificationValue) / ResearchCost
        """
        numerator = (novelty * data_availability * economic_plausibility * expected_frequency * diversification_value)
        cost_clamped = max(1.0, float(research_cost))
        score = numerator / cost_clamped
        return round(float(score), 2)

    def evaluate_hypothesis(self, candidate_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates candidate against 6 Hard Gates first, then computes ResearchScore.
        """
        gates = {
            "dataset_available": bool(candidate_spec.get("dataset_available", False)),
            "hypothesis_novel": bool(candidate_spec.get("hypothesis_novel", False)),
            "economic_mechanism_explicit": bool(candidate_spec.get("economic_mechanism_explicit", False)),
            "no_duplicate_or_rejected_family": not bool(candidate_spec.get("is_family_rejected", False)),
            "minimum_expected_opportunity_frequency": bool(candidate_spec.get("expected_frequency_value", 0) >= 3.0),
            "execution_cost_plausible": bool(candidate_spec.get("execution_cost_plausible", False))
        }

        all_gates_passed = all(gates.values())

        score = self.calculate_research_score(
            novelty=candidate_spec.get("novelty", 5.0),
            data_availability=candidate_spec.get("data_availability", 5.0),
            economic_plausibility=candidate_spec.get("economic_plausibility", 5.0),
            expected_frequency=candidate_spec.get("expected_frequency_value", 5.0),
            diversification_value=candidate_spec.get("diversification_value", 5.0),
            research_cost=candidate_spec.get("research_cost", 3.0)
        )

        status = "AUTHORIZED_FOR_RESEARCH" if all_gates_passed else "REJECTED_HARD_GATES"

        return {
            "family": candidate_spec.get("family", "UNKNOWN"),
            "status": status,
            "hard_gates": gates,
            "all_gates_passed": all_gates_passed,
            "research_score": score
        }

    def calculate_first_revenue_priority(self, candidate_spec: Dict[str, Any]) -> float:
        """
        Calculates FIRST_REVENUE Priority Score:
        RevenueProbability * TimeToRevenue * Automation * Recurrence * CapitalEfficiency
        """
        rev_prob = float(candidate_spec.get("revenue_probability", 0.8))
        time_score = max(1.0, 10.0 - (float(candidate_spec.get("time_to_first_revenue_days", 5)) / 2.0))
        automation = float(candidate_spec.get("automation_ratio", 0.9)) * 10.0
        recurrence = float(candidate_spec.get("recurrence_score", 8.0))
        cap_eff = float(candidate_spec.get("capital_efficiency", 10.0))

        priority = rev_prob * time_score * automation * recurrence * cap_eff
        return round(float(priority), 2)

    def rank_candidates(self, candidates_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters out candidates that fail Hard Gates, then ranks remaining candidates by FIRST_REVENUE priority.
        """
        evaluated = [self.evaluate_hypothesis(c) for c in candidates_list]
        passed = [e for e in evaluated if e["all_gates_passed"]]
        for p in passed:
            p["first_revenue_priority"] = self.calculate_first_revenue_priority(p)

        passed_sorted = sorted(passed, key=lambda x: x["first_revenue_priority"], reverse=True)
        return passed_sorted
