# AUTOMATON: Binance Futures Demo & Real Execution Architecture

This document describes the execution engine architecture, security invariants, risk boundaries, checklist requirements, and roadmaps for activating Binance Futures Demo (Testnet) and Real (Mainnet) trading.

---

## 1. Execution Engine Architecture

Automaton uses a centralized, provider-agnostic, fail-closed architecture to prevent environment pollution and duplicate order execution.

```
                  ┌──────────────────────────────────────────────┐
                  │              EXECUTION CONFIG                │
                  │   Enforces PAPER / DEMO / REAL Isolation    │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │            BINANCE FUTURES CLIENT            │
                  │   Unified REST/WS Client (Masked Secrets)    │
                  │   DEMO -> testnet.binancefuture.com Only     │
                  └──────────────┬───────────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
┌──────────────┐        ┌──────────────────┐        ┌─────────────────┐
│ORDER MANAGER │        │ POSITION MANAGER │        │  RISK MANAGER   │
│ - Idempotency│        │ - Multi-strategy │        │ - $300/strategy │
│ - Safe Retry │        │   exposure       │        │ - $1000 total   │
│ - No Dupes   │        │ - Pair tracking  │        │ - $50 Daily Max │
└──────┬───────┘        └────────┬─────────┘        └────────┬────────┘
       │                         │                           │
       └─────────────────────────┼───────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────────────────────┐
                  │            RECONCILIATION ENGINE             │
                  │   Continuous Check: Local vs Exchange State  │
                  │   Mismatch -> Triggers HALT NEW ORDERS       │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │                 KILL SWITCH                  │
                  │   Circuit breaker: Cancels open orders       │
                  │   Auto-kill on mismatch, stale data, losses  │
                  └──────────────────────────────────────────────┘
```

### Core Components (`src/execution/`)

1. **`execution_config.py`**:
   - Centralizes environment definitions: `PAPER`, `DEMO`, `REAL`.
   - Strictly fails closed: DEMO mode rejects Mainnet URLs with `PermissionError`.
   - Masks secrets and scrubs API keys from logging strings.

2. **`binance_client.py`**:
   - Centralized wrapper over Binance Futures REST API endpoints.
   - Enforces rate limits, timeout backoffs, and error code categorization.
   - Prevents duplicate network requests.

3. **`order_manager.py`**:
   - Generates deterministic `clientOrderId` (e.g. `a_stat_btc_b_123456_a1b2c3d4`).
   - Idempotency guard: If an order ID is already active or in-flight, it queries order status instead of sending a duplicate order.

4. **`position_manager.py`**:
   - Tracks paired statistical arbitrage legs (Symbol Y and Symbol X) with gamma ratios.
   - Computes aggregate gross and net exposure across all active strategies.

5. **`reconciliation.py`**:
   - Runs full bidirectional reconciliation between local state and Binance positions/orders/balances.
   - Emits `halt_required = True` immediately upon any discrepancy $> 0.0001$.

6. **`risk_manager.py`**:
   - Pre-trade validation gate enforcing:
     - Max position per strategy: **$300.00 USD**
     - Max total exposure: **$1,000.00 USD**
     - Max daily loss: **$50.00 USD**
     - Max strategy drawdown: **10.0%**
     - Max concurrent positions: **3 pairs**
     - Max leverage: **10x**
     - Stale data timeout: **30 seconds**

7. **`kill_switch.py`**:
   - Circuit breaker triggered automatically on:
     - Position mismatch
     - Unexpected fills
     - Stale data (> 30s)
     - Repeated API failures ($\ge 3$)
     - Daily loss breach ($> \$50$)
     - Strategy DD breach ($> 10\%$)
     - Local/server clock drift ($> 1500\text{ ms}$)

8. **`binance_demo_runner.py`**:
   - Orchestrates live monitoring on Testnet feeds, enforcing Paper Gate checks before any order generation.

---

## 2. Environment Variables & Credentials

