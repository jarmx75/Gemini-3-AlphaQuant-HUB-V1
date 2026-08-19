"""
Execution Configuration & API Security Module
Defines environments (PAPER, DEMO, REAL), risk limits, endpoints, and credentials validation.
Strictly fails closed.
"""

import os
import re
import json
import logging
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"


class ExecutionMode(str, Enum):
    PAPER = "PAPER"
    DRY_RUN = "DRY_RUN"
    DEMO = "DEMO"
    REAL = "REAL"


# Standard Endpoints
DEMO_REST_URL = "https://testnet.binancefuture.com"
DEMO_WSS_URL = "wss://stream.binancefuture.com"
MAINNET_REST_URL = "https://fapi.binance.com"
MAINNET_WSS_URL = "wss://fstream.binance.com"
LOCAL_DRY_RUN_URL = "LOCAL_DRY_RUN_NO_NETWORK"


def mask_secret(secret: Optional[str]) -> str:
    """Masks API keys and secrets for secure logging."""
    if not secret:
        return "[EMPTY]"
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-4:]}"


def sanitize_log_message(msg: str, secrets: Optional[list] = None) -> str:
    """Removes sensitive keys/secrets from log strings."""
    if not secrets:
        return msg
    sanitized = msg
    for sec in secrets:
        if sec and len(sec) > 4:
            sanitized = sanitized.replace(sec, mask_secret(sec))
    return sanitized


@dataclass
class ExecutionConfig:
    env: ExecutionMode = ExecutionMode.PAPER
    api_key: str = ""
    api_secret: str = ""
    base_url: str = DEMO_REST_URL
    wss_url: str = DEMO_WSS_URL
    real_trading_enabled: bool = False
    kill_switch_active: bool = False
    
    # Centralized Risk Parameters
    max_position_per_strategy: float = 300.0   # Max notional ($150 per leg = $300 per pair)
    max_total_exposure: float = 1000.0         # Max aggregate notional across portfolio
    max_daily_loss: float = 50.0               # Max daily loss in USD ($50)
    max_strategy_drawdown_pct: float = 10.0    # 10% max strategy DD
    max_concurrent_positions: int = 3          # Max concurrent open pair positions
    max_leverage: int = 10                     # 10x max leverage
    stale_data_timeout_sec: float = 30.0       # Max allowable data latency
    min_paper_trades_for_demo: int = 100       # Gate threshold
    
    # Request & Timing Parameters
    request_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff_sec: float = 0.5
    
    def __post_init__(self):
        self.validate_environment()

    def validate_environment(self):
        """Enforces fail-closed isolation between environments."""
        # 1. Reject invalid environments
        if self.env not in (ExecutionMode.PAPER, ExecutionMode.DRY_RUN, ExecutionMode.DEMO, ExecutionMode.REAL):
            raise ValueError(f"CRITICAL SECURITY: Invalid ExecutionMode '{self.env}'. Must fail closed.")

        # 2. DRY_RUN is completely isolated from network
        if self.env == ExecutionMode.DRY_RUN:
            self.base_url = LOCAL_DRY_RUN_URL
            self.wss_url = LOCAL_DRY_RUN_URL

        # 3. DEMO must strictly use Testnet URL
        if self.env == ExecutionMode.DEMO:
            if "fapi.binance.com" in self.base_url or "api.binance.com" in self.base_url:
                raise PermissionError("CRITICAL SECURITY BREACH: Mainnet URL detected in DEMO mode! Blocking execution.")
            self.base_url = DEMO_REST_URL
            self.wss_url = DEMO_WSS_URL

        # 4. REAL is strictly guarded
        if self.env == ExecutionMode.REAL:
            if not self.real_trading_enabled:
                raise PermissionError("REAL TRADING BLOCKED: REAL_TRADING_ENABLED is false. Execution failed closed.")

    def is_strategy_allowed_for_live(self, strategy_id: str, paper_trades: int = 0) -> bool:
        """
        Validates whether a strategy can be traded in REAL mode.
        Requires:
        - registry human_approval == APPROVED
        - paper_trades >= 100
        - strategy status == PAPER_ACTIVE
        - REAL_TRADING_ENABLED == True
        """
        if self.env != ExecutionMode.REAL:
            # Not a real trading context
            return True

        if not self.real_trading_enabled:
            logger.error("🛑 Security Check Failed: REAL_TRADING_ENABLED is False")
            return False

        if paper_trades < self.min_paper_trades_for_demo:
            logger.error(f"🛑 Security Check Failed: Strategy {strategy_id} has {paper_trades} < {self.min_paper_trades_for_demo} paper trades.")
            return False

        if not REGISTRY_PATH.exists():
            logger.error(f"🛑 Security Check Failed: registry.json not found at {REGISTRY_PATH}")
            return False

        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
            
            # Check active strategies
            active_list = registry_data.get("active_paper_strategies", [])
            for strat in active_list:
                if strat.get("id") == strategy_id:
                    status = strat.get("status")
                    approval = strat.get("human_approval", "")
                    if status != "PAPER_ACTIVE":
                        logger.error(f"🛑 Security Check Failed: {strategy_id} status is {status}, not PAPER_ACTIVE.")
                        return False
                    if "APPROVED" not in approval or "PENDING" in approval:
                        logger.error(f"🛑 Security Check Failed: {strategy_id} human_approval is '{approval}' (NOT APPROVED).")
                        return False
                    return True
            
            logger.error(f"🛑 Security Check Failed: Strategy {strategy_id} not found in active_paper_strategies.")
            return False
        except Exception as e:
            logger.error(f"🛑 Security Check Failed: Error reading registry.json: {e}")
            return False

    def __repr__(self) -> str:
        return (
            f"ExecutionConfig(env={self.env.value}, "
            f"base_url='{self.base_url}', "
            f"api_key='{mask_secret(self.api_key)}', "
            f"api_secret='{mask_secret(self.api_secret)}', "
            f"real_trading_enabled={self.real_trading_enabled}, "
            f"kill_switch_active={self.kill_switch_active}, "
            f"max_position_per_strategy=${self.max_position_per_strategy}, "
            f"max_daily_loss=${self.max_daily_loss})"
        )


