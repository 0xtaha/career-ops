"""Lever provider — hits the public postings endpoint."""
from __future__ import annotations

import re
from typing import Optional

import httpx

from career_ops_core.providers._types import JobListing, PortalEntry, Provider


def _resolve_api_url(entry: PortalEntry) -> Optional[str]:
    m = re.search(r"jobs\.lever\.co/([^/?#]+)", entry.careers_url)
    if not m:
        return None
    return f"https://api.lever.co/v0/postings/{m.group(1)}"


class LeverProvider(Provider):
    @property
    def id(self) -> str:
        return "lever"

    def detect(self, entry: PortalEntry) -> Optional[dict]:
        url = _resolve_api_url(entry)
        return {"url": url} if url else None

    async def fetch(self, entry: PortalEntry, client: httpx.AsyncClient) -> list[JobListing]:
        api_url = _resolve_api_url(entry)
        if not api_url:
            raise ValueError(f"lever: cannot derive API URL for {entry.name}")
        resp = await client.get(api_url)
        resp.raise_for_status()
        jobs = resp.json()
        if not isinstance(jobs, list):
            return []
        return [
            JobListing(
                title=j.get("text", ""),
                url=j.get("hostedUrl", ""),
                company=entry.name,
                location=(j.get("categories") or {}).get("location", ""),
            )
            for j in jobs
        ]


lever = LeverProvider()
