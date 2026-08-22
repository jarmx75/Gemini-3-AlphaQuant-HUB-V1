"""
Factor Library & Automaton Memory Extension (Phase 2 Economic Redesign)
Registers, queries, and classifies all historical research batches into structured factor records.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.memory.memory_router import AutomatonMemory
from src.memory.schemas import MemoryType

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FACTOR_LIBRARY_JSON = PROJECT_ROOT / "docs" / "FACTOR_LIBRARY.json"

HISTORICAL_BATCH_FACTORS = [
    {
        "factor_id": "FACTOR_BATCH_A",
        "family": "TREND_FOLLOWING_4H",
        "factor_type": "MOMENTUM_BREAKOUT",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.66,
        "standalone_dd": 131.1,
        "standalone_expectancy": -2.55,
        "portfolio_correlation": 0.35,
        "marginal_expectancy": -1.2,
        "marginal_dd": 14.5,
        "research_score": 4.2,
        "source_batch": "Batch_A",
        "status": "REJECTED",
        "notes": "Donchian 4H channel breakouts suffer constant whipsaws and trailing stop fee drag in crypto."
    },
    {
        "factor_id": "FACTOR_BATCH_B",
        "family": "CROSS_SECTIONAL_MOMENTUM_4H",
        "factor_type": "CROSS_SECTIONAL_DISPERSION",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.92,
        "standalone_dd": 22.8,
        "standalone_expectancy": -0.17,
        "portfolio_correlation": 0.40,
        "marginal_expectancy": -0.8,
        "marginal_dd": 6.2,
        "research_score": 6.5,
        "source_batch": "Batch_B",
        "status": "REJECTED",
        "notes": "High turnover (1200-4300 trades) causes 16 bps roundtrip fee friction to destroy cross-sectional spread."
    },
    {
        "factor_id": "FACTOR_BATCH_C",
        "family": "VOLATILITY_COMPRESSION_BREAKOUT",
        "factor_type": "VOLATILITY_COMPRESSION",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.71,
        "standalone_dd": 30.8,
        "standalone_expectancy": -1.57,
        "portfolio_correlation": 0.28,
        "marginal_expectancy": -0.5,
        "marginal_dd": 8.0,
        "research_score": 5.8,
        "source_batch": "Batch_C",
        "status": "REJECTED",
        "notes": "Bollinger bandwidth compression filter reduces trade count but false breakouts remain negative expectancy."
    },
    {
        "factor_id": "FACTOR_BATCH_D",
        "family": "EVENT_SHOCK_REVERSAL_1H",
        "factor_type": "EVENT_SHOCK",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.72,
        "standalone_dd": 51.5,
        "standalone_expectancy": -0.76,
        "portfolio_correlation": 0.15,
        "marginal_expectancy": -0.3,
        "marginal_dd": 12.0,
        "research_score": 7.1,
        "source_batch": "Batch_D",
        "status": "REJECTED",
        "notes": "1H price/volume extreme shocks exhibit strong liquidation cascade momentum rather than fast mean-reversion."
    },
    {
        "factor_id": "FACTOR_BATCH_D2",
        "family": "LIQUIDATION_DERIVATIVES_REVERSAL",
        "factor_type": "MICROSTRUCTURE_LIQUIDATION",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.64,
        "standalone_dd": 0.9,
        "standalone_expectancy": -0.77,
        "portfolio_correlation": 0.10,
        "marginal_expectancy": -0.2,
        "marginal_dd": 0.5,
        "research_score": 8.4,
        "source_batch": "Batch_D2",
        "status": "REJECTED",
        "notes": "Open Interest + Taker Imbalance shock filtering yields insufficient trade opportunity frequency (< 100 trades)."
    },
    {
        "factor_id": "FACTOR_BATCH_E",
        "family": "FUNDING_CONTRARIAN",
        "factor_type": "FUNDING_RATE_ANOMALY",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.61,
        "standalone_dd": 8.0,
        "standalone_expectancy": -0.90,
        "portfolio_correlation": 0.12,
        "marginal_expectancy": -0.4,
        "marginal_dd": 2.1,
        "research_score": 6.9,
        "source_batch": "Batch_E",
        "status": "REJECTED",
        "notes": "Extreme funding rate signals regime persistence rather than immediate mean exhaustion."
    },
    {
        "factor_id": "FACTOR_BATCH_F",
        "family": "FUNDING_MOMENTUM_1H",
        "factor_type": "FUNDING_MOMENTUM",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.94,
        "standalone_dd": 18.5,
        "standalone_expectancy": -0.13,
        "portfolio_correlation": 0.22,
        "marginal_expectancy": -0.1,
        "marginal_dd": 4.0,
        "research_score": 7.5,
        "source_batch": "Batch_F",
        "status": "REJECTED",
        "notes": "Funding momentum suffers from late entry drag; by the time 12h-24h trend confirms, movement is mature."
    },
    {
        "factor_id": "FACTOR_BATCH_G",
        "family": "BASIS_SPOT_PERP",
        "factor_type": "BASIS_ARBITRAGE",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.00,
        "standalone_dd": 100.8,
        "standalone_expectancy": -1.46,
        "portfolio_correlation": 0.05,
        "marginal_expectancy": -1.0,
        "marginal_dd": 25.0,
        "research_score": 5.0,
        "source_batch": "Batch_G",
        "status": "REJECTED",
        "notes": "Spot/perp basis arbitraged too quickly in modern crypto (2024+); 16 bps fee friction destroys minute yield."
    },
    {
        "factor_id": "FACTOR_BATCH_H",
        "family": "MEAN_REVERSION_1H_FREQUENCY_EXPANSION",
        "factor_type": "COINTEGRATION_THRESHOLD",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.96,
        "standalone_dd": 26.6,
        "standalone_expectancy": -0.44,
        "portfolio_correlation": 0.85,
        "marginal_expectancy": -0.6,
        "marginal_dd": 19.9,
        "research_score": 3.1,
        "source_batch": "Batch_H",
        "status": "REJECTED",
        "notes": "Relaxing ADF p-threshold > 0.05 admits non-stationary random walks, degrading PF and quadrupling drawdown."
    },
    {
        "factor_id": "FACTOR_BATCH_I",
        "family": "MEAN_REVERSION_1H_UNIVERSE_EXPANSION",
        "factor_type": "PAIR_SELECTION",
        "classification": "FACTOR_WEAK",
        "standalone_pf": 1.22,
        "standalone_dd": 195.3,
        "standalone_expectancy": -97.69,
        "portfolio_correlation": 0.70,
        "marginal_expectancy": -15.0,
        "marginal_dd": 110.0,
        "research_score": 6.2,
        "source_batch": "Batch_I",
        "status": "REJECTED",
        "notes": "Cross-ecosystem L1 altcoin pairs suffer beta scale distortion; base 3-pair universe remains sole valid set."
    },
    {
        "factor_id": "FACTOR_BATCH_J",
        "family": "LOG_DOLLAR_NEUTRAL_STAT_ARB_1H",
        "factor_type": "LOG_NEUTRAL_SIZING",
        "classification": "FACTOR_VALIDATED",
        "standalone_pf": 1.02,
        "standalone_dd": 0.7,
        "standalone_expectancy": 0.02,
        "portfolio_correlation": 0.65,
        "marginal_expectancy": 0.01,
        "marginal_dd": 0.2,
        "research_score": 12.5,
        "source_batch": "Batch_J",
        "status": "VALIDATED_TOOLING",
        "notes": "Log-price formulation successfully eliminates beta scale distortion and keeps DD < 1.0%."
    },
    {
        "factor_id": "FACTOR_BATCH_K",
        "family": "CROSS_EXCHANGE_LEAD_LAG_5M",
        "factor_type": "CROSS_EXCHANGE_LATENCY",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.58,
        "standalone_dd": 15.8,
        "standalone_expectancy": -0.70,
        "portfolio_correlation": 0.02,
        "marginal_expectancy": -0.5,
        "marginal_dd": 3.0,
        "research_score": 8.0,
        "source_batch": "Batch_K",
        "status": "REJECTED",
        "notes": "Cross-exchange 5m lead-lag correlation is near zero; HFT sub-second arbitrage & taker fees prevent discrete bar alpha."
    },
    {
        "factor_id": "FACTOR_BATCH_L",
        "family": "EQUITY_OVERNIGHT_GAP_REVERSAL_1D",
        "factor_type": "OVERNIGHT_GAP",
        "classification": "FACTOR_REJECTED",
        "standalone_pf": 0.93,
        "standalone_dd": 3.9,
        "standalone_expectancy": -0.13,
        "portfolio_correlation": 0.04,
        "marginal_expectancy": -0.2,
        "marginal_dd": 1.5,
        "research_score": 7.8,
        "source_batch": "Batch_L",
        "status": "REJECTED",
        "notes": "ETF overnight gap downs reflect fundamental macro re-pricings and do not mean-revert intraday."
    },
    {
        "factor_id": "FACTOR_BATCH_M",
        "family": "CROSS_ASSET_TSMOM_1D",
        "factor_type": "MACRO_TREND_FOLLOWING",
        "classification": "FACTOR_VALIDATED",
        "standalone_pf": 2.98,
        "standalone_dd": 6.55,
        "standalone_expectancy": 14.53,
        "portfolio_correlation": 0.03,
        "marginal_expectancy": 5.2,
        "marginal_dd": 0.8,
        "research_score": 18.5,
        "source_batch": "Batch_M",
        "status": "PAPER_CANDIDATE",
        "notes": "Multi-asset daily trend following demonstrates strong orthogonal alpha (PF 1.64-2.98, DD 6.5-9.9%). Belongs to ALPHA_SOURCE_02 EQUITY_TREND."
    },
    {
        "factor_id": "FACTOR_BATCH_N",
        "family": "FUTURES_TERM_STRUCTURE_CARRY",
        "factor_type": "FUTURES_TERM_STRUCTURE",
        "classification": "DATASET_UNAVAILABLE",
        "standalone_pf": 0.00,
        "standalone_dd": 0.0,
        "standalone_expectancy": 0.00,
        "portfolio_correlation": 0.00,
        "marginal_expectancy": 0.0,
        "marginal_dd": 0.0,
        "research_score": 0.0,
        "source_batch": "Batch_N",
        "status": "REJECTED",
        "notes": "Simultaneous dual contract expiration dataset not available in free public data feeds. Commercial license required."
    },
    {
        "factor_id": "FACTOR_BATCH_O",
        "family": "SEC_INSIDER_CLUSTER_BUYING",
        "factor_type": "EVENT_INSIDER_ACCUMULATION",
        "classification": "FACTOR_WEAK",
        "standalone_pf": 1.33,
        "standalone_dd": 92.5,
        "standalone_expectancy": 1.51,
        "portfolio_correlation": 0.01,
        "marginal_expectancy": 0.2,
        "marginal_dd": 22.0,
        "research_score": 14.2,
        "source_batch": "Batch_O",
        "status": "REJECTED",
        "notes": "SEC Form 4 cluster buying exhibits positive medium-term event drift (+1.7% at 10d), but un-stopped 20d holdings on small/mid-caps cause severe standalone drawdown."
    }
]


class FactorLibrary:
    """
    Interface for Automaton Factor Library.
    """

    def __init__(self):
        self.memory = AutomatonMemory()
        self._sync_factors_to_memory()

    def _sync_factors_to_memory(self):
        for f in HISTORICAL_BATCH_FACTORS:
            try:
                self.memory.write(
                    memory_type=MemoryType.CORE,
                    family=f["family"],
                    batch_id=f["source_batch"],
                    claim_text=f"[{f['classification']}] {f['factor_id']}: {f['notes']}",
                    source_path="docs/FACTOR_LIBRARY.md",
                    source_commit="HEAD",
                    tags=[f["classification"], f["factor_type"]]
                )
            except Exception:
                pass

    def get_all_factors(self) -> List[Dict[str, Any]]:
        return HISTORICAL_BATCH_FACTORS

    def get_factors_by_classification(self, classification: str) -> List[Dict[str, Any]]:
        return [f for f in HISTORICAL_BATCH_FACTORS if f["classification"] == classification]
