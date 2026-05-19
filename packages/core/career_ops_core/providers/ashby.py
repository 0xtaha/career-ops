"""Ashby provider — hits the public posting-api endpoint."""
from __future__ import annotations

import re
from typing import Optional

import httpx

from career_ops_core.providers._types import JobListing, PortalEntry, Provider


def _resolve_api_url(entry: PortalEntry) -> Optional[str]:
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", entry.careers_url)
    if not m:
        return None
    return f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}?includeCompensation=true"


class AshbyProvider(Provider):
    @property
    def id(self) -> str:
        return "ashby"

    def detect(self, entry: PortalEntry) -> Optional[dict]:
        url = _resolve_api_url(entry)
        return {"url": url} if url else None

    async def fetch(self, entry: PortalEntry, client: httpx.AsyncClient) -> list[JobListing]:
        api_url = _resolve_api_url(entry)
        if not api_url:
            raise ValueError(f"ashby: cannot derive API URL for {entry.name}")
        resp = await client.get(api_url)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return [
            JobListing(
                title=j.get("title", ""),
                url=j.get("jobUrl", ""),
                company=entry.name,
                location=j.get("location", ""),
            )
            for j in jobs
        ]


ashby = AshbyProvider()
