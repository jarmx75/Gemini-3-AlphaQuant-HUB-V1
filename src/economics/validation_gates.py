"""
Validation Gates Module (Phase 2 Economic Redesign - Track B)
Enforces 7 Hard Validation Gates before any economic opportunity is authorized for experiment execution.
"""

from typing import Dict, Any, Tuple, List
from src.memory.preflight import enforce_preflight


class ValidationGates:
    """
    Enforces 7 Hard Validation Gates:
    1. Legal & Regulatory Compliance
    2. Technical Feasibility
    3. Reasonable Capital (No upfront capital required for test)
    4. Data / Information Availability
    5. Testable Without Real Money (Zero real money spent)
    6. Not Duplicate
    7. Not Previously Rejected (Checked via MemoryPreflight)
    """

    def evaluate_opportunity_gates(self, opp: Dict[str, Any]) -> Tuple[bool, List[str]]:
        rejections = []

        # 1. Legal
        if opp.get("regulatory_burden", 10) > 8:
            rejections.append("REJECTED_HIGH_REGULATORY_BURDEN")

        # 2. Technical Feasibility
        if opp.get("technical_feasibility", 0) < 5:
            rejections.append("REJECTED_LOW_TECHNICAL_FEASIBILITY")

        # 3. Reasonable Capital
        if opp.get("capital_required_usd", 1000) > 500:
            rejections.append("REJECTED_EXCESSIVE_CAPITAL_REQUIREMENT")

        # 4. Data Availability
        if not opp.get("data_available", True):
            rejections.append("REJECTED_DATA_UNAVAILABLE")

        # 5. Testable Without Real Money
        if not opp.get("testable_without_real_money", True):
            rejections.append("REJECTED_REQUIRES_REAL_MONEY")

        # 6. Duplicate check
        if opp.get("is_duplicate", False):
            rejections.append("REJECTED_DUPLICATE")

        # 7. MemoryPreflight Check
        family_name = opp.get("family", "UNKNOWN")
        preflight_pass = enforce_preflight(family_name, opp.get("problem", ""))
        if not preflight_pass:
            rejections.append("REJECTED_PREFLIGHT_MEMORY_BLOCKED")

        passed = len(rejections) == 0
        return passed, rejections