| Variable | Purpose | Allowed Environments | Required For |
| :--- | :--- | :--- | :--- |
| `BINANCE_ENV` | Target environment (`PAPER`, `DEMO`, `REAL`) | All | All |
| `BINANCE_TEST_KEY` | Testnet API Key | `DEMO`, `PAPER` | Binance Testnet |
| `BINANCE_TEST_SECRET` | Testnet API Secret | `DEMO`, `PAPER` | Binance Testnet |
| `BINANCE_REAL_KEY` | Production API Key *(Not deployed)* | `REAL` | Mainnet (Disabled) |
| `BINANCE_REAL_SECRET` | Production API Secret *(Not deployed)* | `REAL` | Mainnet (Disabled) |
| `REAL_TRADING_ENABLED` | Hard toggle for real trading (`true`/`false`) | `REAL` | Must be `false` |
| `KILL_SWITCH` | Emergency circuit breaker toggle | All | Fails closed if `true` |

### Security Invariants
- **No Hardcoded Keys**: All keys loaded strictly via `os.getenv`.
- **Zero Withdrawal Permissions**: API keys must have **Futures Trading ONLY** permissions enabled. Withdrawal permissions are strictly prohibited.
- **Separate Credentials**: DEMO and REAL must use completely distinct API key pairs.

---

## 3. Operational Risks & Mitigations

| Risk | Severity | Mitigation in Architecture |
| :--- | :--- | :--- |
| **Network Timeout During Order Placement** | HIGH | `OrderManager` checks exchange order status by `clientOrderId` before retrying; never duplicates orders. |
| **Exchange vs Local Position Desync** | HIGH | `ReconciliationEngine` audits net symbol quantities every cycle; mismatches trip the `KillSwitch` and halt orders. |
| **Stale WebSocket / REST Market Data** | MEDIUM | `RiskManager` checks quote timestamps; rejects pre-trade orders if data latency $> 30\text{s}$. |
| **Flash Crash / Daily Loss Runaway** | HIGH | Hard daily loss ceiling ($\$50\text{ USD}$) automatically halts all new entries. |
| **Accidental Mainnet Connection in Demo** | CRITICAL | `ExecutionConfig` throws `PermissionError` if `fapi.binance.com` is configured when `BINANCE_ENV=DEMO`. |

---

## 4. Activation Checklist

### Checklist to Activate Demo (Testnet)
- [ ] 1. Continuous execution of `PairsTradingPaperRunner` until each strategy records $\ge 100$ paper trades.
- [ ] 2. Run `python -m src.execution.demo_readiness` and verify:
  - `overall_demo_gate_passed: true`
  - `gate_status: ELIGIBLE_FOR_DEMO`
- [ ] 3. Obtain valid Binance Futures Testnet API Key and Secret from `testnet.binancefuture.com`.
- [ ] 4. Set `.env`:
  ```env
  BINANCE_ENV=DEMO
  BINANCE_TEST_KEY=your_testnet_key
  BINANCE_TEST_SECRET=your_testnet_secret
  REAL_TRADING_ENABLED=false
  KILL_SWITCH=false
  ```
- [ ] 5. Run test suite: `python -m unittest discover tests -v` (100% pass required).
- [ ] 6. Start runner: `python -m src.execution.binance_demo_runner`.

### Checklist to Activate Real (Mainnet)
- [ ] 1. Demo execution completed with $\ge 100$ testnet trades with positive expectancy and $< 10\%$ drawdown.
- [ ] 2. Human Operator manually edits `src/factory/registry.json` and changes:
  `"human_approval": "APPROVED"`
- [ ] 3. Strict code freeze and security audit on all trading logic.
- [ ] 4. Set `.env`:
  ```env
  BINANCE_ENV=REAL
  BINANCE_REAL_KEY=your_restricted_real_key
  BINANCE_REAL_SECRET=your_restricted_real_secret
  REAL_TRADING_ENABLED=true
  ```
- [ ] 5. Human approval verification: System will fail closed if `APPROVED` is absent or `REAL_TRADING_ENABLED != true`.
