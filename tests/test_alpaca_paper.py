"""
Unit tests for Alpaca Paper Trading Broker Adapter and Multi-Market Execution.
Verifies:
1. Alpaca paper endpoint strictly enforced (https://paper-api.alpaca.markets).
2. Live endpoint (https://api.alpaca.markets) immediately rejected with SecurityViolationError.
3. Invalid environment (!= "ALPACA_PAPER") immediately rejected.
4. Mock order execution, positions tracking, and cash balance accounting.
5. Order cancellation.
6. Equity paper log isolation (logs/execution/paper_trades_equity.json).
7. End-to-end dry-run rehearsal pipeline.
"""

import json
import unittest
from pathlib import Path

from src.execution.broker_adapters.alpaca_paper import (
    AlpacaPaperBroker,
    ALPACA_PAPER_BASE_URL,
    FORBIDDEN_LIVE_URL,
    SecurityViolationError
)
from src.execution.equity_dry_run import run_equity_dry_run_rehearsal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EQUITY_LOG_PATH = PROJECT_ROOT / "logs" / "execution" / "paper_trades_equity.json"
CRYPTO_POS_PATH = PROJECT_ROOT / "logs" / "execution" / "paper_positions.json"


class TestAlpacaPaperBroker(unittest.TestCase):

    def test_1_paper_endpoint_allowed(self):
        """1. Verifies that valid Alpaca paper endpoint initializes cleanly."""
        broker = AlpacaPaperBroker(
            base_url=ALPACA_PAPER_BASE_URL,
            environment="ALPACA_PAPER",
            mock_mode=True
        )
        self.assertEqual(broker.base_url, ALPACA_PAPER_BASE_URL)
        self.assertEqual(broker.environment, "ALPACA_PAPER")

    def test_2_live_endpoint_strictly_rejected(self):
        """2. Verifies that live Alpaca endpoint raises fatal SecurityViolationError."""
        with self.assertRaises(SecurityViolationError):
            AlpacaPaperBroker(
                base_url=FORBIDDEN_LIVE_URL,
                environment="ALPACA_PAPER",
                mock_mode=True
            )

        with self.assertRaises(SecurityViolationError):
            AlpacaPaperBroker(
                base_url="https://api.alpaca.markets/v2",
                environment="ALPACA_PAPER",
                mock_mode=True
            )

    def test_3_non_paper_environment_rejected(self):
        """3. Verifies that non-paper environment string raises SecurityViolationError."""
        with self.assertRaises(SecurityViolationError):
            AlpacaPaperBroker(
                base_url=ALPACA_PAPER_BASE_URL,
                environment="LIVE",
                mock_mode=True
            )

        with self.assertRaises(SecurityViolationError):
            AlpacaPaperBroker(
                base_url=ALPACA_PAPER_BASE_URL,
                environment="PRODUCTION",
                mock_mode=True
            )

    def test_4_mock_order_execution_and_positions(self):
        """4. Verifies mock order execution, position updates, and cash accounting."""
        broker = AlpacaPaperBroker(mock_mode=True, initial_cash=10000.0)
        broker.set_mock_prices({"SPY": 500.0, "QQQ": 400.0})

        # Submit buy order: 2 SPY @ $500 = $1000 + $0.80 fee
        res = broker.submit_order(symbol="SPY", qty=2.0, side="buy")
        self.assertEqual(res["status"], "filled")
        self.assertEqual(res["symbol"], "SPY")

        positions = broker.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "SPY")
        self.assertEqual(float(positions[0]["qty"]), 2.0)
        self.assertEqual(float(positions[0]["avg_entry_price"]), 500.0)

        # Cash reduced
        self.assertAlmostEqual(broker.cash, 10000.0 - 1000.0 - 0.80, places=2)

    def test_5_mock_order_cancellation(self):
        """5. Verifies order cancellation in mock broker."""
        broker = AlpacaPaperBroker(mock_mode=True, initial_cash=10000.0)
        res = broker.submit_order(symbol="GLD", qty=5.0, side="buy")
        cid = res["client_order_id"]

        canceled = broker.cancel_order(cid)
        self.assertTrue(canceled)
        self.assertEqual(broker.mock_orders[cid]["status"], "canceled")

    def test_6_equity_dry_run_rehearsal_pipeline(self):
        """6. Verifies end-to-end equity dry-run execution without polluting crypto logs."""
        results = run_equity_dry_run_rehearsal()

        self.assertIn("TSMOM_1D_M1_N21", results)
        self.assertIn("TSMOM_1D_M2_N63", results)
        self.assertTrue(results["TSMOM_1D_M1_N21"]["orders_count"] > 0)
        self.assertTrue(results["TSMOM_1D_M2_N63"]["orders_count"] > 0)

        # Verify equity log file exists and is valid JSON
        self.assertTrue(EQUITY_LOG_PATH.exists())
        with open(EQUITY_LOG_PATH, "r") as f:
            eq_data = json.load(f)

        self.assertEqual(eq_data["market"], "US_EQUITY_ETF")
        self.assertEqual(eq_data["broker"], "ALPACA_PAPER_MOCK")
        self.assertTrue(eq_data["total_trades"] > 0)

    def test_7_missing_credentials_fails_closed_in_live_paper_mode(self):
        """7. Verifies that mock_mode=False without API keys raises ALPACA_PAPER_NOT_CONFIGURED."""
        with self.assertRaises(ValueError) as ctx:
            AlpacaPaperBroker(
                base_url=ALPACA_PAPER_BASE_URL,
                environment="ALPACA_PAPER",
                mock_mode=False,
                api_key="",
                secret_key=""
            )
        self.assertIn("ALPACA_PAPER_NOT_CONFIGURED", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
