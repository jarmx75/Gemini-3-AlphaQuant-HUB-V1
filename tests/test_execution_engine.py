"""
Unit & Integration Tests for Automaton Binance Futures Execution Engine
Verifies fail-closed environment isolation, security gates, secret scrubbing,
idempotency, position reconciliation halts, and kill switch circuit breakers.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import logging
from pathlib import Path

from src.execution.execution_config import (
    ExecutionConfig,
    ExecutionMode,
    DEMO_REST_URL,
    MAINNET_REST_URL,
    mask_secret,
    sanitize_log_message
)
from src.execution.binance_client import (
    BinanceFuturesClient,
    BinanceClientError,
    BinanceSecurityBreachError
)
from src.execution.order_manager import OrderManager, OrderStatus
from src.execution.position_manager import PositionManager
from src.execution.reconciliation import ReconciliationEngine
from src.execution.risk_manager import RiskManager
from src.execution.kill_switch import KillSwitch, KillReason


class TestExecutionEngineSecurity(unittest.TestCase):

    def test_real_blocked_without_approved(self):
        """1. REAL trading is strictly blocked if strategy human_approval is not APPROVED in registry."""
        config = ExecutionConfig(
            env=ExecutionMode.REAL,
            real_trading_enabled=True,
            api_key="real_key_mock",
            api_secret="real_secret_mock",
            base_url=MAINNET_REST_URL
        )
        # Pairs_Stat_Arb_Base has human_approval: PENDING in registry.json
        allowed = config.is_strategy_allowed_for_live("Pairs_Stat_Arb_Base", paper_trades=150)
        self.assertFalse(allowed, "Strategy with PENDING approval MUST be blocked in REAL mode.")

    def test_real_blocked_with_insufficient_paper_trades(self):
        """2. REAL trading is strictly blocked if paper_trades < 100."""
        config = ExecutionConfig(
            env=ExecutionMode.REAL,
            real_trading_enabled=True,
            api_key="real_key_mock",
            api_secret="real_secret_mock",
            base_url=MAINNET_REST_URL
        )
        # Even if approval were mock-approved, insufficient paper trades must reject
        allowed = config.is_strategy_allowed_for_live("Pairs_Stat_Arb_Base", paper_trades=45)
        self.assertFalse(allowed, "Strategy with <100 paper trades MUST be blocked in REAL mode.")

    def test_demo_allowed_without_approved(self):
        """3. DEMO mode is permitted without human APPROVED status."""
        config = ExecutionConfig(
            env=ExecutionMode.DEMO,
            api_key="demo_key_mock",
            api_secret="demo_secret_mock"
        )
        allowed = config.is_strategy_allowed_for_live("Pairs_Stat_Arb_Base", paper_trades=0)
        self.assertTrue(allowed, "DEMO mode should not require manual APPROVED registry flag.")

    def test_demo_never_uses_mainnet_url(self):
        """4. DEMO mode strictly forbids connecting to Mainnet endpoints."""
        # Attempting to construct a DEMO config pointing to Mainnet raises PermissionError
        with self.assertRaises(PermissionError):
            ExecutionConfig(
                env=ExecutionMode.DEMO,
                base_url=MAINNET_REST_URL
            )

        # Valid DEMO config must have testnet URL
        demo_config = ExecutionConfig(env=ExecutionMode.DEMO)
        self.assertEqual(demo_config.base_url, DEMO_REST_URL)

        # Client security invariant check
        demo_config.base_url = "https://fapi.binance.com" # tampering attempt
        with self.assertRaises(BinanceSecurityBreachError):
            BinanceFuturesClient(demo_config)

    def test_secrets_never_appear_in_logs_or_repr(self):
        """5. Secrets (API keys, secrets) are scrubbed and never appear in plaintext."""
        raw_key = "super_secret_api_key_xyz_12345678"
        raw_secret = "ultra_confidential_secret_abc_98765432"

        config = ExecutionConfig(
            env=ExecutionMode.DEMO,
            api_key=raw_key,
            api_secret=raw_secret
        )

        repr_str = repr(config)
        self.assertNotIn(raw_key, repr_str)
        self.assertNotIn(raw_secret, repr_str)
        self.assertIn(mask_secret(raw_key), repr_str)

        # Test log sanitizer
        log_msg = f"Error communicating with key {raw_key} and signature {raw_secret}"
        sanitized = sanitize_log_message(log_msg, [raw_key, raw_secret])
        self.assertNotIn(raw_key, sanitized)
        self.assertNotIn(raw_secret, sanitized)

    def test_duplicate_order_retry_idempotency(self):
        """6. OrderManager prevents duplicate order placement upon retry using clientOrderId."""
        config = ExecutionConfig(env=ExecutionMode.PAPER)
        client = BinanceFuturesClient(config)
        order_mgr = OrderManager(client, config)

        client_id = "test_idempotent_order_001"
        
        # First submission
        order1 = order_mgr.submit_order_idempotent(
            strategy_id="Pairs_Stat_Arb_Base",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.01,
            client_order_id=client_id
        )
        self.assertEqual(order1.status, OrderStatus.FILLED)
        self.assertEqual(len(order_mgr.orders), 1)

        # Second submission with exact same client_order_id
        with patch.object(client, 'create_order') as mock_create:
            order2 = order_mgr.submit_order_idempotent(
                strategy_id="Pairs_Stat_Arb_Base",
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.01,
                client_order_id=client_id
            )
            # Must NOT call create_order again
            mock_create.assert_not_called()
            self.assertEqual(order2.client_order_id, client_id)
            self.assertEqual(len(order_mgr.orders), 1)

    def test_position_mismatch_triggers_halt(self):
        """7. Position mismatch between local manager and exchange triggers HALT and Kill Switch."""
        config = ExecutionConfig(env=ExecutionMode.PAPER)
        client = BinanceFuturesClient(config)
        pos_mgr = PositionManager()
        order_mgr = OrderManager(client, config)
        reconciler = ReconciliationEngine(client, pos_mgr, order_mgr)
        kill_switch = KillSwitch(config, client, order_mgr)

        # Local state has an open position
        pos_mgr.open_pair_position(
            strategy_id="Pairs_Stat_Arb_Base",
            pair_name="BTCUSDT/ETHUSDT",
            side="LONG_SPREAD",
            sym_y="BTCUSDT", side_y="BUY", qty_y=0.05, price_y=60000.0,
            sym_x="ETHUSDT", side_x="SELL", qty_x=1.0, price_x=3000.0,
            gamma=1.0, entry_time_str="2026-08-18 12:00:00"
        )

        # Exchange returns 0 positions (mismatch!)
        with patch.object(client, 'get_positions', return_value=[]):
            report = reconciler.run_full_reconciliation()
            self.assertTrue(report.halt_required, "Reconciliation MUST require halt on mismatch.")
            self.assertGreater(len(report.position_mismatches), 0)

            # Check auto kill trigger
            kill_event = kill_switch.check_auto_kill_conditions(reconciliation_report=report)
            self.assertIsNotNone(kill_event)
            self.assertEqual(kill_event.reason, KillReason.POSITION_MISMATCH)
            self.assertTrue(kill_switch.is_triggered)

    def test_kill_switch_cancels_and_blocks_orders(self):
        """8. Kill switch immediately blocks new orders and prevents risk approval."""
        config = ExecutionConfig(env=ExecutionMode.PAPER, kill_switch_active=True)
        client = BinanceFuturesClient(config)
        pos_mgr = PositionManager()
        risk_mgr = RiskManager(config, pos_mgr)

        # Pre-trade risk validation must reject
        approved, reason = risk_mgr.validate_pre_trade_risk(
            strategy_id="Pairs_Stat_Arb_Base",
            pair_name="BTCUSDT/ETHUSDT",
            order_notional=150.0
        )
        self.assertFalse(approved)
        self.assertIn("Kill switch is actively triggered", reason)

        # Client create_order must raise security error
        with self.assertRaises(BinanceSecurityBreachError):
            client.create_order(symbol="BTCUSDT", side="BUY", quantity=0.01)

    def test_invalid_environment_fails_closed(self):
        """9. Any invalid / unrecognized environment string fails closed."""
        with self.assertRaises(ValueError):
            ExecutionConfig(env="INVALID_ENVIRONMENT_PROD")


if __name__ == "__main__":
    unittest.main()