def load_execution_config_from_env() -> ExecutionConfig:
    """Loads execution config strictly from environment variables."""
    env_str = os.getenv("BINANCE_ENV", "PAPER").upper()
    try:
        mode = ExecutionMode(env_str)
    except ValueError:
        logger.warning(f"Invalid BINANCE_ENV='{env_str}'. Defaulting to PAPER for safety.")
        mode = ExecutionMode.PAPER

    real_enabled = os.getenv("REAL_TRADING_ENABLED", "false").lower() == "true"
    kill_switch = os.getenv("KILL_SWITCH", "false").lower() == "true"

    if mode == ExecutionMode.DRY_RUN:
        api_key = "DRY_RUN_LOCAL_KEY"
        api_secret = "DRY_RUN_LOCAL_SECRET"
        base_url = LOCAL_DRY_RUN_URL
        wss_url = LOCAL_DRY_RUN_URL
    elif mode == ExecutionMode.DEMO:
        api_key = os.getenv("BINANCE_DEMO_KEY") or os.getenv("BINANCE_TEST_KEY") or os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_DEMO_SECRET") or os.getenv("BINANCE_TEST_SECRET") or os.getenv("BINANCE_API_SECRET", "")
        base_url = DEMO_REST_URL
        wss_url = DEMO_WSS_URL
    elif mode == ExecutionMode.REAL:
        api_key = os.getenv("BINANCE_REAL_KEY") or os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_REAL_SECRET") or os.getenv("BINANCE_API_SECRET", "")
        base_url = MAINNET_REST_URL
        wss_url = MAINNET_WSS_URL
    else:  # PAPER
        api_key = os.getenv("BINANCE_TEST_KEY", "")
        api_secret = os.getenv("BINANCE_TEST_SECRET", "")
        base_url = DEMO_REST_URL
        wss_url = DEMO_WSS_URL

    return ExecutionConfig(
        env=mode,
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        wss_url=wss_url,
        real_trading_enabled=real_enabled,
        kill_switch_active=kill_switch,
        max_position_per_strategy=float(os.getenv("MAX_POSITION_PER_STRATEGY", "300.0")),
        max_total_exposure=float(os.getenv("MAX_TOTAL_EXPOSURE", "1000.0")),
        max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "50.0")),
        max_strategy_drawdown_pct=float(os.getenv("MAX_STRATEGY_DRAWDOWN_PCT", "10.0")),
        max_concurrent_positions=int(os.getenv("MAX_CONCURRENT_POSITIONS", "3")),
        max_leverage=int(os.getenv("MAX_LEVERAGE", "10")),
        stale_data_timeout_sec=float(os.getenv("STALE_DATA_TIMEOUT_SEC", "30.0"))
    )
