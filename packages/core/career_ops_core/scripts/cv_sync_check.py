"""cv_sync_check — validate consistency between cv.md and config/profile.yml.

Port of cv-sync-check.mjs.
"""
from __future__ import annotations

import re

import yaml

from career_ops_core.config import ProjectConfig


def cv_sync_check(cfg: ProjectConfig) -> None:
    cv = cfg.cv_md
    profile = cfg.profile_yml

    issues: list[str] = []
    warnings: list[str] = []

    if not cv.exists():
        print("⚠️  cv.md not found — skipping sync check")
        return
    if not profile.exists():
        print("⚠️  config/profile.yml not found — skipping sync check")
        return

    cv_text = cv.read_text(encoding="utf-8")
    profile_data = yaml.safe_load(profile.read_text(encoding="utf-8")) or {}

    # Check name appears in cv.md
    name = profile_data.get("name", "")
    if name and name not in cv_text:
        issues.append(f"Name '{name}' from profile.yml not found in cv.md")

    # Check email appears in cv.md
    email = profile_data.get("email", "")
    if email and email not in cv_text:
        warnings.append(f"Email '{email}' from profile.yml not found in cv.md")

    # Check target roles appear somewhere in cv.md
    target_roles = profile_data.get("target_roles", [])
    for role in (target_roles or []):
        role_words = [w.lower() for w in role.split() if len(w) > 3]
        if role_words and not any(w in cv_text.lower() for w in role_words):
            warnings.append(f"Target role '{role}' has no matching keywords in cv.md")

    if issues:
        print("❌ CV sync issues:")
        for i in issues:
            print(f"  {i}")
    if warnings:
        print("⚠️  CV sync warnings:")
        for w in warnings:
            print(f"  {w}")
    if not issues and not warnings:
        print("✅ cv.md and config/profile.yml are in sync")
