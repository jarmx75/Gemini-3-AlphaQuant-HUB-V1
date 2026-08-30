"""
Prospect Pipeline & Local Draft Engine (Sprint #36.6.1 / Etapa 2.1)

Features:
- Safe prospect tracking without external HTTP side-effects.
- Self-targeting exclusion via SelfIdentityConfig.
- Explicit Trust Classification System (VERIFIED_EXTERNAL_SOURCE, UNVERIFIED_EXTERNAL_SOURCE, TEMPLATE_OR_SYNTHETIC, INTERNAL_OR_SELF, HISTORICAL_IMPORTED).
- Strict Eligibility Gate: ONLY VERIFIED_EXTERNAL_SOURCE can receive ELIGIBLE_FOR_DRAFT status.
- Persistent deduplication by source_url, target_identifier, and channel combination.
- Local draft generation with mandatory human approval (PENDING_HUMAN_APPROVAL / NOT_ATTEMPTED).
- Historical draft & prospect remediation (INVALIDATED_SOURCE_NOT_VERIFIED) for unverified/template drafts.
"""

import os
import json
import logging
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

from src.economics.self_identity_config import SelfIdentityConfig

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def _get_log_dir() -> Path:
    d = Path(os.environ.get('PAYPAL_LOG_DIR') or ('/tmp/logs/portfolio' if os.environ.get('VERCEL') or not os.access(PROJECT_ROOT, os.W_OK) else PROJECT_ROOT / 'logs' / 'portfolio'))
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        d = Path('/tmp/logs/portfolio')
        d.mkdir(parents=True, exist_ok=True)
    return d

LOGS_PORTFOLIO_DIR = _get_log_dir()
PROSPECTS_JSONL = LOGS_PORTFOLIO_DIR / "prospects.jsonl"
DRAFTS_JSONL = LOGS_PORTFOLIO_DIR / "drafts.jsonl"
OPPORTUNITY_POOL_FILE = LOGS_PORTFOLIO_DIR / "opportunity_pool.jsonl"
EVENT_HISTORY_FILE = LOGS_PORTFOLIO_DIR / "external_acquisition_event_history.jsonl"


def normalize_url(url: str) -> str:
    """Normalizes URL for strict deduplication matching."""
    if not url:
        return ""
    clean = url.strip().lower().rstrip("/")
    if "#" in clean:
        clean = clean.split("#")[0]
    return clean


def normalize_target_id(target_id: str) -> str:
    """Normalizes target identifier for strict deduplication matching."""
    if not target_id:
        return ""
    return target_id.strip().lower()


def classify_source_trust(candidate: Dict[str, Any]) -> str:
    """
    Classifies candidate source trust according to Etapa 3.1 strict verification rules:
    - INTERNAL_OR_SELF: Owner repo, user, domain, or keyword match.
    - TEMPLATE_OR_SYNTHETIC: Candidate generated from template, mock adapter fixture, or simulated candidate.
    - UNVERIFIED_EXTERNAL_SOURCE: Appears external but lacks current HTTP 200 verification proof.
    - HISTORICAL_IMPORTED: Inherited data without verified source.
    - VERIFIED_EXTERNAL_SOURCE: Authenticated live API response with HTTP 200 status or live API verification.
    """
    if not candidate:
        return "UNKNOWN"

    is_self, _, _ = SelfIdentityConfig.is_self_target(candidate)
    if is_self:
        return "INTERNAL_OR_SELF"

    explicit_trust = candidate.get("source_trust_classification")

    if explicit_trust == "VERIFIED_EXTERNAL_SOURCE":
        proof = candidate.get("verification_proof")
        if candidate.get("is_live_api_verified") or (isinstance(proof, dict) and proof.get("http_status") == 200):
            return "VERIFIED_EXTERNAL_SOURCE"
        return "UNVERIFIED_EXTERNAL_SOURCE"

    if explicit_trust in ["UNVERIFIED_EXTERNAL_SOURCE", "TEMPLATE_OR_SYNTHETIC", "INTERNAL_OR_SELF", "HISTORICAL_IMPORTED"]:
        return explicit_trust

    is_synthetic = candidate.get("is_synthetic", False) or candidate.get("is_template", False)
    if is_synthetic or candidate.get("source_type") == "TEMPLATE":
        return "TEMPLATE_OR_SYNTHETIC"

    return "UNVERIFIED_EXTERNAL_SOURCE"


