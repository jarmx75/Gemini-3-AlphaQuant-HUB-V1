# READ-ONLY GITHUB DISCOVERY ADAPTER REPORT

> **Security Guarantee**: The GitHub discovery adapter operates strictly in **READ-ONLY** mode using official HTTP `GET` requests to `https://api.github.com/search/issues`. It performs **ZERO** external mutations (no comments, no issues, no PRs, no reactions, no DMs, no user follows). Automated publication remains strictly disabled (`EXTERNAL_PUBLICATION_ATTEMPTED = FALSE`).

---

## 1. Adapter Capabilities & Scope

### What the Adapter DOES:
- Issues HTTP `GET` queries to the official GitHub Search Issues REST API (`https://api.github.com/search/issues`).
- Searches for open, public issues on third-party repositories discussing real quantitative technical problems.
- Parses repository metadata, issue titles, body excerpts, and timestamps.
- Filters out self-owned targets (`jarmx75`, `alpha-quant1`, `jarmx75/Gemini-3-AlphaQuant-HUB-V1`).
- Evaluates technical context relevance and intent scores dynamically.
- Attaches cryptographic/API verification proof to qualify candidates as `VERIFIED_EXTERNAL_SOURCE`.
- Generates objective local educational drafts stored strictly in `logs/portfolio/drafts.jsonl` with status `PENDING_HUMAN_APPROVAL`.

### What the Adapter DOES NOT DO:
- **NO HTTP POST / PUT / DELETE / PATCH requests**.
- **NO automated comments or issue replies**.
- **NO repository or pull request creation**.
- **NO user reactions, stars, or follows**.
- **NO HTML scraping** (uses official REST API exclusively).
- **NO private data collection** (records public URLs and issue titles only).
- **NO guaranteed sales, leads, or revenue classification** (search results are uncontacted candidates only).

---

## 2. Search Query Rotation Engine

The adapter rotates deterministically across targeted quantitative research queries:
1. `"backtest overfitting"`
2. `"lookahead bias"`
3. `"overfitting trading strategy"`
4. `"Sharpe ratio out of sample"`
5. `"slippage backtest"`
6. `"walk forward optimization"`

Query parameters format:  
`https://api.github.com/search/issues?q=is:issue+is:open+type:issue+"{term}"&sort=created&order=desc&per_page=30`

---

## 3. Conservative Execution Caps & Rate Limit Protection

To protect API quotas and maintain strict operational safety, the adapter enforces conservative per-run limits:
- **Max GitHub API Requests per Run**: 3
- **Max Results per Query**: 30
- **Max Verified Prospects per Run**: 10
- **Max Local Drafts per Run**: 5
- **Network Timeout**: 10 seconds per HTTP GET call
- **Rate Limit Monitoring**: Inspects `X-RateLimit-Remaining`, `X-RateLimit-Limit`, and `X-RateLimit-Reset` headers on every response.
- **Unauthenticated Handling**: If `GITHUB_TOKEN` is unavailable, issues unauthenticated GET requests with custom `User-Agent` (`Trading-Autonomous-System-Audit-Engine/1.0`). If rate-limited (HTTP 403), logs rate-limit state gracefully without uncaught exceptions.

---

## 4. Safety Filters & Self-Identity Exclusion (`SelfIdentityConfig`)

Every candidate issue item returned by GitHub Search API is evaluated against 8 mandatory safety gates:
1. **API Provenance**: Must originate directly from an authenticated or official GET response from `api.github.com`.
2. **Open Public Status**: `state == "open"`.
3. **Valid Domain**: `html_url` belongs to `github.com`.
4. **Self-Target Exclusion**: Repository owner / author does NOT match `jarmx75`, `alpha-quant1`, `jarmx75/Gemini-3-AlphaQuant-HUB-V1`, or configured self-identity domains. Matches receive `status = "BLOCKED_SELF_TARGET"`.
5. **Relevance Filtering**: Candidates from archived, fork, spam, or tutorial repos are filtered out.
6. **Technical Signal Gate**: `context_score >= 50` and `intent_score >= 40`.
7. **Persistent Deduplication**: Target URL / identifier must not exist in `prospects.jsonl` or historical target records. Matches receive `status = "BLOCKED_DUPLICATE"`.
8. **Minimal Public Info**: Records only public URLs, issue numbers, titles, and timestamps.

---

## 5. Verification Proof & `VERIFIED_EXTERNAL_SOURCE` Definition

A prospect is classified as `VERIFIED_EXTERNAL_SOURCE` if and only if it passes all safety gates and includes an authentic verification proof dictionary:

```json
{
  "github_api_endpoint": "https://api.github.com/search/issues",
  "fetched_at_utc": "2026-08-30T20:30:00.000000+00:00",
  "repository_full_name": "Bbambaaamm/Autonomous-Quant-Lab",
  "issue_number": 76,
  "html_url": "https://github.com/Bbambaaamm/Autonomous-Quant-Lab/issues/76",
  "api_url": "https://api.github.com/repos/Bbambaaamm/Autonomous-Quant-Lab/issues/76",
  "issue_created_at": "2026-08-30T15:20:10Z",
  "issue_updated_at": "2026-08-30T15:20:10Z",
  "query_term": "backtest overfitting",
  "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"
}
```

---

## 6. Local Draft Specification & Mandatory Human Approval

For qualified `VERIFIED_EXTERNAL_SOURCE` prospects (up to 5 per run), local educational drafts are generated with issue-tailored observations:

- **Storage File**: `logs/portfolio/drafts.jsonl`
- **Approval Status**: `"PENDING_HUMAN_APPROVAL"`
- **External Publication Status**: `"NOT_ATTEMPTED"`
- **Human Approval Required**: `true`
- **Tone**: Objective, technical, and educational. Zero profit claims, zero performance guarantees, zero automated commercial links.

---

## 7. How to Review Verified Prospects & Local Drafts

1. Inspect discovered prospects in `logs/portfolio/prospects.jsonl` where `"source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"`.
2. Inspect corresponding local drafts in `logs/portfolio/drafts.jsonl` where `"approval_status": "PENDING_HUMAN_APPROVAL"`.
3. Verify that `external_publication_status` remains `"NOT_ATTEMPTED"`.
4. Review proposed technical observations for accuracy and human approval.
