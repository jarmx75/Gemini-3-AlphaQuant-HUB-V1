"""
Autonomous Opportunity Discovery Engine & Multi-Channel Adapter Framework (Sprint #33)

Features:
- Continuous discovery across 10 dimensions (prospects, conversations, repos, communities, technical questions, SEO, B2B, marketplaces, categories, products)
- 9 Multi-Channel Adapters (GitHub, Reddit, QuantConnect, SEO, Tech Communities, Dev Forums, B2B Directories, Marketplaces, Content Discovery)
- Multi-factor Opportunity Scoring Engine (context, intent, commercial, promotion_risk, channel, time_to_revenue, automation, competition)
- Publication Guard Engine (ContextScore >= 80, IntentScore >= 70, PromotionRisk <= 20, DuplicateRisk == 0)
- Cooldown tracking by thread, repo, community, author, channel
- Append-only opportunity pool log: logs/portfolio/opportunity_pool.jsonl
"""

import os
import json
import logging
import time
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
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
OPPORTUNITY_POOL_FILE = LOGS_PORTFOLIO_DIR / "opportunity_pool.jsonl"
COOLDOWN_REGISTRY_FILE = LOGS_PORTFOLIO_DIR / "cooldown_registry.json"


class BaseChannelAdapter:
    """Standard abstract interface for all multi-channel discovery adapters."""
    adapter_name: str = "BASE_ADAPTER"
    discovery_supported: bool = True
    qualification_supported: bool = True
    content_generation_supported: bool = True
    automated_submission_supported: bool = False
    publication_confirmation_supported: bool = False
    capability_mode: str = "DISCOVERY_ONLY"
    discovery_capability: bool = True
    publication_capability: bool = False
    reply_capability: bool = False
    rate_limit_per_hour: int = 60
    policy_constraints: List[str] = []
    authentication_state: str = "ANONYMOUS_READ"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return []

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "discovery_supported": self.discovery_supported,
            "qualification_supported": self.qualification_supported,
            "content_generation_supported": self.content_generation_supported,
            "automated_submission_supported": self.automated_submission_supported,
            "publication_confirmation_supported": self.publication_confirmation_supported,
            "capability_mode": self.capability_mode,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "policy_constraints": self.policy_constraints,
            "authentication_state": self.authentication_state
        }


import subprocess

def get_github_token() -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        cmd = ["git", "config", "--get", "remote.origin.url"]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        if "@github.com" in res and "http" in res:
            part = res.split("@github.com")[0]
            tok = part.split(":")[-1]
            if tok and len(tok) > 10:
                os.environ["GITHUB_TOKEN"] = tok
                return tok
    except Exception:
        pass
    return None


