"""Role normalisation and fuzzy matching.

Port of the normalisation logic in merge-tracker.mjs.
Critical constants are module-level frozensets so they can be imported
anywhere without reconstruction overhead.

Issue #633 edge case: "Staff SWE API" vs "Staff SWE Kubernetes Platform"
must NOT match — they share only BASELINE_TOKENS.
"""
from __future__ import annotations

import re

# Tokens that appear in almost every role title and provide NO signal.
ROLE_STOPWORDS: frozenset[str] = frozenset(
    [
        # seniority / level
        "junior", "mid", "middle", "senior", "staff", "principal", "lead",
        "head", "chief", "associate", "intern", "entry", "level",
        # contract / work mode
        "remote", "hybrid", "onsite", "contract", "contractor", "freelance",
        "fulltime", "parttime", "permanent", "temporary", "intern", "internship",
        # generic job words
        "role", "position", "opportunity", "team", "based",
        # common locations
        "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "chennai",
        "london", "berlin", "paris", "madrid", "barcelona", "amsterdam", "dublin",
        "york", "francisco", "seattle", "boston", "austin", "chicago", "toronto",
        "tokyo", "singapore", "sydney", "melbourne", "lisbon", "warsaw",
        # regions / countries
        "europe", "emea", "apac", "latam", "americas", "india", "spain", "germany",
        "france", "italy", "canada", "brazil", "mexico", "japan",
        # short prepositions that leak through the length filter
        "with", "from", "into", "over", "this", "that",
    ]
)

# Short specialty acronyms that ARE discriminating despite being ≤3 chars.
# Deliberately narrow: specific team/tech names, NOT broad "ai"/"ml"/"llm"
# (those appear across many roles and would regress #329).
SHORT_SPECIALTY: frozenset[str] = frozenset(
    ["api", "sre", "sdk", "cli", "gpu", "cpu", "ios", "qa", "ux", "ui", "ar", "vr", "ocr", "crm", "erp"]
)

# Generic role-level descriptors. Overlap *only* in this set means the roles
# are at the same altitude, not the same role (Issue #633).
BASELINE_TOKENS: frozenset[str] = frozenset(
    [
        "software", "engineer", "developer", "manager", "architect",
        "analyst", "designer", "consultant", "specialist",
        "platform", "systems", "services",
        "backend", "frontend", "fullstack",
    ]
)


def normalize_company(name: str) -> str:
    """Collapse a company name to a lowercase alphanumeric key."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def role_tokens(s: str) -> list[str]:
    """Tokenise a role title, filtering stopwords and short non-specialty words."""
    words = re.sub(r"[^a-z0-9\s]", " ", s.lower()).split()
    return [
        w for w in words
        if (len(w) > 3 or w in SHORT_SPECIALTY) and w not in ROLE_STOPWORDS
    ]


def role_fuzzy_match(a: str, b: str) -> bool:
    """Return True when two role titles refer to the same role.

    Requires:
    - At least 2 tokens in common
    - At least 1 discriminating (non-baseline) token in the overlap
    - Jaccard-style ratio ≥ 0.6 on the smaller token set
    """
    words_a = role_tokens(a)
    words_b = role_tokens(b)
    if not words_a or not words_b:
        return False

    set_b = set(words_b)
    overlap = [w for w in words_a if w in set_b]
    if len(overlap) < 2:
        return False

    # Require at least one non-baseline token (guards against #633)
    discriminating = [w for w in overlap if w not in BASELINE_TOKENS]
    if not discriminating:
        return False

    min_len = min(len(words_a), len(words_b))
    return len(overlap) / min_len >= 0.6
