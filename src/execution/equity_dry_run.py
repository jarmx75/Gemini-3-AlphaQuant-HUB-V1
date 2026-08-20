"""
Equity Dry-Run Execution Rehearsal Runner
Tests full lifecycle for US Equity ETF TSMOM strategies:
Signal -> Risk -> Order Generation -> Broker Fill -> Position Tracking -> Reconciliation -> Close

STRICT SECURITY INVARIANTS:
1. Uses AlpacaPaperBroker in mock/offline mode (ZERO external network calls).
2. Keeps logs strictly separate in logs/execution/paper_trades_equity.json.
3. APPROVED=false, DEMO_ORDERS=0, REAL_ORDERS=0 preserved.
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

from src.execution.broker_adapters.alpaca_paper import AlpacaPaperBroker, ALPACA_PAPER_BASE_URL
from src.strategies.equity_tsmom_adapter import EquityTSMOMAdapter, DEFAULT_UNIVERSE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "historical_equities"
LOGS_DIR = PROJECT_ROOT / "logs" / "execution"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
EQUITY_PAPER_TRADES_LOG = LOGS_DIR / "paper_trades_equity.json"


def load_recent_equity_data(n_bars: int = 100) -> pd.DataFrame:
    """Loads aligned recent daily close prices for the 8 ETFs."""
    close_dict = {}
    for sym in DEFAULT_UNIVERSE:
        file_path = DATA_DIR / f"{sym}_1d_2022_2026.csv"
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'])
        close_dict[sym] = df.set_index('date')['close']
        
    df_close = pd.DataFrame(close_dict).sort_index().dropna()
    return df_close.iloc[-n_bars:]


def run_equity_dry_run_rehearsal() -> Dict[str, Any]:
    logger.info("=== STARTING EQUITY DRY-RUN REHEARSAL FOR TSMOM M1 & M2 ===")
    
    # 1. Instantiate Alpaca Paper Broker in Mock Mode
    broker = AlpacaPaperBroker(mock_mode=True, initial_cash=100000.0)
    account = broker.get_account()
    logger.info(f"🏦 [BROKER INIT] Cash: ${float(account['cash']):,.2f} | Buying Power: ${float(account['buying_power']):,.2f}")

    # 2. Load Market Data
    df_close = load_recent_equity_data(n_bars=90)
    current_prices = df_close.iloc[-1].to_dict()
    broker.set_mock_prices(current_prices)
    logger.info(f"📊 [MARKET DATA] Latest close prices: {current_prices}")

    # 3. Instantiate Strategy Adapters
    adapter_m1 = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M1_N21", lookback_window=21)
    adapter_m2 = EquityTSMOMAdapter(strategy_id="TSMOM_1D_M2_N63", lookback_window=63)

    results = {}
    paper_trades_record = []

    for adapter in [adapter_m1, adapter_m2]:
        logger.info(f"\n--- Processing Strategy: {adapter.strategy_id} ---")
        
        # A. Signal Generation
        target_weights = adapter.compute_target_weights(df_close)
        logger.info(f"🎯 [TARGET WEIGHTS] {target_weights}")

        # B. Check Current Positions
        positions = broker.get_positions()
        curr_pos_map = {p['symbol']: float(p['qty']) for p in positions}
        total_equity = float(broker.get_account()['portfolio_value'])

        # C. Order Generation
        orders = adapter.generate_rebalance_orders(
            current_positions=curr_pos_map,
            target_weights=target_weights,
            total_equity=total_equity,
            current_prices=current_prices
        )
        logger.info(f"📋 [ORDERS GENERATED] {len(orders)} rebalancing orders proposed.")

        # D. Execution Lifecycle
        filled_orders = []
        for o in orders:
            res = broker.submit_order(
                symbol=o['symbol'],
                qty=o['qty'],
                side=o['side'],
                order_type="market"
            )
            filled_orders.append(res)
            paper_trades_record.append({
                "strategy_id": adapter.strategy_id,
                "symbol": o['symbol'],
                "side": o['side'],
                "qty": o['qty'],
                "price": o['price'],
                "notional": o['delta_notional'],
                "status": "FILLED",
                "timestamp": res.get("filled_at")
            })

        # E. Post-Execution Reconciliation
        updated_positions = broker.get_positions()
        updated_account = broker.get_account()
        logger.info(f"✅ [RECONCILIATION] Open Positions count: {len(updated_positions)}")
        for p in updated_positions:
            logger.info(f"   -> {p['symbol']}: {p['qty']} shares @ ${p['avg_entry_price']} USD (Market Value: ${p['market_value']})")
        logger.info(f"💰 [PORTFOLIO STATE] Cash: ${float(updated_account['cash']):,.2f} | Portfolio Value: ${float(updated_account['portfolio_value']):,.2f}")

        results[adapter.strategy_id] = {
            "target_weights": target_weights,
            "orders_count": len(orders),
            "fills_count": len(filled_orders),
            "positions_count": len(updated_positions),
            "portfolio_value": float(updated_account['portfolio_value'])
        }

    # 4. Save Dry-Run Logs to dedicated file
    with open(EQUITY_PAPER_TRADES_LOG, "w") as f:
        json.dump({
            "market": "US_EQUITY_ETF",
            "broker": "ALPACA_PAPER_MOCK",
            "environment": "DRY_RUN",
            "total_trades": len(paper_trades_record),
            "trades": paper_trades_record
        }, f, indent=2)
    logger.info(f"💾 Saved equity dry-run trades log to {EQUITY_PAPER_TRADES_LOG}")

    logger.info("=== EQUITY DRY-RUN REHEARSAL COMPLETED SUCCESSFULLY ===")
    return results


if __name__ == '__main__':
    run_equity_dry_run_rehearsal()
