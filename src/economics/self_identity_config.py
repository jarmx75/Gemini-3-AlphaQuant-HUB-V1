"""
Centralized Self-Identity Configuration & Exclusion Engine (Sprint #36.6 / Etapa 2)

Features:
- Configurable rules to identify self-owned repositories, authors, domains, and thread targets.
- Prevents self-targeting by detecting owner artifacts without secret dependencies.
- Extensible interface allowing addition of new self-identities.
"""

import re
from typing import Dict, Any, Tuple, Optional, Set


class SelfIdentityConfig:
    """
    Centralized self-identity rules and matching engine for prospect qualification.
    """

    OWNER_USERNAMES: Set[str] = {
        "jarmx75",
        "alpha-quant1",
        "alpha_quant_hub"
    }

    OWNER_REPOSITORIES: Set[str] = {
        "jarmx75/gemini-3-alphaquant-hub-v1",
        "jarmx75/trading-autonomous-system",
        "alpha-quant1/automaton-quant-audit-api"
    }

    OWNER_DOMAINS: Set[str] = {
        "jarmx75.github.io",
        "jarmx75.github.io/gemini-3-alphaquant-hub-v1",
        "automaton-quant-audit-api.vercel.app"
    }

    OWNER_KEYWORDS: Set[str] = {
        "gemini-3-alphaquant-hub-v1",
        "jarmx75"
    }

    @classmethod
    def is_self_target(cls, candidate: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """
        Evaluates candidate opportunity for self-targeting indicators.
        Returns: (is_self: bool, block_reason: Optional[str], ownership_classification: str)
        """
        if not candidate:
            return False, None, "UNKNOWN"

        source_url = str(candidate.get("source_url", "")).lower()
        repository = str(candidate.get("repository", "")).lower()
        author = str(candidate.get("author", "")).lower()
        target_id = str(candidate.get("target_identifier", candidate.get("thread_id", ""))).lower()
        comments_url = str(candidate.get("comments_url", "")).lower()

        # 1. Check Repository Match
        if repository and repository in cls.OWNER_REPOSITORIES:
            return True, f"Matches self-owned repository: '{repository}'", "SELF"

        # 2. Check Author Match
        if author and author in cls.OWNER_USERNAMES:
            return True, f"Matches self-owned author: '{author}'", "SELF"

        # 3. Check Source URL Domains / Repositories
        for repo in cls.OWNER_REPOSITORIES:
            if repo in source_url or repo in comments_url:
                return True, f"Source URL matches self-owned repository: '{repo}'", "SELF"

        for domain in cls.OWNER_DOMAINS:
            if domain in source_url or domain in comments_url:
                return True, f"Source URL matches self-owned domain: '{domain}'", "SELF"

        for kw in cls.OWNER_KEYWORDS:
            if kw in source_url or kw in repository or kw in target_id:
                return True, f"Target matches self-owned keyword: '{kw}'", "SELF"

        return False, None, "THIRD_PARTY"