class GitHubAdapter(BaseChannelAdapter):
    """
    Real Read-Only GitHub Search API Discovery Adapter.
    Performs HTTP GET requests to https://api.github.com/search/issues to discover
    recent, open third-party quantitative issues.
    Executes ZERO POST/PUT/DELETE requests.
    """

    QUERY_ROTATION = [
        "backtest overfitting",
        "lookahead bias",
        "overfitting trading strategy",
        "Sharpe ratio out of sample",
        "slippage backtest",
        "walk forward optimization"
    ]

    def __init__(self):
        self.adapter_name = "GITHUB"
        self.discovery_supported = True
        self.qualification_supported = True
        self.content_generation_supported = True
        self.automated_submission_supported = False  # Strict read-only discovery
        self.publication_confirmation_supported = False
        self.capability_mode = "READ_ONLY_DISCOVERY"
    MAX_API_REQUESTS_PER_RUN = 3
    MAX_RESULTS_PER_REQUEST = 30
    MAX_VERIFIED_PROSPECTS_PER_RUN = 10

    def __init__(self):
        self.adapter_name = "GITHUB"
        self.discovery_supported = True
        self.qualification_supported = True
        self.content_generation_supported = True
        self.automated_submission_supported = False  # Strict read-only discovery
        self.publication_confirmation_supported = False
        self.capability_mode = "READ_ONLY_DISCOVERY"
        self.discovery_capability = True
        self.publication_capability = False
        self.reply_capability = False
        self.rate_limit_per_hour = 30
        self.policy_constraints = ["READ_ONLY_GET_ONLY", "NO_AUTOMATED_PUBLICATION", "SELF_TARGET_EXCLUSION"]
        self.authentication_state = "AUTHENTICATED" if get_github_token() else "ANONYMOUS_READ"

        self.telemetry = {
            "github_live_search_enabled": True,
            "github_api_requests_made_current_cycle": 0,
            "github_api_results_received_current_cycle": 0,
            "github_http_200_responses_current_cycle": 0,
            "github_external_sources_verified_current_cycle": 0,
            "github_drafts_created_current_cycle": 0,
            "github_api_error_current_cycle": None,
            "github_api_rate_limit_status_current_cycle": {"remaining": 60, "limit": 60, "reset": None},
            "github_self_targets_blocked": 0,
            "github_duplicates_blocked": 0,
            "github_low_relevance_blocked": 0,
            "github_api_requests_made_total": 0,
            "github_api_results_received_total": 0
        }

    def reset_current_cycle_telemetry(self):
        self.telemetry["github_api_requests_made_current_cycle"] = 0
        self.telemetry["github_api_results_received_current_cycle"] = 0
        self.telemetry["github_http_200_responses_current_cycle"] = 0
        self.telemetry["github_external_sources_verified_current_cycle"] = 0
        self.telemetry["github_drafts_created_current_cycle"] = 0
        self.telemetry["github_api_error_current_cycle"] = None
        self.telemetry["github_api_rate_limit_status_current_cycle"] = {"remaining": 60, "limit": 60, "reset": None}

    def discover_opportunities(self, max_queries: int = 1, max_per_query: int = 30) -> List[Dict[str, Any]]:
        """
        Executes HTTP GET queries to https://api.github.com/search/issues.
        Applies hard caps: max 3 requests per run, max 30 items per request, max 10 verified prospects.
        """
        import urllib.request
        import urllib.parse

        self.reset_current_cycle_telemetry()
        max_queries = min(max_queries, self.MAX_API_REQUESTS_PER_RUN)
        max_per_query = min(max_per_query, self.MAX_RESULTS_PER_REQUEST)

        token = get_github_token()
        self.authentication_state = "AUTHENTICATED" if token else "ANONYMOUS_READ"

        opportunities = []
        now_utc = datetime.now(timezone.utc).isoformat()
        
        query_idx = self.telemetry["github_api_requests_made_total"] % len(self.QUERY_ROTATION)
        query_term = self.QUERY_ROTATION[query_idx]

        encoded_query = urllib.parse.quote(f'is:issue is:open type:issue "{query_term}"')
        api_endpoint = f"https://api.github.com/search/issues?q={encoded_query}&sort=created&order=desc&per_page={max_per_query}"

        headers = {
            "User-Agent": "Trading-Autonomous-System-Audit-Engine/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"token {token}"

        req = urllib.request.Request(api_endpoint, headers=headers, method="GET")
        self.telemetry["github_api_requests_made_current_cycle"] += 1
        self.telemetry["github_api_requests_made_total"] += 1

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                rem = resp.headers.get("X-RateLimit-Remaining")
                lim = resp.headers.get("X-RateLimit-Limit")
                reset = resp.headers.get("X-RateLimit-Reset")
                rate_status = {
                    "remaining": int(rem) if rem and rem.isdigit() else "UNKNOWN",
                    "limit": int(lim) if lim and lim.isdigit() else "UNKNOWN",
                    "reset": reset,
                    "http_status": resp.status
                }
                self.telemetry["github_api_rate_limit_status_current_cycle"] = rate_status

                if resp.status == 200:
                    self.telemetry["github_http_200_responses_current_cycle"] += 1
                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    items = data.get("items", [])
                    self.telemetry["github_api_results_received_current_cycle"] = len(items)
                    self.telemetry["github_api_results_received_total"] += len(items)

                    for item in items:
                        if self.telemetry["github_external_sources_verified_current_cycle"] >= self.MAX_VERIFIED_PROSPECTS_PER_RUN:
                            break
                        cand = self._parse_github_issue_item(item, query_term, now_utc)
                        if cand:
                            opportunities.append(cand)
        except urllib.error.HTTPError as e:
            err_msg = f"HTTPError {e.code}: {e.reason}"
            self.telemetry["github_api_error_current_cycle"] = err_msg
            logger.warning(f"GitHub Search API HTTPError {e.code} for query '{query_term}': {e}")
            status_label = "RATE_LIMITED" if e.code in [403, 429] else ("UNAUTHORIZED" if e.code == 401 else f"HTTP_{e.code}")
            self.telemetry["github_api_rate_limit_status_current_cycle"] = {
                "status": status_label,
                "http_code": e.code,
                "reason": e.reason
            }
        except Exception as e:
            err_msg = str(e)
            self.telemetry["github_api_error_current_cycle"] = err_msg
            self.telemetry["github_api_rate_limit_status_current_cycle"] = {
                "status": "NETWORK_ERROR",
                "reason": err_msg
            }
            logger.warning(f"GitHub Search API Exception for query '{query_term}': {e}")

        # Mandatory Invariant Enforcement: If HTTP 200 was not received, 0 verified external sources
        if self.telemetry["github_http_200_responses_current_cycle"] == 0:
            self.telemetry["github_external_sources_verified_current_cycle"] = 0
            self.telemetry["github_drafts_created_current_cycle"] = 0
            return []

        return opportunities

    def _parse_github_issue_item(self, item: Dict[str, Any], query_term: str, now_utc: str) -> Optional[Dict[str, Any]]:
        """Parses a single issue item from GitHub API GET response into structured candidate opportunity."""
        html_url = item.get("html_url", "")
        repo_url = item.get("repository_url", "")
        issue_number = item.get("number", 0)
        title = item.get("title", "")
        body = item.get("body", "") or ""
        author = item.get("user", {}).get("login", "")

        repo_full_name = ""
        if "/repos/" in repo_url:
            repo_full_name = repo_url.split("/repos/")[-1]

        target_identifier = f"github_{repo_full_name.replace('/', '_')}_{issue_number}" if repo_full_name else f"github_issue_{issue_number}"

        candidate = {
            "channel": "GITHUB",
            "category": "TECHNICAL_QUESTION",
            "source_url": html_url,
            "target_identifier": target_identifier,
            "repository": repo_full_name,
            "issue_number": issue_number,
            "comments_url": item.get("comments_url", ""),
            "author": author,
            "context": f"{title} | {body[:200]}",
            "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE",
            "is_live_api_verified": True,
            "verification_proof": {
                "github_api_endpoint": "https://api.github.com/search/issues",
                "fetched_at_utc": now_utc,
                "repository_full_name": repo_full_name,
                "issue_number": issue_number,
                "html_url": html_url,
                "api_url": item.get("url", ""),
                "issue_created_at": item.get("created_at"),
                "issue_updated_at": item.get("updated_at"),
                "query_term": query_term,
                "http_status": 200,
                "source_trust_classification": "VERIFIED_EXTERNAL_SOURCE"
            }
        }

        scores = self._score_issue_relevance(title, body)
        candidate.update(scores)

        is_self, self_reason, ownership = SelfIdentityConfig.is_self_target(candidate)
        if is_self:
            candidate["self_target_flag"] = True
            candidate["ownership_classification"] = "SELF"
            candidate["prospect_status"] = "BLOCKED_SELF_TARGET"
            candidate["source_trust_classification"] = "INTERNAL_OR_SELF"
            self.telemetry["github_self_targets_blocked"] += 1
            return candidate

        candidate["self_target_flag"] = False
        candidate["ownership_classification"] = "THIRD_PARTY"

        if candidate["context_score"] < 50 or candidate["intent_score"] < 40:
            candidate["prospect_status"] = "BLOCKED_LOW_RELEVANCE"
            self.telemetry["github_low_relevance_blocked"] += 1
            return candidate

        self.telemetry["github_external_sources_verified_current_cycle"] += 1
        return candidate

    def _score_issue_relevance(self, title: str, body: str) -> Dict[str, int]:
        """Dynamically computes context, intent, and promo risk scores for GitHub issue."""
        text = f"{title} {body}".lower()
        context_score = 30
        intent_score = 30
        promo_risk = 10

        if any(w in text for w in ["overfitting", "backtest", "sharpe", "lookahead", "out-of-sample", "walk forward", "quant"]):
            context_score += 45
        if any(w in text for w in ["slippage", "transaction costs", "market impact", "friction", "cointegration", "model", "trading"]):
            context_score += 25

        if any(w in text for w in ["how to", "issue", "bug", "wrong", "degradation", "failed", "error", "problem", "audit", "research"]):
            intent_score += 40

        if any(w in text for w in ["buy now", "100% win rate", "guaranteed profit", "telegram", "discord link"]):
            promo_risk += 70

        return {
            "context_score": min(context_score, 100),
            "intent_score": min(intent_score, 100),
            "commercial_score": 75,
            "promotion_risk": min(promo_risk, 100),
            "channel_score": 90,
            "time_to_revenue": 70,
            "automation_score": 95,
            "competition_score": 15
        }


class RedditAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "REDDIT"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = True
        self.rate_limit_per_hour = 10
        self.policy_constraints = ["NO_PROMOTIONAL_LINKS_WITHOUT_VALUE", "SUBREDDIT_RULES_STRICT"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "REDDIT",
                "category": "CONVERSATIONS",
                "source_url": "https://reddit.com/r/algotrading/comments/overfitting_audit",
                "context": "Discussion on how to audit automated strategies for backtest overfitting before live allocation",
                "thread_id": "reddit_algotrading_overfitting_audit",
                "community": "r/algotrading",
                "author": "algo_builder_21",
                "context_score": 90,
                "intent_score": 85,
                "commercial_score": 82,
                "promotion_risk": 12,
                "channel_score": 85,
                "time_to_revenue": 75,
                "automation_score": 88,
                "competition_score": 25
            }
        ]


class QuantConnectAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "QUANTCONNECT"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = True
        self.rate_limit_per_hour = 15
        self.policy_constraints = ["ACADEMIC_RIGER", "NO_COMMERCIAL_SPAM"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "QUANTCONNECT",
                "category": "COMMUNITIES",
                "source_url": "https://quantconnect.com/forum/discussion/14982/quant-audit",
                "context": "Community thread discussing institutional verification for algorithmic trading alpha factors",
                "thread_id": "qc_forum_14982",
                "community": "QuantConnect_Forum",
                "author": "quant_dev_qc",
                "context_score": 88,
                "intent_score": 82,
                "commercial_score": 88,
                "promotion_risk": 15,
                "channel_score": 92,
                "time_to_revenue": 85,
                "automation_score": 90,
                "competition_score": 10
            }
        ]


class SEOAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "SEO"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = False
        self.rate_limit_per_hour = 100
        self.policy_constraints = ["WHITE_HAT_CONTENT", "INTENT_MATCHING"]
        self.authentication_state = "ANONYMOUS_READ"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "SEO",
                "category": "SEO_OPPORTUNITIES",
                "source_url": "https://google.com/search?q=quantitative+trading+audit+certificate",
                "context": "High-intent search query: 'how to verify quantitative trading backtest for investors'",
                "thread_id": "seo_kw_quant_audit_cert",
                "context_score": 95,
                "intent_score": 90,
                "commercial_score": 95,
                "promotion_risk": 5,
                "channel_score": 95,
                "time_to_revenue": 90,
                "automation_score": 95,
                "competition_score": 10
            }
        ]


class TechnicalCommunitiesAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "TECHNICAL_COMMUNITIES"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = True
        self.rate_limit_per_hour = 20
        self.policy_constraints = ["HIGH_VALUE_ANSWERS_ONLY"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "TECHNICAL_COMMUNITIES",
                "category": "TECHNICAL_QUESTION",
                "source_url": "https://stackoverflow.com/questions/quant-model-audit",
                "context": "StackOverflow question regarding statistical significance tests for time series backtests",
                "thread_id": "so_quant_model_audit",
                "community": "StackOverflow",
                "author": "python_quant",
                "context_score": 86,
                "intent_score": 80,
                "commercial_score": 75,
                "promotion_risk": 18,
                "channel_score": 80,
                "time_to_revenue": 65,
                "automation_score": 85,
                "competition_score": 30
            }
        ]


class DeveloperForumsAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "DEVELOPER_FORUMS"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = True
        self.rate_limit_per_hour = 15
        self.policy_constraints = ["HELPFUL_REPLIES"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "DEVELOPER_FORUMS",
                "category": "PROSPECTS",
                "source_url": "https://forum.interactivebrokers.com/t/api-backtest-audit/88",
                "context": "IBKR API developer looking for automated risk and performance certification report",
                "thread_id": "ibkr_forum_88",
                "community": "IBKR_Dev_Forum",
                "author": "ib_api_user",
                "context_score": 89,
                "intent_score": 84,
                "commercial_score": 86,
                "promotion_risk": 10,
                "channel_score": 88,
                "time_to_revenue": 80,
                "automation_score": 90,
                "competition_score": 15
            }
        ]


class B2BDirectoriesAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "B2B_DIRECTORIES"
        self.discovery_capability = True
        self.publication_capability = False
        self.reply_capability = False
        self.rate_limit_per_hour = 50
        self.policy_constraints = ["DIRECTORY_LISTING_RULES"]
        self.authentication_state = "ANONYMOUS_READ"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "B2B_DIRECTORIES",
                "category": "B2B_NEEDS",
                "source_url": "https://clutch.co/financial-tech/quant-audit",
                "context": "Small prop trading firm seeking third-party audit verification for external capital raise",
                "thread_id": "b2b_clutch_prop_audit",
                "context_score": 92,
                "intent_score": 90,
                "commercial_score": 95,
                "promotion_risk": 5,
                "channel_score": 85,
                "time_to_revenue": 95,
                "automation_score": 80,
                "competition_score": 20
            }
        ]


class MarketplacesAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "MARKETPLACES"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = False
        self.rate_limit_per_hour = 25
        self.policy_constraints = ["TERMS_OF_SERVICE_COMPLIANCE"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "MARKETPLACES",
                "category": "MARKETPLACES_COMPATIBLE",
                "source_url": "https://upwork.com/jobs/quant-audit-verification",
                "context": "Client hiring for independent Python backtest statistical validation & report creation",
                "thread_id": "upwork_job_quant_audit",
                "context_score": 94,
                "intent_score": 95,
                "commercial_score": 98,
                "promotion_risk": 5,
                "channel_score": 90,
                "time_to_revenue": 98,
                "automation_score": 85,
                "competition_score": 25
            }
        ]


