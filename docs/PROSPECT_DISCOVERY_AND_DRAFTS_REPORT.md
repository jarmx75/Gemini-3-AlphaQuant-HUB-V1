# PROSPECT DISCOVERY & LOCAL DRAFTS OPERATIONAL REPORT

> **Safety Notice**: The acquisition pipeline operates strictly in non-contact safe mode (`DISCOVERY_AND_DRAFT_ONLY`). It discovers prospective leads, filters self-owned targets and duplicates, generates local educational drafts, and sets mandatory human approval status (`PENDING_HUMAN_APPROVAL`). The system executes **ZERO** external HTTP requests or automated publications (`EXTERNAL_PUBLICATION_ATTEMPTED = FALSE`).

---

## 1. Storage Locations for Prospects & Drafts

- **Prospects Storage**: `logs/portfolio/prospects.jsonl`
- **Local Drafts Storage**: `logs/portfolio/drafts.jsonl`
- **Opportunity Pool Storage**: `logs/portfolio/opportunity_pool.jsonl`
- **Event History Storage**: `logs/portfolio/external_acquisition_event_history.jsonl`

All records are saved as append-only JSON Lines (`.jsonl`) files, preserving complete audit traceability without mutating historical logs.

---

## 2. Self-Targeting Exclusion Rules (`SelfIdentityConfig`)

Centralized self-identity rules in `src/economics/self_identity_config.py` automatically detect and exclude candidate opportunities matching self-owned assets:

- **Self-Owned Repositories**:
  - `jarmx75/Gemini-3-AlphaQuant-HUB-V1`
  - `jarmx75/trading-autonomous-system`
  - `alpha-quant1/automaton-quant-audit-api`
- **Self-Owned Authors & Users**:
  - `jarmx75`, `alpha-quant1`, `alpha_quant_hub`
- **Self-Owned Domains**:
  - `jarmx75.github.io`
  - `jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1`
  - `automaton-quant-audit-api.vercel.app`

### Action on Self-Target Match:
- `self_target_flag = True`
- `ownership_classification = "SELF"`
- `status = "BLOCKED_SELF_TARGET"`
- `evidence = "Matches self-owned repository: jarmx75/Gemini-3-AlphaQuant-HUB-V1"`
- **Result**: Draft generation is **blocked**; candidate is **excluded** from eligible prospects.

---

## 3. Persistent Deduplication Rules

The `ProspectPipelineEngine` enforces persistent deduplication across 3 index keys:
1. **Normalized Source URL**: `normalize_url(source_url)`
2. **Normalized Target Identifier**: `normalize_target_id(target_identifier)`
3. **Channel + Target Combination**: `CHANNEL::target_identifier`

### Action on Duplicate Match:
- `duplicate_flag = True`
- `status = "BLOCKED_DUPLICATE"`
- `duplicate_reason = "Duplicate source URL / target match in history"`
- **Result**: Prevents multiple contributions to the same issue, repo, thread, or channel target.

---

## 4. Prospect Eligibility Criteria

A candidate opportunity is classified as `ELIGIBLE_FOR_DRAFT` if and only if it satisfies all of the following conditions:
1. `self_target_flag == False` (Third-party target)
2. `duplicate_flag == False` (Target never previously processed)
3. `relevance_score >= 50` (Relevant quantitative technical context)
4. `intent_score >= 40` (Demonstrated technical problem or verification question)
5. `promotion_risk <= 35` (No spam or aggressive advertising risk)

---

## 5. Local Draft Specification & Mandatory Human Approval

Every draft generated for an eligible prospect adheres to the following strict schema:

```json
{
  "draft_id": "draft_a1b2c3d4e5",
  "prospect_id": "prospect_f6g7h8i9j0",
  "created_at_utc": "2026-08-30T17:45:00.000000+00:00",
  "channel": "GITHUB",
  "source_url": "https://github.com/stat-arb/pairs-trading-engine/issues/42",
  "proposed_message": "### Quantitative Diagnostic: ...",
  "value_provided_summary": "Technical diagnostic overview for cointegration test stability",
  "call_to_action": "Optional link to public quantitative verification tool.",
  "approval_status": "PENDING_HUMAN_APPROVAL",
  "external_publication_status": "NOT_ATTEMPTED",
  "human_approval_required": true
}
```

### Safety Protections:
- `approval_status`: Hardcoded to `"PENDING_HUMAN_APPROVAL"`.
- `external_publication_status`: Hardcoded to `"NOT_ATTEMPTED"`.
- `human_approval_required`: Hardcoded to `true`.
- **Tone & Content**: Objective, technical, and educational. Zero profit claims, zero performance guarantees, zero aggressive marketing.

---

## 6. Zero Automated Publication Guarantee

The pipeline **NEVER** publishes draft contributions automatically in default mode.
- External HTTP POST endpoints are disabled in default safe mode (`DISCOVERY_AND_DRAFT_ONLY`).
- To execute an external API call, `--allow-external-publication` must be passed explicitly to the runner.
- In default `--once` execution, `EXTERNAL_PUBLICATION_ATTEMPTED = FALSE`.

---

## 7. How to Review Generated Local Drafts

1. Open `logs/portfolio/drafts.jsonl` in any text editor or JSON viewer.
2. Filter entries by `"approval_status": "PENDING_HUMAN_APPROVAL"`.
3. Inspect `proposed_message`, `source_url`, and `value_provided_summary`.
4. To approve or modify a draft, edit the `approval_status` field locally or keep for manual copy-paste review.
