# MASTER CONTEXT DOCUMENT — TRADING-AUTONOMOUS-SYSTEM

> **NOTICE FOR AI AGENTS & ENGINEERS**: This document provides full, self-contained operational, architectural, commercial, and historical context for the `trading-autonomous-system` repository. An AI model reading this file has complete knowledge of the project without needing access to previous chat logs.

---

# 1. PROJECT IDENTITY

- **Project Name**: `trading-autonomous-system`
- **Original Purpose**: Autonomous quantitative trading system, factor engine, strategy generator, and backtesting platform.
- **Current Purpose**: Fully autonomous customer acquisition, opportunity discovery, lead qualification, value delivery, and revenue generation platform for quantitative strategy auditing and verification services.
- **Current Commercial Objective**: Acquire real paying external customers for quantitative strategy audits, algorithm execution reality verification, and robustness testing.
- **Current Operating Experiment**: Continuous local 24-hour customer acquisition experiment (`python3 scripts/local_acquisition_pilot.py --loop`).

---

# 2. BUSINESS MODEL

The commercial engine offers three tiered quantitative audit products via PayPal Hosted Payment Links:

1. **QUANT_AUDIT_49**
   - **Service**: Basic Quantitative Audit & Overfitting Verification.
   - **Price**: $49.00 USD
   - **Canonical Payment Link**: `https://www.paypal.com/ncp/payment/SH9CKB2WSX728`

2. **QUANT_EXECUTION_REALITY_AUDIT_79**
   - **Service**: Execution Reality Audit, Slippage/Spread Friction Analysis & Order-Book Market Impact.
   - **Price**: $79.00 USD
   - **Canonical Payment Link**: `https://www.paypal.com/ncp/payment/TMMGL3YRC8PFN`

3. **COMPLETE_QUANT_VALIDATION_BUNDLE_96**
   - **Service**: Complete Quant Audit + Execution Reality + Monte Carlo Robustness & Certificate.
   - **Price**: $96.00 USD
   - **Canonical Payment Link**: `https://www.paypal.com/ncp/payment/2Y3RX97HNWXY6`

### Internal Test System Payment:
- **SYSTEM_TEST_PAYMENT**: $1.00 MXN (`https://www.paypal.com/ncp/payment/25GRGEEFTJ2QL`)
- **CRITICAL INVARIANT**: $1 MXN test transactions are strictly isolated as system tests and **MUST NEVER** authorize commercial product fulfillment, certificates, or commercial revenue aggregation.

---

# 3. PAYMENT ARCHITECTURE

- **Checkout Mechanism**: PayPal Hosted Payment Links (No-Code Payment buttons) serve as the primary commercial checkout surface.
- **Revoked API Deprecation**: Legacy PayPal Orders API v2 credentials were intentionally revoked in Sprint #34.1 to eliminate secret storage risks. Payment capture relies 100% on asynchronous IPN / Webhooks.
- **PayPal IPN Endpoint**: Production listener live on Vercel backend at `https://automaton-quant-audit-api.vercel.app/api/ipn`.
- **PayPal Webhook Endpoint**: Production listener live at `https://automaton-quant-audit-api.vercel.app/api/webhook`.
- **Proof of Payment Rule**: Browser redirection to `success.html` is **NOT** accepted as proof of payment. Commercial fulfillment occurs **ONLY** upon receipt of a verified HTTP POSTBACK IPN from PayPal.
- **Idempotency & Primary Key**: PayPal `txn_id` serves as the primary payment identity. Repeated `txn_id` events yield `DUPLICATE_IGNORED` with zero duplicate fulfillment.
- **Test Payment Isolation**: `SYSTEM_TEST_PAYMENT` events verify IPN postback handshake and endpoint availability but produce zero commercial revenue or audit certificates.
- **$1 MXN Reference Reconciliation**: Observed transaction ID `8WB32625PL331771` (merchant email notification reference `8WB32625PL3317718`). The system reconciles 17-digit merchant references by stripping trailing character padding to match standard 17-character PayPal transaction IDs without treating IDs as secrets.

---

# 4. PAYPAL REAL TEST RESULT

- **Live Test Event**: A real $1.00 MXN payment was completed from the owner's personal PayPal account to the business merchant account.
- **Handshake Verification**: PayPal sent an authentic IPN event to `https://automaton-quant-audit-api.vercel.app/api/ipn`. Postback handshake received `VERIFIED` status from PayPal.
- **Merchant Notification**: Email confirmation received by merchant account.
- **Funnel Classification**: Correctly classified as `SYSTEM_TEST_PAYMENT` and isolated from commercial metrics.
- **Current Financial Status**:
  - `REAL_REVENUE_USD = 0.0`
  - `FIRST_REVENUE_ACHIEVED = FALSE`
  - **Reason**: No external commercial customer has yet purchased a $49 / $79 / $96 product link.

