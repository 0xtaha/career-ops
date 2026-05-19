"""Greenhouse provider — hits the public boards-api JSON endpoint.

SSRF protection: careers_url hostname validated against ALLOWED_HOSTS allowlist.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from career_ops_core.providers._types import JobListing, PortalEntry, Provider

ALLOWED_GREENHOUSE_HOSTS = frozenset(
    [
        "boards-api.greenhouse.io",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
    ]
)


def _assert_greenhouse_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"greenhouse: URL must use HTTPS: {url}")
    if parsed.hostname not in ALLOWED_GREENHOUSE_HOSTS:
        raise ValueError(
            f"greenhouse: untrusted hostname \"{parsed.hostname}\" — must be one of: "
            + ", ".join(sorted(ALLOWED_GREENHOUSE_HOSTS))
        )
    return url


def _resolve_api_url(entry: PortalEntry) -> Optional[str]:
    if entry.api:
        _assert_greenhouse_url(entry.api)
        return entry.api
    m = re.search(r"job-boards(?:\.eu)?\.greenhouse\.io/([^/?#]+)", entry.careers_url)
    if m:
        return f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs"
    return None


class GreenhouseProvider(Provider):
    @property
    def id(self) -> str:
        return "greenhouse"

    def detect(self, entry: PortalEntry) -> Optional[dict]:
        url = _resolve_api_url(entry)
        return {"url": url} if url else None

    async def fetch(self, entry: PortalEntry, client: httpx.AsyncClient) -> list[JobListing]:
        api_url = _resolve_api_url(entry)
        if not api_url:
            raise ValueError(f"greenhouse: cannot derive API URL for {entry.name}")
        _assert_greenhouse_url(api_url)
        # follow_redirects=False equivalent: prevent SSRF via server-side redirects
        resp = await client.get(api_url, follow_redirects=False)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return [
            JobListing(
                title=j.get("title", ""),
                url=j.get("absolute_url", ""),
                company=entry.name,
                location=(j.get("location") or {}).get("name", ""),
            )
            for j in jobs
            if j.get("absolute_url")
        ]


greenhouse = GreenhouseProvider()
