"""Shared HTTP utilities for providers.

Uses httpx.AsyncClient with a 10s timeout and User-Agent spoofing.
"""
from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 10.0
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; career-ops/1.9)"


def make_client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"user-agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
    )