---

# 5. VERCEL ARCHITECTURE

- **Production API Alias**: `https://automaton-quant-audit-api.vercel.app`
- **Vercel Project Name**: `automaton-quant-audit-api`
- **Vercel Team**: `alpha-quant1`
- **Frontend / Backend Split**:
  - **Frontend Landing Page**: Hosted on GitHub Pages at `https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/`
  - **Backend Serverless API**: Hosted on Vercel at `automaton-quant-audit-api.vercel.app`
- **Public API Routes**:
  1. `/api/ipn` — PayPal Instant Payment Notification handler & postback verifier.
  2. `/api/webhook` — PayPal Webhook receiver.
  3. `/api/analytics` — Funnel telemetry and event collector.
  4. `/api/revenue-scheduler` — Acquisition scheduler trigger.
  5. `/api/upload-audit` — Customer strategy upload & automated audit trigger.
  6. `/api/capture-order` — Order verification.
- **Root Route Behavior**: Navigating to `https://automaton-quant-audit-api.vercel.app/` returns HTTP 404 by design because Vercel hosts API endpoints exclusively. The 404 at root is **NOT** an API failure.
- **Cron Limitation**: Vercel Hobby accounts enforce a maximum cron frequency of 1 invocation per day (`0 9 * * *`). Therefore, continuous 15-minute acquisition cycles cannot run on Vercel Hobby cron.

---

# 6. LOCAL AUTONOMOUS ACQUISITION RUNTIME

- **Primary Driver**: `scripts/local_acquisition_pilot.py`
- **Execution Modes**:
  - `python3 scripts/local_acquisition_pilot.py --once` — Runs a single 15-minute cycle and exits with JSON report.
  - `python3 scripts/local_acquisition_pilot.py --loop` — Runs continuous 15-minute acquisition cycles 24/7.
- **Experiment Scope**: 24-hour continuous customer acquisition pilot running locally on Mac worker node.
- **Prerequisites**: Mac system sleep must be disabled during the 24-hour experiment window.

---

# 7. ACQUISITION ENGINE

- **Core Module**: `src/economics/autonomous_opportunity_discovery_engine.py` (`AutonomousOpportunityDiscoveryEngine`)
- **Discovery Adapters (9 Channels)**:
  1. `GITHUB` — Public issues, discussions, & quantitative repositories.
  2. `REDDIT` — Algorithmic trading & quantitative finance subreddits.
  3. `QUANTCONNECT` — QuantConnect community discussions & algorithm forums.
  4. `SEO` — Organic search strategy & landing content optimization.
  5. `TECHNICAL_COMMUNITIES` — Specialized quant & developer communities.
  6. `DEVELOPER_FORUMS` — Trading bot and Python developer forums.
  7. `B2B_DIRECTORIES` — Fintech & trading vendor listings.
  8. `MARKETPLACES` — Strategy and bot marketplaces.
  9. `CONTENT_DISCOVERY` — Technical articles, blogs, & whitepaper distribution.
- **Capability Model**: Each channel adapter explicitly declares its capability mode. Automated submission (`automated_submission_supported = True`) is currently enabled for `GITHUB`. Other channels operate in qualification/discovery mode.

---

# 8. OUTREACH SAFETY & QUALITY GATES

- **Outreach Engine**: `src/economics/outreach_execution_engine.py` (`RealOutreachExecutionEngine`)
- **3-Tier Action Classification**:
  - `TIER_A_AUTO_PUBLISH` — ContextScore >= 70, IntentScore >= 60, PromoRisk <= 25, DupRisk == 0, `automated_submission_supported == True`.
  - `TIER_B_VALUE_CONTRIBUTION` — ContextScore >= 55, IntentScore >= 45, PromoRisk <= 35. Local educational response.
  - `TIER_C_BLOCK` — High promotion risk, low intent, or low context score. Blocked from publication.
- **Safety Protections**:
  - Anti-repeat guard (Thread ID, Repo, Author, Channel cooldowns).
  - Exposure budgets (Max per-cycle and per-target publication limits).
  - Strict distinction: Locally generated draft content is recorded as `ACTION_GENERATED_LOCALLY`. Only verified HTTP API submissions are recorded as `ACTION_SENT_EXTERNALLY`. Remote existence checks confirm `PUBLICATION_CONFIRMED`.

