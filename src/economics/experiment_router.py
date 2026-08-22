"""
Autonomous Experiment Router (Phase 2 Economic Redesign - Track A & B)
Selects the next experiment with highest Expected Economic Value across Trading, SaaS, API, Data, Service, Automation, Information, Lead-Gen.
"""

import logging
from typing import Dict, Any, List
from src.economics.opportunity_engine import OpportunityEngine

logger = logging.getLogger(__name__)


class AutonomousExperimentRouter:
    """
    Unified Experiment Router for Trading & Non-Trading Opportunities.
    """

    def __init__(self):
        self.engine = OpportunityEngine()

    def select_next_best_experiment(self) -> Dict[str, Any]:
        """
        Processes catalog, filters through gates, scores EOS, and selects #1 highest economic value experiment.
        """
        catalog_summary = self.engine.process_catalog()
        top_selected = catalog_summary["top_3_selected"]

        if not top_selected:
            return {"status": "NO_EXPERIMENTS_AUTHORIZED", "selected_experiment": None}

        best_experiment = top_selected[0]

        logger.info(f"Selected #1 Experiment: {best_experiment['id']} ({best_experiment['family']}) - EOS: {best_experiment['eos_score']}")

        return {
            "status": "EXPERIMENT_SELECTED",
            "selected_experiment": best_experiment,
            "runner_up_experiments": top_selected[1:]
        }