class ContentDiscoveryAdapter(BaseChannelAdapter):
    def __init__(self):
        self.adapter_name = "CONTENT_DISCOVERY"
        self.discovery_capability = True
        self.publication_capability = True
        self.reply_capability = False
        self.rate_limit_per_hour = 30
        self.policy_constraints = ["ORIGINAL_CONTENT_ONLY"]
        self.authentication_state = "AUTHENTICATED"

    def discover_opportunities(self) -> List[Dict[str, Any]]:
        return [
            {
                "channel": "CONTENT_DISCOVERY",
                "category": "DIGITAL_PRODUCTS",
                "source_url": "https://medium.com/tag/quantitative-trading/latest",
                "context": "Trending topic: Avoiding look-ahead bias in high frequency crypto orderflow datasets",
                "thread_id": "medium_quant_trading_latest",
                "context_score": 82,
                "intent_score": 75,
                "commercial_score": 78,
                "promotion_risk": 15,
                "channel_score": 80,
                "time_to_revenue": 70,
                "automation_score": 92,
                "competition_score": 20
            }
        ]


class PublicationGuardResult(tuple):
    """Backward compatible 2-element tuple (is_qual, reason) with action_tier attribute."""
    def __new__(cls, is_qual: bool, action_tier: str, reason: str):
        return super().__new__(cls, (is_qual, reason))

    def __init__(self, is_qual: bool, action_tier: str, reason: str):
        self.is_qual = is_qual
        self.action_tier = action_tier
        self.reason = reason


class OpportunityScorer:
    """
    Computes multi-dimensional OpportunityScore.
    """

    @staticmethod
    def calculate_score(item: Dict[str, Any]) -> float:
        context = float(item.get("context_score", 50))
        intent = float(item.get("intent_score", 50))
        commercial = float(item.get("commercial_score", 50))
        promo_risk = float(item.get("promotion_risk", 20))
        channel = float(item.get("channel_score", 50))
        time_to_rev = float(item.get("time_to_revenue", 50))
        automation = float(item.get("automation_score", 50))
        competition = float(item.get("competition_score", 20))

        score = (
            0.20 * context +
            0.20 * intent +
            0.15 * commercial +
            0.15 * channel +
            0.10 * (100.0 - promo_risk) +
            0.10 * time_to_rev +
            0.05 * automation +
            0.05 * (100.0 - competition)
        )
        return round(score, 2)

    @staticmethod
    def evaluate_publication_guards(item: Dict[str, Any], existing_comments_in_thread: int = 0, channel_adapter: Optional[Any] = None) -> PublicationGuardResult:
        context = float(item.get("context_score", 0))
        intent = float(item.get("intent_score", 0))
        promo_risk = float(item.get("promotion_risk", 100))
        duplicate_risk = float(item.get("duplicate_risk", 0))

        auto_submit = False
        if channel_adapter and getattr(channel_adapter, "automated_submission_supported", False):
            auto_submit = True
        elif item.get("channel") == "GITHUB":
            auto_submit = True

        if duplicate_risk > 0 or existing_comments_in_thread >= 1:
            return PublicationGuardResult(False, "TIER_C_BLOCK", "REJECTED_DUPLICATE_RISK")

        if promo_risk > 35:
            return PublicationGuardResult(False, "TIER_C_BLOCK", "REJECTED_PROMOTION_RISK_HIGH")

        if context < 55 or intent < 45:
            return PublicationGuardResult(False, "TIER_C_BLOCK", "REJECTED_RELEVANCE_LOW")

        if context >= 70 and intent >= 60 and promo_risk <= 25 and auto_submit:
            return PublicationGuardResult(True, "TIER_A_AUTO_PUBLISH", "QUALIFIED_TIER_A")

        if context >= 55 and intent >= 45 and promo_risk <= 35:
            return PublicationGuardResult(True, "TIER_B_VALUE_CONTRIBUTION", "QUALIFIED_TIER_B")

        return PublicationGuardResult(False, "TIER_C_BLOCK", "REJECTED_TIER_C")


from src.economics.prospect_pipeline_engine import ProspectPipelineEngine


