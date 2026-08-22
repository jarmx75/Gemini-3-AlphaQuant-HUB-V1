"""
Revenue Memory Module (Phase 2 Economic Redesign - Track B)
Extends Automaton Memory for revenue opportunities across lifecycle states:
OPPORTUNITY_DISCOVERED, OPPORTUNITY_SCREENED, EXPERIMENT_RUNNING, VALIDATED, REVENUE_GENERATING, SCALING, KILLED.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType

logger = logging.getLogger(__name__)


class RevenueMemory:
    """
    Lifecycle tracker for Non-Trading & Trading Revenue Opportunities.
    """

    def __init__(self):
        self.memory = AutomatonMemory()

    def record_opportunity_state(
        self,
        opp_id: str,
        family: str,
        status: str,  # OPPORTUNITY_DISCOVERED, OPPORTUNITY_SCREENED, EXPERIMENT_RUNNING, VALIDATED, REVENUE_GENERATING, SCALING, KILLED
        eos_score: float,
        details: Dict[str, Any]
    ) -> bool:
        claim_text = f"[{status}] {opp_id} ({family}) - EOS: {eos_score} | Details: {json.dumps(details)}"
        try:
            self.memory.write(
                memory_type=MemoryType.CORE,
                family=family,
                batch_id=opp_id,
                claim_text=claim_text,
                source_path="docs/REVENUE_SOURCE_MAP.md",
                source_commit="HEAD",
                tags=[status, family]
            )
            logger.info(f"Recorded revenue opportunity state: {opp_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to record revenue memory for {opp_id}: {e}")
            return False