---

# 9. TELEMETRY ARCHITECTURE

Telemetry is mathematically isolated across 4 distinct accounting layers:
1. **SYSTEM HISTORICAL TOTALS** — Cumulative historical test runs & internal development benchmarks.
2. **SESSION TOTALS** — Aggregated metrics since `session_start_utc` (`2026-08-26T00:09:57Z`).
3. **CURRENT CYCLE** — Single 15-minute cycle metrics.
4. **DELTA FROM PREVIOUS CYCLE** — Net change since previous cycle.

### Telemetry Invariants:
- `UNKNOWN != 0` — Unverified data must be labeled UNKNOWN, not zero.
- `TEST != REAL` — Test events never mix with real customer funnels.
- `PAYMENT_RETURN != PAYMENT_COMPLETED` — Browser return is not payment proof.
- `AUDIT_COMPLETED != PAID` — Internal test audits do not imply revenue.
- `CERTIFICATE != CUSTOMER` — Test certificates do not represent real customers.

---

# 10. CURRENT TELEMETRY (LATEST OBSERVED STATE)

- **Session ID**: `sess_20260826_000957_11e9b0`
- **Session Start (UTC)**: `2026-08-26T00:09:57.414562+00:00`
- **Session Elapsed Hours**: `72.96 hours`
- **Total Cycles Executed**: `237` (237 Successful, 0 Failed, 0 Idle)
- **Opportunities Evaluated (Session)**: `10,710`
- **Targets Selected (Session)**: `1,222`
- **Tier Classification (Session)**:
  - `Tier A Targets`: `32`
  - `Tier B Targets`: `0`
  - `Tier C Targets`: `1,190`
- **Actions Accounted (Session)**:
  - `Actions Attempted`: `1,222`
  - `Actions Generated Locally`: `1,190`
  - `Actions Sent Externally`: `32`
  - `Publications Confirmed`: `32`
- **Real Customer Funnel**:
  - `Human Replies`: `0`
  - `Landing Visits`: `0`
  - `Quiz Starts`: `0`
  - `Checkouts Started`: `0`
  - `Real Payments Completed`: `0`
  - `Real Revenue USD`: `$0.00`
  - `Real Customer Audits`: `0`
  - `Real Customer Certificates`: `0`
- **Historical Test Artifacts (Isolated)**:
  - `Historical Test Audits`: `153`
  - `Historical Test Certificates`: `153`
  - `Historical Test Payments`: `1` ($1 MXN System Test)

---

# 11. CURRENT CRITICAL STATUS