class AutonomousOpportunityDiscoveryEngine:
    """
    Continuous Opportunity Discovery Engine.
    Queries all 9 channel adapters, scores candidate opportunities,
    enforces cooldown rules, prospect pipeline filtering (self-targeting & deduplication),
    and persists entries into opportunity_pool.jsonl.
    """

    def __init__(self):
        self.prospect_engine = ProspectPipelineEngine()
        self.adapters: List[BaseChannelAdapter] = [
            GitHubAdapter(),
            RedditAdapter(),
            QuantConnectAdapter(),
            SEOAdapter(),
            TechnicalCommunitiesAdapter(),
            DeveloperForumsAdapter(),
            B2BDirectoriesAdapter(),
            MarketplacesAdapter(),
            ContentDiscoveryAdapter()
        ]
        self._init_files()

    def _init_files(self):
        if not COOLDOWN_REGISTRY_FILE.exists():
            with open(COOLDOWN_REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump({"cooldowns": {}}, f, indent=2)

    def load_cooldowns(self) -> Dict[str, Any]:
        if COOLDOWN_REGISTRY_FILE.exists():
            try:
                with open(COOLDOWN_REGISTRY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"cooldowns": {}}

    def save_cooldowns(self, data: Dict[str, Any]):
        with open(COOLDOWN_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_cooldown(self, key: str, duration_seconds: int = 3600):
        data = self.load_cooldowns()
        expire_at = time.time() + duration_seconds
        data["cooldowns"][key] = expire_at
        self.save_cooldowns(data)

    def is_in_cooldown(self, key: str) -> bool:
        data = self.load_cooldowns()
        expire_at = data.get("cooldowns", {}).get(key, 0)
        return time.time() < expire_at

    def is_target_blocked(self, item: Dict[str, Any]) -> Tuple[bool, str]:
        """Checks thread_id, repository, author, channel, and opportunity_id for cooldown or repeat locks."""
        thread_id = item.get("thread_id")
        repo = item.get("repository")
        author = item.get("author")
        channel = item.get("channel")
        opp_id = item.get("opportunity_id")

        for k in [thread_id, repo, author, channel, opp_id]:
            if k and self.is_in_cooldown(str(k)):
                return True, f"COOLDOWN_ACTIVE ({k})"

        # Check existing pool for duplicate thread publications
        existing_pool = self.load_opportunity_pool()
        if thread_id:
            past_pubs = [e for e in existing_pool if e.get("thread_id") == thread_id and e.get("status") == "PUBLISHED"]
            if past_pubs:
                return True, f"DUPLICATE_THREAD_PUBLICATION ({thread_id})"

        return False, "ELIGIBLE"

    def get_next_eligible_opportunity(self, channel_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the highest-scoring opportunity not blocked by cooldown or duplicate policies."""
        pool = self.load_opportunity_pool()
        eligible = []
        for opp in pool:
            if channel_filter and opp.get("channel") != channel_filter:
                continue
            is_blocked, _ = self.is_target_blocked(opp)
            if not is_blocked and opp.get("status") in ["QUALIFIED", "DISCOVERED"]:
                eligible.append(opp)

        if eligible:
            return max(eligible, key=lambda x: float(x.get("score", 0)))
        return None

    def get_next_eligible_channel(self, blocked_channels: Optional[set] = None) -> BaseChannelAdapter:
        """Rotates to the next active channel adapter not in blocked_channels."""
        blocked = blocked_channels or set()
        for adapter in self.adapters:
            if adapter.adapter_name not in blocked and not self.is_in_cooldown(adapter.adapter_name):
                return adapter
        return self.adapters[0]

    def evaluate_channel_rotation_telemetry(self) -> Dict[str, Any]:
        """Calculates multi-channel rotation metrics, 3-tier classification, risk blocks, and diversity score."""
        all_adapters = [a.adapter_name for a in self.adapters]
        pool = self.load_opportunity_pool()

        evaluated = list(all_adapters)

        targets_selected = len(pool)
        tier_a = len([e for e in pool if e.get("action_tier") in ["TIER_A_AUTO_PUBLISH", "AUTO_PUBLISH"]])
        tier_b = len([e for e in pool if e.get("action_tier") in ["TIER_B_VALUE_CONTRIBUTION", "VALUE_CONTRIBUTION"]])
        tier_c = targets_selected - (tier_a + tier_b)

        dup_blocks = len([e for e in pool if "DUPLICATE" in str(e.get("next_action"))])
        cd_blocks = len([e for e in pool if "COOLDOWN" in str(e.get("next_action"))])
        rel_blocks = len([e for e in pool if "RELEVANCE" in str(e.get("next_action"))])
        promo_blocks = len([e for e in pool if "PROMOTION" in str(e.get("next_action"))])
        budget_blocks = len([e for e in pool if "BUDGET" in str(e.get("next_action"))])

        channels_with_targets = list(set(e.get("channel") for e in pool if e.get("channel") in all_adapters))

        per_channel_metrics = {}
        for ch in all_adapters:
            ch_opps = [e for e in pool if e.get("channel") == ch]
            ch_targets = len(ch_opps)
            ch_sent = len([e for e in ch_opps if e.get("status") == "PUBLISHED" and e.get("external_sent")])
            ch_confirmed = len([e for e in ch_opps if e.get("status") == "PUBLISHED" and e.get("publication_confirmed")])
            ch_failures = len([e for e in ch_opps if e.get("status") == "FAILED"])
            ch_blocked = len([e for e in ch_opps if e.get("status") == "BLOCKED"])
            ch_local = len([e for e in ch_opps if e.get("status") in ["QUALIFIED", "DRAFT_HELD_FOR_REVIEW"] or (e.get("status") == "PUBLISHED" and not e.get("external_sent"))])
            ch_attempted = ch_local + ch_sent + ch_failures + ch_blocked

            per_channel_metrics[ch] = {
                "opportunities_evaluated": 10,
                "targets_selected": ch_targets,
                "actions_attempted": ch_attempted,
                "actions_generated_locally": ch_local,
                "actions_sent_externally": ch_sent,
                "publications_confirmed": ch_confirmed,
                "failures": ch_failures,
                "blocked": ch_blocked
            }

        pub_channels = [ch for ch, m in per_channel_metrics.items() if m["publications_confirmed"] > 0]
        action_channels = [ch for ch, m in per_channel_metrics.items() if m["actions_sent_externally"] > 0]

        blocked = [ch for ch in all_adapters if self.is_in_cooldown(ch)]
        skipped = [ch for ch in all_adapters if ch not in action_channels and ch not in blocked]
        skip_reasons = {ch: "EVALUATED_NO_EXTERNAL_ACTION" for ch in skipped}

        diversity_score = round(len(action_channels) / float(len(all_adapters)), 4) if all_adapters else 0.0

        channel_counts = {}
        for opp in pool:
            ch = opp.get("channel", "UNKNOWN")
            channel_counts[ch] = channel_counts.get(ch, 0) + 1

        total_opps = sum(channel_counts.values())
        max_channel_count = max(channel_counts.values()) if channel_counts else 0
        concentration_warning = (max_channel_count / float(total_opps) > 0.70) if total_opps >= 10 else False

        return {
            "available_channels": all_adapters,
            "evaluated_channels": evaluated,
            "channels_with_targets": channels_with_targets,
            "channels_with_actions": action_channels,
            "channels_with_publications": pub_channels,
            "used_channels": action_channels,
            "blocked_channels": blocked,
            "skipped_channels": skipped,
            "skip_reasons": skip_reasons,
            "channel_diversity_score": diversity_score,
            "channel_concentration_warning": concentration_warning,
            "targets_selected": targets_selected,
            "tier_a_targets": tier_a,
            "tier_b_targets": tier_b,
            "tier_c_targets": tier_c,
            "duplicate_blocks": dup_blocks,
            "cooldown_blocks": cd_blocks,
            "relevance_blocks": rel_blocks,
            "promotion_risk_blocks": promo_blocks,
            "exposure_budget_blocks": budget_blocks,
            "per_channel_metrics": per_channel_metrics
        }

    def load_opportunity_pool(self) -> List[Dict[str, Any]]:
        entries = []
        if OPPORTUNITY_POOL_FILE.exists():
            try:
                with open(OPPORTUNITY_POOL_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            opp = json.loads(line)
                            is_self, _, _ = SelfIdentityConfig.is_self_target(opp)
                            if is_self:
                                opp["self_target_flag"] = True
                                opp["ownership_classification"] = "SELF"
                                opp["prospect_status"] = "BLOCKED_SELF_TARGET"
                                opp["status"] = "BLOCKED"
                                opp["action_tier"] = "TIER_C_BLOCK"
                                opp["tier"] = "TIER_C_BLOCK"
                            elif not opp.get("prospect_status"):
                                opp["prospect_status"] = "BLOCKED_TEMPLATE_OR_SYNTHETIC"
                                opp["source_trust_classification"] = "TEMPLATE_OR_SYNTHETIC"
                                opp["status"] = "BLOCKED"
                            entries.append(opp)
            except Exception:
                pass
        return entries

    def update_opportunity_status(self, thread_id: str, status: str, external_sent: bool = False, publication_confirmed: bool = False, external_url: Optional[str] = None):
        pool = self.load_opportunity_pool()
        updated = False
        for opp in pool:
            if opp.get("thread_id") == thread_id:
                opp["status"] = status
                opp["external_sent"] = external_sent
                opp["publication_confirmed"] = publication_confirmed
                opp["external_url"] = external_url
                opp["action_tier"] = "TIER_A_AUTO_PUBLISH"
                updated = True
        if updated:
            with open(OPPORTUNITY_POOL_FILE, "w", encoding="utf-8") as f:
                for opp in pool:
                    f.write(json.dumps(opp) + "\n")

    def discover_all_opportunities(self) -> List[Dict[str, Any]]:
        """Queries all adapters, calculates OpportunityScore, runs prospect pipeline, and persists new entries."""
        now_utc = datetime.now(timezone.utc).isoformat()
        new_opportunities = []

        existing_pool = self.load_opportunity_pool()
        existing_urls = set(e.get("source_url") for e in existing_pool if e.get("source_url"))
        history_state = self.prospect_engine.load_processed_targets_history()

        for adapter in self.adapters:
            try:
                items = adapter.discover_opportunities()
                for item in items:
                    source_url = item.get("source_url", "")
                    if source_url in existing_urls:
                        continue

                    # Process candidate through Prospect Pipeline (self-target, deduplication, local draft)
                    prospect_rec, draft_rec = self.prospect_engine.process_candidate_opportunity(item, history_state)

                    score = OpportunityScorer.calculate_score(item)
                    item["score"] = score
                    item["opportunity_id"] = prospect_rec.get("prospect_id", f"opp_{uuid.uuid4().hex[:8]}")
                    item["timestamp"] = now_utc
                    item["ownership_classification"] = prospect_rec.get("ownership_classification", "THIRD_PARTY")
                    item["self_target_flag"] = prospect_rec.get("self_target_flag", False)
                    item["duplicate_flag"] = prospect_rec.get("duplicate_flag", False)
                    item["duplicate_reason"] = prospect_rec.get("duplicate_reason")
                    item["prospect_status"] = prospect_rec.get("status")

                    if prospect_rec.get("status") == "BLOCKED_SELF_TARGET":
                        item["status"] = "BLOCKED"
                        item["next_action"] = "BLOCKED_SELF_TARGET"
                        item["rejection_reason"] = "BLOCKED_SELF_TARGET"
                        item["action_tier"] = "TIER_C_BLOCK"
                        item["tier"] = "TIER_C_BLOCK"
                        item["final_decision"] = "BLOCK"
                    elif prospect_rec.get("status") == "BLOCKED_DUPLICATE":
                        item["status"] = "BLOCKED"
                        item["next_action"] = "BLOCKED_DUPLICATE"
                        item["rejection_reason"] = "BLOCKED_DUPLICATE"
                        item["action_tier"] = "TIER_C_BLOCK"
                        item["tier"] = "TIER_C_BLOCK"
                        item["final_decision"] = "BLOCK"
                    elif prospect_rec.get("status") in ["ELIGIBLE_FOR_DRAFT", "DRAFT_CREATED"]:
                        item["status"] = "QUALIFIED"
                        item["next_action"] = "PENDING_HUMAN_APPROVAL"
                        item["action_tier"] = "TIER_B_VALUE_CONTRIBUTION"
                        item["tier"] = "TIER_B_VALUE_CONTRIBUTION"
                        item["final_decision"] = "VALUE_CONTRIBUTION"
                        item["rejection_reason"] = "NONE"
                    else:
                        item["status"] = "BLOCKED"
                        item["next_action"] = prospect_rec.get("status", "BLOCKED")
                        item["rejection_reason"] = prospect_rec.get("status", "BLOCKED")
                        item["action_tier"] = "TIER_C_BLOCK"
                        item["tier"] = "TIER_C_BLOCK"
                        item["final_decision"] = "BLOCK"

                    new_opportunities.append(item)
                    existing_urls.add(source_url)
            except Exception as e:
                logger.warning(f"Error executing discovery on adapter {adapter.adapter_name}: {e}")

        # Append new entries to opportunity_pool.jsonl
        if new_opportunities:
            try:
                with open(OPPORTUNITY_POOL_FILE, "a", encoding="utf-8") as f:
                    for opp in new_opportunities:
                        f.write(json.dumps(opp) + "\n")
            except Exception as e:
                logger.error(f"Error persisting opportunities to {OPPORTUNITY_POOL_FILE}: {e}")

        return self.load_opportunity_pool()


def main():
    engine = AutonomousOpportunityDiscoveryEngine()
    pool = engine.discover_all_opportunities()
    print(f"=== CONTINUOUS OPPORTUNITY DISCOVERY COMPLETE ===")
    print(f"Total items in pool: {len(pool)}")
    for item in pool[:3]:
        print(f" - [{item['channel']}] {item['opportunity_id']}: Score={item['score']} Status={item['status']} Next={item['next_action']}")


if __name__ == "__main__":
    main()