class ProspectPipelineEngine:
    """
    Prospect Qualification and Safe Local Draft Pipeline Engine.
    Discovers, scores, and qualifies candidate opportunities without ANY external publication.
    Enforces that ONLY candidates with VERIFIED_EXTERNAL_SOURCE can receive ELIGIBLE_FOR_DRAFT
    and create local contributions (status = PENDING_HUMAN_APPROVAL).
    """

    MAX_DRAFTS_PER_RUN = 5

    def __init__(self, prospects_file: Optional[Path] = None, drafts_file: Optional[Path] = None):
        self.prospects_file = prospects_file or PROSPECTS_JSONL
        self.drafts_file = drafts_file or DRAFTS_JSONL
        self.drafts_created_this_run = 0
        LOGS_PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()
        self.remediate_existing_data()

    def _ensure_storage(self):
        if not self.prospects_file.exists():
            self.prospects_file.touch()
        if not self.drafts_file.exists():
            self.drafts_file.touch()

    def remediate_existing_data(self):
        """
        Etapa 3.1 Strict Remediation Routine:
        Remediates any pre-existing prospect or draft record that lacks current HTTP 200 verification proof.
        Invalidates unverified drafts to INVALIDATED_SOURCE_NOT_VERIFIED and downgrades prospects to HISTORICAL_IMPORTED.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Remediate Prospects
        if self.prospects_file.exists():
            try:
                prospects = []
                p_modified = False
                with open(self.prospects_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        p = json.loads(line)
                        is_self, _, _ = SelfIdentityConfig.is_self_target(p)

                        proof = p.get("verification_proof")
                        has_valid_proof = (
                            isinstance(proof, dict)
                            and proof.get("http_status") == 200
                            and proof.get("github_api_endpoint")
                        )

                        if is_self:
                            p["status"] = "BLOCKED_SELF_TARGET"
                            p["self_target_flag"] = True
                            p["ownership_classification"] = "SELF"
                            p["source_trust_classification"] = "INTERNAL_OR_SELF"
                            p_modified = True
                        elif not has_valid_proof:
                            if p.get("status") in ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"]:
                                p["status"] = "BLOCKED_HISTORICAL_UNVERIFIED"
                                p["source_trust_classification"] = "HISTORICAL_IMPORTED"
                                p["invalidation_reason"] = "Lacks current HTTP 200 GitHub REST API verification proof"
                                p_modified = True
                            elif p.get("source_trust_classification") == "VERIFIED_EXTERNAL_SOURCE":
                                p["source_trust_classification"] = "HISTORICAL_IMPORTED"
                                p_modified = True

                        prospects.append(p)

                if p_modified:
                    with open(self.prospects_file, "w", encoding="utf-8") as f:
                        for p in prospects:
                            f.write(json.dumps(p) + "\n")
            except Exception as e:
                logger.warning(f"Error remediating prospects: {e}")

        # 2. Remediate Drafts
        if self.drafts_file.exists():
            try:
                drafts = []
                d_modified = False
                with open(self.drafts_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        d = json.loads(line)

                        proof = d.get("verification_proof")
                        has_valid_proof = (
                            isinstance(proof, dict)
                            and proof.get("http_status") == 200
                        )

                        if d.get("approval_status") == "PENDING_HUMAN_APPROVAL" and not has_valid_proof:
                            d["approval_status"] = "INVALIDATED_SOURCE_NOT_VERIFIED"
                            d["external_publication_status"] = "NOT_ATTEMPTED"
                            d["source_trust_classification"] = "HISTORICAL_IMPORTED"
                            d["invalidation_reason"] = "Lacks current HTTP 200 GitHub REST API verification proof"
                            d["invalidated_at_utc"] = now_iso
                            d_modified = True
                        drafts.append(d)

                if d_modified:
                    with open(self.drafts_file, "w", encoding="utf-8") as f:
                        for d in drafts:
                            f.write(json.dumps(d) + "\n")
            except Exception as e:
                logger.warning(f"Error remediating existing drafts data: {e}")

    def load_processed_targets_history(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Loads historical processed URLs, target_identifiers, and channel+target keys
        from prospects.jsonl, opportunity_pool.jsonl, and external_acquisition_event_history.jsonl.
        """
        urls: Set[str] = set()
        targets: Set[str] = set()
        channel_targets: Set[str] = set()

        if self.prospects_file.exists():
            try:
                with open(self.prospects_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                            u = normalize_url(item.get("source_url", ""))
                            t = normalize_target_id(item.get("target_identifier", ""))
                            c = str(item.get("channel", "")).upper()
                            if u: urls.add(u)
                            if t: targets.add(t)
                            if c and t: channel_targets.add(f"{c}::{t}")
                        except Exception:
                            pass
            except Exception:
                pass

        if OPPORTUNITY_POOL_FILE.exists():
            try:
                with open(OPPORTUNITY_POOL_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                            u = normalize_url(item.get("source_url", ""))
                            t = normalize_target_id(item.get("thread_id", item.get("target_identifier", "")))
                            c = str(item.get("channel", "")).upper()
                            if u: urls.add(u)
                            if t: targets.add(t)
                            if c and t: channel_targets.add(f"{c}::{t}")
                        except Exception:
                            pass
            except Exception:
                pass

        if EVENT_HISTORY_FILE.exists():
            try:
                with open(EVENT_HISTORY_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                            u = normalize_url(item.get("external_url", item.get("source_url", "")))
                            t = normalize_target_id(item.get("target_id", ""))
                            c = str(item.get("channel", "")).upper()
                            if u: urls.add(u)
                            if t: targets.add(t)
                            if c and t: channel_targets.add(f"{c}::{t}")
                        except Exception:
                            pass
            except Exception:
                pass

        return urls, targets, channel_targets

    def process_candidate_opportunity(self, candidate: Dict[str, Any], history_state: Optional[Tuple[Set[str], Set[str], Set[str]]] = None) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Evaluates candidate opportunity through:
        1. Trust Classification System (VERIFIED, UNVERIFIED, TEMPLATE, INTERNAL_OR_SELF)
        2. Self-targeting exclusion check
        3. Persistent deduplication check
        4. Relevance qualification
        5. Prospect record creation
        6. Local draft generation ONLY for VERIFIED_EXTERNAL_SOURCE
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        if history_state:
            hist_urls, hist_targets, hist_channel_targets = history_state
        else:
            hist_urls, hist_targets, hist_channel_targets = self.load_processed_targets_history()

        raw_url = candidate.get("source_url", "")
        norm_url = normalize_url(raw_url)
        raw_target = candidate.get("target_identifier", candidate.get("thread_id", candidate.get("repository", "")))
        norm_target = normalize_target_id(raw_target)
        channel = str(candidate.get("channel", "UNKNOWN")).upper()
        ch_target_key = f"{channel}::{norm_target}" if norm_target else ""

        context_score = int(candidate.get("context_score", 0))
        intent_score = int(candidate.get("intent_score", 0))
        promo_risk = int(candidate.get("promotion_risk", 0))

        is_self, self_reason, ownership = SelfIdentityConfig.is_self_target(candidate)
        trust_class = classify_source_trust(candidate)

        if is_self:
            trust_class = "INTERNAL_OR_SELF"
            ownership = "SELF"

        is_duplicate = False
        dup_reason = None

        if norm_url and norm_url in hist_urls:
            is_duplicate = True
            dup_reason = f"Duplicate source URL match: '{raw_url}'"
        elif norm_target and norm_target in hist_targets:
            is_duplicate = True
            dup_reason = f"Duplicate target identifier match: '{raw_target}'"
        elif ch_target_key and ch_target_key in hist_channel_targets:
            is_duplicate = True
            dup_reason = f"Duplicate channel-target match: '{ch_target_key}'"

        if is_self or trust_class == "INTERNAL_OR_SELF":
            status = "BLOCKED_SELF_TARGET"
            evidence_summary = self_reason or "Self-target match"
        elif is_duplicate:
            status = "BLOCKED_DUPLICATE"
            evidence_summary = dup_reason or "Duplicate match"
        elif trust_class == "TEMPLATE_OR_SYNTHETIC":
            status = "BLOCKED_TEMPLATE_OR_SYNTHETIC"
            evidence_summary = "Candidate generated from template, mock adapter fixture, or synthetic data"
        elif trust_class == "UNVERIFIED_EXTERNAL_SOURCE":
            status = "PENDING_SOURCE_VERIFICATION"
            evidence_summary = "Source appears external but lacks cryptographic/API proof"
        elif trust_class == "HISTORICAL_IMPORTED":
            status = "BLOCKED_HISTORICAL_UNVERIFIED"
            evidence_summary = "Historical imported data without verification proof"
        elif context_score < 50 or intent_score < 40:
            status = "BLOCKED_LOW_RELEVANCE"
            evidence_summary = f"Low scores (context: {context_score}, intent: {intent_score})"
        elif trust_class == "VERIFIED_EXTERNAL_SOURCE":
            status = "ELIGIBLE_FOR_DRAFT"
            evidence_summary = "Verified external source passed all safety and relevance gates"
        else:
            status = "PENDING_SOURCE_VERIFICATION"
            evidence_summary = f"Unclassified trust level: {trust_class}"

        prospect_id = f"prospect_{hashlib.md5(f'{channel}_{norm_url}_{norm_target}'.encode()).hexdigest()[:10]}"

        prospect_entry = {
            "prospect_id": prospect_id,
            "discovered_at_utc": timestamp,
            "channel": channel,
            "source_url": raw_url,
            "source_type": candidate.get("category", "TECHNICAL_QUESTION"),
            "target_identifier": raw_target,
            "context_summary": candidate.get("context", "Technical quantitative opportunity"),
            "relevance_score": context_score,
            "intent_score": intent_score,
            "promotion_risk": promo_risk,
            "ownership_classification": ownership,
            "source_trust_classification": trust_class,
            "self_target_flag": is_self,
            "duplicate_flag": is_duplicate,
            "duplicate_reason": dup_reason,
            "evidence": {
                "summary": evidence_summary,
                "context_score": context_score,
                "intent_score": intent_score,
                "promotion_risk": promo_risk,
                "trust_classification": trust_class,
                "self_block_reason": self_reason,
                "dup_block_reason": dup_reason
            },
            "status": status
        }

        self._append_prospect(prospect_entry)

        if norm_url: hist_urls.add(norm_url)
        if norm_target: hist_targets.add(norm_target)
        if ch_target_key: hist_channel_targets.add(ch_target_key)

        draft_entry = None
        if status == "ELIGIBLE_FOR_DRAFT":
            if self.drafts_created_this_run < self.MAX_DRAFTS_PER_RUN:
                draft_entry = self.generate_local_draft(prospect_entry)
                prospect_entry["status"] = "DRAFT_CREATED"
                self.drafts_created_this_run += 1
            else:
                prospect_entry["status"] = "BLOCKED_MAX_DRAFTS_CAP"
                prospect_entry["evidence_summary"] = f"Max draft generation cap of {self.MAX_DRAFTS_PER_RUN} reached for this run"

        return prospect_entry, draft_entry

    def generate_local_draft(self, prospect: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates objective, non-promotional technical educational contribution for human approval.
        ONLY invoked for prospects with VERIFIED_EXTERNAL_SOURCE.
        Enforces approval_status = PENDING_HUMAN_APPROVAL and external_publication_status = NOT_ATTEMPTED.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        draft_id = f"draft_{uuid.uuid4().hex[:10]}"
        
        context_str = prospect.get("context_summary", "Quantitative Strategy Overfitting Audit")
        issue_title = context_str.split("|")[0].strip() if "|" in context_str else context_str
        raw_id = str(prospect.get("target_identifier", "quant_repo"))
        repo_name = prospect.get("repository") or (raw_id.replace("github_", "").rsplit("_", 1)[0].replace("_", "/") if "_" in raw_id else "quant-repo")
        issue_num = raw_id.rsplit("_", 1)[-1] if "_" in raw_id else "1"

        proposed_message = f"""
### Technical Observation: {issue_title} ({repo_name})

When auditing quantitative model robustness for open issues on {repo_name}:
1. **Out-of-Sample Resampling**: Apply stationary block bootstrap to evaluate return distribution stability across market regimes.
2. **Execution Friction**: Deduct spread and slippage friction roundtrip before computing Sharpe ratio.
3. **Overfitting Diagnostic**: Measure Probability of Backtest Overfitting (PBO) across N sub-partitions.

*Educational note*: Technical diagnostic observation for issue #{issue_num}.
        """.strip()

        draft_entry = {
            "draft_id": draft_id,
            "prospect_id": prospect["prospect_id"],
            "created_at_utc": timestamp,
            "channel": prospect["channel"],
            "source_url": prospect["source_url"],
            "source_trust_classification": prospect.get("source_trust_classification", "VERIFIED_EXTERNAL_SOURCE"),
            "verification_proof": prospect.get("verification_proof"),
            "proposed_message": proposed_message,
            "value_provided_summary": f"Technical diagnostic observation regarding '{issue_title}' on repository {repo_name}",
            "call_to_action": "Optional link to public quantitative verification tool.",
            "approval_status": "PENDING_HUMAN_APPROVAL",
            "external_publication_status": "NOT_ATTEMPTED",
            "human_approval_required": True
        }

        self._append_draft(draft_entry)
        return draft_entry

    def evaluate_pipeline_telemetry(self) -> Dict[str, Any]:
        """
        Calculates mathematical pipeline telemetry metrics enforcing all invariants.
        Invariants:
        1. prospects_discovered == sum(mutually_exclusive_statuses)
        2. local_drafts_created <= prospects_eligible
        3. blocked_self_target accurately reflects self-owned candidates
        """
        prospects = self.load_all_prospects()
        drafts = self.load_all_drafts()

        discovered = len(prospects)
        eligible = len([p for p in prospects if p.get("status") in ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"]])
        blocked_self = len([p for p in prospects if p.get("status") == "BLOCKED_SELF_TARGET"])
        blocked_dup = len([p for p in prospects if p.get("status") == "BLOCKED_DUPLICATE"])
        pending_verif = len([p for p in prospects if p.get("status") == "PENDING_SOURCE_VERIFICATION"])
        template_synth = len([p for p in prospects if p.get("status") == "BLOCKED_TEMPLATE_OR_SYNTHETIC"])
        low_relevance = len([p for p in prospects if p.get("status") == "BLOCKED_LOW_RELEVANCE"])
        historical_unverified = len([p for p in prospects if p.get("status") == "BLOCKED_HISTORICAL_UNVERIFIED"])
        max_drafts_cap_blocked = len([p for p in prospects if p.get("status") == "BLOCKED_MAX_DRAFTS_CAP"])

        valid_drafts = len([d for d in drafts if d.get("approval_status") == "PENDING_HUMAN_APPROVAL"])

        return {
            "prospects_discovered": discovered,
            "prospects_eligible": eligible,
            "blocked_self_target": blocked_self,
            "blocked_duplicate": blocked_dup,
            "pending_source_verification": pending_verif,
            "template_or_synthetic": template_synth,
            "blocked_low_relevance": low_relevance,
            "blocked_historical_unverified": historical_unverified,
            "blocked_max_drafts_cap": max_drafts_cap_blocked,
            "internal_or_self": blocked_self,
            "local_drafts_created": valid_drafts,
            "total_drafts_in_log": len(drafts),
            "invalidated_drafts": len([d for d in drafts if d.get("approval_status") == "INVALIDATED_SOURCE_NOT_VERIFIED"])
        }

    def _append_prospect(self, prospect: Dict[str, Any]):
        try:
            with open(self.prospects_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(prospect) + "\n")
        except Exception as e:
            logger.warning(f"Error saving prospect: {e}")

    def _append_draft(self, draft: Dict[str, Any]):
        try:
            with open(self.drafts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(draft) + "\n")
        except Exception as e:
            logger.warning(f"Error saving draft: {e}")

    def load_all_prospects(self) -> List[Dict[str, Any]]:
        prospects = []
        if self.prospects_file.exists():
            try:
                with open(self.prospects_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            prospects.append(json.loads(line))
            except Exception:
                pass
        return prospects

    def load_all_drafts(self) -> List[Dict[str, Any]]:
        drafts = []
        if self.drafts_file.exists():
            try:
                with open(self.drafts_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            drafts.append(json.loads(line))
            except Exception:
                pass
        return drafts
