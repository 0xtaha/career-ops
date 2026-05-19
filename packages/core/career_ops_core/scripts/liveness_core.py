"""liveness_core — classify job posting liveness from page signals.

Pure function, no I/O — port of liveness-core.mjs.
Expired signals win over generic apply text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

_HARD_EXPIRED = [
    re.compile(r"job (is )?no longer available", re.I),
    re.compile(r"job.*no longer open", re.I),
    re.compile(r"position has been filled", re.I),
    re.compile(r"this job has expired", re.I),
    re.compile(r"job posting has expired", re.I),
    re.compile(r"no longer accepting applications", re.I),
    re.compile(r"this (position|role|job) (is )?no longer", re.I),
    re.compile(r"this job (listing )?is closed", re.I),
    re.compile(r"job (listing )?not found", re.I),
    re.compile(r"the page you are looking for doesn.t exist", re.I),
    re.compile(r"applications?\s+(?:(?:have|are|is)\s+)?closed", re.I),
    re.compile(r"closed on \d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.I),
    re.compile(r"closed on (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}", re.I),
    re.compile(r"diese stelle (ist )?(nicht mehr|bereits) besetzt", re.I),
    re.compile(r"offre (expirée|n'est plus disponible)", re.I),
]

_LISTING_PAGE = [
    re.compile(r"\d+\s+jobs?\s+found", re.I),
    re.compile(r"search for jobs page is loaded", re.I),
]

_EXPIRED_URL = [
    re.compile(r"[?&]error=true", re.I),
]

_APPLY = [
    re.compile(r"\bapply\b", re.I),
    re.compile(r"\bsolicitar\b", re.I),
    re.compile(r"\bbewerben\b", re.I),
    re.compile(r"\bpostuler\b", re.I),
    re.compile(r"submit application", re.I),
    re.compile(r"easy apply", re.I),
    re.compile(r"start application", re.I),
    re.compile(r"ich bewerbe mich", re.I),
]

MIN_CONTENT_CHARS = 300


@dataclass
class LivenessResult:
    result: str   # 'active' | 'expired' | 'uncertain'
    reason: str


def classify_liveness(
    status: int = 0,
    final_url: str = "",
    body_text: str = "",
    apply_controls: Sequence[str] = (),
) -> LivenessResult:
    """Classify whether a job posting is still live.

    Expired signals take precedence over apply controls.
    """
    if status in (404, 410):
        return LivenessResult("expired", f"HTTP {status}")

    for pat in _EXPIRED_URL:
        if pat.search(final_url):
            return LivenessResult("expired", f"redirect to {final_url}")

    for pat in _HARD_EXPIRED:
        if pat.search(body_text):
            return LivenessResult("expired", f"pattern matched: {pat.pattern}")

    for control in apply_controls:
        if any(p.search(control) for p in _APPLY):
            return LivenessResult("active", "visible apply control detected")

    for pat in _LISTING_PAGE:
        if pat.search(body_text):
            return LivenessResult("expired", f"pattern matched: {pat.pattern}")

    if len(body_text.strip()) < MIN_CONTENT_CHARS:
        return LivenessResult("expired", "insufficient content — likely nav/footer only")

    return LivenessResult("uncertain", "content present but no visible apply control found")
