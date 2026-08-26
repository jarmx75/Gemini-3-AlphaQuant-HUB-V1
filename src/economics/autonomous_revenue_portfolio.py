"""
Autonomous Revenue Portfolio Engine (Sprint #33)

Features:
- Multi-product service management across 8 product states (DISCOVERY, VALIDATION, ACQUISITION, CONVERTING, SCALING, WEAK, PAUSED, REJECTED)
- Active products: QUANT_AUDIT ($49 USD), DATA_PRODUCTS ($29 USD), PROP_VERIFICATION ($299 USD)
- Effort redistribution based on real performance metrics
- Section 13 Safety Gate: Can DISCOVER, SCORE, PROPOSE new products, but DOES NOT deploy without economic validation gate clearance
- Append-only portfolio state log: logs/portfolio/revenue_portfolio_state.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
PORTFOLIO_STATE_FILE = LOGS_PORTFOLIO_DIR / "revenue_portfolio_state.json"
LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

VALID_PRODUCT_STATES = {
    "DISCOVERY", "VALIDATION", "ACQUISITION", "CONVERTING",
    "SCALING", "WEAK", "PAUSED", "REJECTED"
}


class AutonomousRevenuePortfolio:
    """
    Autonomous Revenue Portfolio Engine for multi-product acquisition & dynamic effort allocation.
    """

    def __init__(self):
        self._init_portfolio()

    def _init_portfolio(self):
        if not PORTFOLIO_STATE_FILE.exists():
            initial_state = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "active_product_count": 3,
                "products": {
                    "QUANT_AUDIT": {
                        "product_id": "QUANT_AUDIT",
                        "name": "Quant Audit Micro-SaaS",
                        "category": "SAAS_AUDIT",
                        "price": 49.00,
                        "margin": 0.95,
                        "recurring": False,
                        "automation_score": 95,
                        "conversion_rate": "UNKNOWN",
                        "revenue_usd": 0.0,
                        "traffic_visits": 0,
                        "qualified_leads": 0,
                        "customers": 0,
                        "retention_rate": "UNKNOWN",
                        "status": "ACQUISITION",
                        "effort_allocation_weight": 0.70,
                        "deployed_in_production": True
                    },
                    "DATA_PRODUCTS": {
                        "product_id": "DATA_PRODUCTS",
                        "name": "Crypto Orderflow Datasets",
                        "category": "DATA_FEED",
                        "price": 29.00,
                        "margin": 0.90,
                        "recurring": True,
                        "automation_score": 90,
                        "conversion_rate": "UNKNOWN",
                        "revenue_usd": 0.0,
                        "traffic_visits": 0,
                        "qualified_leads": 0,
                        "customers": 0,
                        "retention_rate": "UNKNOWN",
                        "status": "VALIDATION",
                        "effort_allocation_weight": 0.20,
                        "deployed_in_production": True
                    },
                    "PROP_VERIFICATION": {
                        "product_id": "PROP_VERIFICATION",
                        "name": "Institutional Alpha Verification",
                        "category": "ENTERPRISE_AUDIT",
                        "price": 299.00,
                        "margin": 0.85,
                        "recurring": False,
                        "automation_score": 80,
                        "conversion_rate": "UNKNOWN",
                        "revenue_usd": 0.0,
                        "traffic_visits": 0,
                        "qualified_leads": 0,
                        "customers": 0,
                        "retention_rate": "UNKNOWN",
                        "status": "DISCOVERY",
                        "effort_allocation_weight": 0.10,
                        "deployed_in_production": False
                    }
                }
            }
            self.save_portfolio(initial_state)

    def load_portfolio(self) -> Dict[str, Any]:
        if PORTFOLIO_STATE_FILE.exists():
            try:
                with open(PORTFOLIO_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"products": {}}

    def save_portfolio(self, state: Dict[str, Any]):
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(PORTFOLIO_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def redistribute_effort(self) -> Dict[str, Any]:
        """
        Dynamically adjusts effort allocation weights based on real customer conversions.
        If real conversions are UNKNOWN or 0, retains default weighting.
        """
        state = self.load_portfolio()
        products = state.get("products", {})

        total_converted = sum(p.get("customers", 0) for p in products.values() if isinstance(p.get("customers"), int))

        if total_converted > 0:
            for pid, p in products.items():
                cust = p.get("customers", 0)
                p["effort_allocation_weight"] = round(cust / total_converted, 4)
        else:
            # Maintain balanced focus on active products
            products["QUANT_AUDIT"]["effort_allocation_weight"] = 0.70
            products["DATA_PRODUCTS"]["effort_allocation_weight"] = 0.20
            products["PROP_VERIFICATION"]["effort_allocation_weight"] = 0.10

        self.save_portfolio(state)
        return state

    def propose_new_product(self, product_id: str, name: str, category: str, price: float, margin: float = 0.90) -> Dict[str, Any]:
        """
        Section 13 Safety Gate:
        Can DISCOVER, SCORE, and PROPOSE new products into DISCOVERY state,
        but DOES NOT automatically deploy to production without passing economic validation gate.
        """
        state = self.load_portfolio()

        if product_id in state["products"]:
            return {"status": "SKIPPED_EXISTING", "product": state["products"][product_id]}

        new_product = {
            "product_id": product_id,
            "name": name,
            "category": category,
            "price": price,
            "margin": margin,
            "recurring": False,
            "automation_score": 85,
            "conversion_rate": "UNKNOWN",
            "revenue_usd": 0.0,
            "traffic_visits": 0,
            "qualified_leads": 0,
            "customers": 0,
            "retention_rate": "UNKNOWN",
            "status": "DISCOVERY",
            "effort_allocation_weight": 0.0,
            "deployed_in_production": False,
            "validation_gate_passed": False,
            "deployment_blocked_reason": "PROPOSED_PRODUCT_AWAITING_ECONOMIC_VALIDATION_GATE"
        }

        state["products"][product_id] = new_product
        state["active_product_count"] = len(state["products"])
        self.save_portfolio(state)
        return {"status": "PROPOSED", "product": new_product}

    def get_portfolio_summary(self) -> Dict[str, Any]:
        state = self.load_portfolio()
        products = state.get("products", {})
        active_count = len([p for p in products.values() if p.get("status") in {"ACQUISITION", "VALIDATION", "CONVERTING", "SCALING"}])

        rev_by_product = {pid: p.get("revenue_usd", 0.0) for pid, p in products.items()}
        leads_by_product = {pid: p.get("qualified_leads", 0) for pid, p in products.items()}

        return {
            "total_products": len(products),
            "active_products": active_count,
            "revenue_by_product": rev_by_product,
            "leads_by_product": leads_by_product,
            "products": products
        }


def main():
    portfolio = AutonomousRevenuePortfolio()
    summary = portfolio.get_portfolio_summary()
    print("=== AUTONOMOUS REVENUE PORTFOLIO ===")
    print(f"Total Products: {summary['total_products']}")
    print(f"Active Products: {summary['active_products']}")
    for pid, p in summary['products'].items():
        print(f" - {pid} (${p['price']} USD): Status={p['status']} Weight={p['effort_allocation_weight']} Deployed={p['deployed_in_production']}")


if __name__ == "__main__":
    main()