- **Architecture Status**: **COMPLETE & FROZEN** for 24-hour experiment.
- **External Action Proof Status**: **PASS** — Real GitHub comment posted & verified remotely.
  - **Repository**: [`jarmx75/Gemini-3-AlphaQuant-HUB-V1`](https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1)
  - **Issue**: `#1`
  - **Comment ID**: `5459378287`
  - **Live URL**: [`https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1#issuecomment-5459378287`](https://github.com/jarmx75/Gemini-3-AlphaQuant-HUB-V1/issues/1#issuecomment-5459378287)
  - **Remote Verification**: `REMOTE_VERIFICATION_STATUS = SUCCESS` (`REMOTE_COMMENT_EXISTS = True`)
- **Final Verdict**: `STATUSES.FINAL_VERDICT = READY_FOR_24H_LOOP`

---

# 12. TEST SUITE

- **Total Unit Tests**: `210`
- **Passed**: `210`
- **Failed**: `0`
- **Pass Rate**: `100% PASS` (`Ran 210 tests in 62.139s OK`)

---

# 13. COMPACT SPRINT HISTORY (SPRINTS 19 THROUGH 36.4.2)

1. **Sprint #19**: Institutional Risk Framework. Added VaR, Expected Shortfall, & stress testing. (Result: Pass)
2. **Sprint #20**: Multi-Asset Portfolio Allocation. Added Black-Litterman & Risk Parity engines. (Result: Pass)
3. **Sprint #21**: Market Microstructure & Order Book Friction. Added slippage & depth modeling. (Result: Pass)
4. **Sprint #22**: Factor Library Expansion. Integrated 50+ quantitative factors. (Result: Pass)
5. **Sprint #23**: Machine Learning Alpha Generator. Added XGBoost & LightGBM signal generators. (Result: Pass)
6. **Sprint #24**: Initial Content Distribution Pilot. Published quant discussions on GitHub. (Caveat: Uncontrolled volume)
7. **Sprint #24.1**: Content Audit & Quality Filter. Cleaned low-quality comments & added relevance gates. (Result: Pass)
8. **Sprint #25**: Automated Backtesting Engine. Implemented stationary block bootstrap Monte Carlo. (Result: Pass)
9. **Sprint #26**: Strategy Robustness Matrix. Added walk-forward optimization & parameter sensitivity. (Result: Pass)
10. **Sprint #27**: Production Risk Circuit Breakers. Added max drawdown auto-deleveraging. (Result: Pass)
11. **Sprint #28**: Regulatory & Compliance Reporting. Generated automated PDF audit certificates. (Result: Pass)
12. **Sprint #29**: Production Autonomous Runtime Verification. Verified 24/7 engine state on Vercel. (Result: Pass)
13. **Sprint #30**: Customer Portal & Strategy Upload. Created `/api/upload-audit` serverless endpoint. (Result: Pass)
14. **Sprint #31**: Commercial Product Definition. Defined $49 / $79 / $96 service tiers. (Result: Pass)
15. **Sprint #31.1**: PayPal API Integration. Added Orders API v2 capture workflows. (Result: Pass)
16. **Sprint #31.2**: Email Delivery Pipeline. Integrated Resend API for instant certificate delivery. (Result: Pass)
17. **Sprint #32**: Public Landing Page Launch. Deployed landing site on GitHub Pages. (Result: Pass)
18. **Sprint #32.1**: Analytics & Funnel Tracking. Deployed `/api/analytics` endpoint on Vercel. (Result: Pass)
19. **Sprint #32.2**: Lead Capture Quiz. Added interactive quantitative readiness quiz. (Result: Pass)
20. **Sprint #32.3**: Checkout Conversion Optimization. Added dynamic pricing pills & social proof. (Result: Pass)
21. **Sprint #32.4**: Automated Follow-up Email Sequences. Added lead nurturing workflows. (Result: Pass)
22. **Sprint #33**: Full System Integration Audit. Verified end-to-end user journey. (Result: Pass)
23. **Sprint #34**: PayPal IPN & Webhook Architecture. Replaced Orders API with IPN listeners. (Result: Pass)
24. **Sprint #34.1**: Credentials Security Clean-Up. Revoked Orders API secrets & migrated to Hosted Links. (Result: Pass)
25. **Sprint #34.2**: IPN Handshake & Idempotency Verifier. Added postback verification & `txn_id` deduplication. (Result: Pass)
26. **Sprint #34.3**: Real $1 MXN IPN Verification. Executed live $1 MXN test payment & verified IPN. (Result: Pass)
27. **Sprint #34.4**: Product-Price Mapping Verification. Verified $49, $79, $96 link mappings. (Result: Pass)
28. **Sprint #34.5**: Fulfillment Pipeline Stress Test. Verified strategy upload -> audit -> cert -> email. (Result: Pass)
29. **Sprint #34.6A**: Vercel Serverless Bundle Optimization. Streamlined package size for serverless limits. (Result: Pass)
30. **Sprint #34.6B**: Vercel Entrypoint & Routing Alignment. Fixed `vercel.json` python route definitions. (Result: Pass)
31. **Sprint #34.6C**: Production Vercel Deployment & Alias Verification. Verified alias `automaton-quant-audit-api.vercel.app`. (Result: Pass)
32. **Sprint #34.7**: 6-Endpoint Live API Health Audit. Verified 200 OK across all 6 API endpoints. (Result: Pass)
33. **Sprint #34.7.1**: Production IPN Route Live Audit. Verified `/api/ipn` postback readiness. (Result: Pass)
34. **Sprint #34.8**: Zero Commercial Revenue Isolation Audit. Verified $1 MXN test never creates revenue. (Result: Pass)
35. **Sprint #34.9**: Requirements & Dependency Cleanup. Removed unnecessary python packages. (Result: Pass)
36. **Sprint #34.10**: Live PayPal IPN & Fulfillment Verification. Verified full postback flow. (Result: Pass)
37. **Sprint #35**: Platform Decision & Cron Evaluation. Selected local Mac worker for 24h pilot. (Result: Pass)
38. **Sprint #36**: Local Autonomous Acquisition Engine. Implemented 15-minute pilot cycle engine. (Result: Pass)
39. **Sprint #36.1**: Telemetry Separation & Session Isolation. Isolated historical artifacts from real funnel. (Result: Pass)
40. **Sprint #36.2**: Rotation & Anti-Idle Engine. Added anti-repeat guard and fallback actions. (Result: Pass)
41. **Sprint #36.3**: Multichannel Acquisition Rotation. Added 9-channel discovery adapters & diversity scoring. (Result: Pass)
42. **Sprint #36.4**: Adaptive Outreach & Exposure Budgets. Implemented 3-tier classification & exposure limits. (Result: Pass)
43. **Sprint #36.4.1**: Telemetry Integrity & Invariants. Enforced mathematical action state machine. (Result: Pass)
44. **Sprint #36.4.2**: Channel Capability Model & External Proof. Added capability declarations, posted live GitHub comment `#5459378287`, verified remotely, and passed 210/210 tests. (Result: Pass)

---

# 14. CURRENT ARCHITECTURAL DECISION

- **Temporary Acquisition Worker**: Local Mac process running `scripts/local_acquisition_pilot.py --loop`.
- **Production API Backend**: Vercel Serverless (`automaton-quant-audit-api.vercel.app`).
- **Production Frontend**: GitHub Pages (`jarmx75.github.io`).
- **Evaluated Worker Alternatives**:
  - *Vercel Hobby Cron*: Rejected for 24/7 continuous acquisition due to 1 run/day limit.
  - *GitHub Actions*: Evaluated for scheduled jobs; deferred pending 24h local pilot evaluation.
  - *Vercel Pro / VPS*: Deferred to post-revenue phase.
- **Current Decision**: Run 24-hour acquisition experiment on local Mac worker.

---

# 15. HOW TO CONTINUE THE PROJECT

To execute or resume the project:

1. **Verify Architecture Freeze**: Ensure no business logic or payment changes are made.
2. **Launch Continuous 24-Hour Experiment**:
   ```bash
   python3 scripts/local_acquisition_pilot.py --loop
   ```
3. **Monitor Progress (Read-Only)**:
   In a separate terminal window, run the read-only monitor anytime:
   ```bash
   python3 src/economics/manual_revenue_funnel_monitor.py
   ```
4. **Post-Experiment Review**: After 24 hours, evaluate real customer conversion, landing traffic, and PayPal IPN events.

---

# 16. MANUAL MONITORING

- **Script**: `src/economics/manual_revenue_funnel_monitor.py`
- **Operating Guarantees**:
  - `READ_ONLY = True`
  - `CRON_UNTOUCHED = True`
  - `SIDE_EFFECTS = 0`
- Running the monitor reads existing JSON files and outputs a clean funnel summary **WITHOUT** mutating state or resetting `session_start_utc`.

---

# 17. SECURITY & SECRETS HANDLING

- `.env` files are **EXCLUDED** from project backups.
- No API keys, passwords, OAuth tokens, SSH keys, or PayPal credentials are baked into backup archives.
- Remote git URLs in backup state documents have credentials sanitized (`https://github.com/...`).
- `.env.example` provides template variable names with all values replaced by `REDACTED`.

---

# 18. RESTORATION INSTRUCTIONS

To restore and run this codebase on a new computer:

1. **Unzip Archive**:
   ```bash
   unzip trading-autonomous-system_FULL.zip -d trading-autonomous-system
   cd trading-autonomous-system
   ```
2. **Create Python Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Secrets**:
   ```bash
   cp .env.example .env
   # Edit .env and supply actual GITHUB_TOKEN, RESEND_API_KEY, etc.
   ```
5. **Inspect Git & Runtime State**:
   ```bash
   cat GIT_STATE.txt
   ```
6. **Execute Test Suite**:
   ```bash
   export PYTHONPATH=".:$PYTHONPATH"
   python3 -m unittest discover tests -v
   ```
7. **Run Single Verification Cycle**:
   ```bash
   python3 scripts/local_acquisition_pilot.py --once
   ```
8. **Start Continuous Acquisition Loop**:
   ```bash
   python3 scripts/local_acquisition_pilot.py --loop
   ```

---

---

# 19. GOOGLE DRIVE DURABLE STORAGE INTEGRATION (SESSION 2026-08-31)

- **Purpose of `/api/storage-health`**: Provides a lightweight, read-only serverless endpoint (`GET /api/storage-health`) to verify durable storage provider health, OAuth 2.0 credential validity, and app-managed private folder metadata access without executing live writes, file listings, or exposing sensitive credentials.
- **Root Cause Bug Identified**: Previous environment synchronization injected the literal masked string `"[SENSITIVE]"` (length=11, SHA-256 `3930fb7a9a99`) into Vercel Production environment variables (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`) instead of raw secret values, causing Google API to reject token refresh with `invalid_client: the oauth client was not found`.
- **Applied Fix & Safety Protocol**:
  1. Executed local OAuth 2.0 Desktop authorization flow with owner consent (`jarmx72@gmail.com`) using minimal scope `https://www.googleapis.com/auth/drive.file`.
  2. Evaluated SHA-256 pre-write safety checks in Python memory:
     - `GOOGLE_OAUTH_CLIENT_ID`: length=72, SHA-256 `8beae8c45a86`
     - `GOOGLE_OAUTH_CLIENT_SECRET`: length=35, SHA-256 `4d62a12bcbfd`
     - `GOOGLE_OAUTH_REFRESH_TOKEN`: length=103, SHA-256 `68bf48928522`, starts with `1//`
  3. Uploaded raw unmasked credentials directly from memory into Vercel Production environment variables.
  4. Executed post-pull SHA-256 hash verification to confirm non-placeholder unmasked storage.
  5. Triggered single Vercel Production redeploy (`npx vercel --prod --force`).
  6. Verified `GET /api/storage-health` response: `HTTP 200`, `health = HEALTHY`, `provider = GOOGLE_DRIVE_OAUTH`.
- **Canonical OAuth Client Name**: `"Automaton Quant Audit Drive Desktop"` (`client_id` suffix `...lbkm36l1out4qchcvatvajnlngl8t43v.apps.googleusercontent.com`).
- **App-Managed Private Storage Folder**: `"Automaton Quant Audit - App Private Storage"`.
- **Current Storage Status**:
  - `HTTP Status`: `200 OK`
  - `Provider`: `GOOGLE_DRIVE_OAUTH`
  - `Configured`: `true`
  - `Health`: `HEALTHY`
  - `Commercial Fulfillment Readiness`: `PARTIAL` (Strict fail-closed isolation until end-to-end customer write validation).

---

# 20. SOURCE OF TRUTH FILES

1. `src/economics/autonomous_opportunity_discovery_engine.py` — Discovery adapters & rotation.
2. `src/economics/outreach_execution_engine.py` — Quality gates, 3-tier outreach, & GitHub API poster.
3. `src/economics/autonomous_revenue_orchestrator.py` — Revenue pipeline orchestrator.
4. `src/economics/autonomous_customer_acquisition_loop.py` — Cycle runner logic.
5. `src/economics/autonomous_revenue_portfolio.py` — Commercial product & pricing rules.
6. `scripts/local_acquisition_pilot.py` — Primary CLI runner (`--once` / `--loop`).
7. `src/economics/acquisition_forensic_audit.py` — Telemetry & funnel forensic auditor.
8. `src/economics/manual_revenue_funnel_monitor.py` — Read-only manual funnel monitor.
9. `src/economics/revenue_observation_session.py` — Persistent session timer module.
10. `src/economics/google_drive_oauth_storage.py` — Google Drive OAuth 2.0 storage engine (`GOOGLE_DRIVE_OAUTH`).
11. `scripts/google_drive_oauth_authorize.py` — Local OAuth 2.0 authorizer tool (`drive.file` scope).
12. `api/storage-health.py` — Vercel serverless storage health check endpoint (`/api/storage-health`).
13. `api/internal-storage-validation.py` — Vercel serverless internal storage write validation endpoint (`/api/internal-storage-validation`).
14. `api/ipn.py` — Vercel PayPal IPN serverless endpoint.
15. `api/webhook.py` — Vercel PayPal Webhook serverless endpoint.
16. `api/analytics.py` — Vercel analytics collector endpoint.
17. `api/revenue-scheduler.py` — Vercel scheduler endpoint.
18. `api/upload-audit.py` — Vercel customer strategy upload endpoint.
19. `api/capture-order.py` — Vercel order capture endpoint.
20. `docs/public_landing/index.html` — Commercial landing page HTML.
21. `docs/public_landing/success.html` — Payment success redirection page.
22. `vercel.json` — Serverless routing configuration.
23. `requirements.txt` — Minimal Python dependencies.
24. `.env.example` — Environment template with redacted keys.

---

# 21. BACKUP MANIFEST REFERENCE

See `BACKUP_MANIFEST.md` in the backup root for timestamp, file inventory, archive SHA-256 hash, and validation metrics.

