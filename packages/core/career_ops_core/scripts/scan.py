"""scan — zero-token portal scanner with pluggable provider layer.

Port of scan.mjs. Providers are discovered via importlib from
career_ops_core.providers (any module not starting with '_' that
exports a Provider instance).
"""
from __future__ import annotations

import asyncio
import importlib
import pkgutil
import re
from datetime import date as _date
from pathlib import Path
from typing import Optional

import yaml

from career_ops_core.config import ProjectConfig
from career_ops_core.data.scan_history import ScanHistoryRow, append_scan_history
from career_ops_core.providers._http import make_client
from career_ops_core.providers._types import JobListing, PortalEntry, Provider

CONCURRENCY = 10


def _load_providers() -> dict[str, Provider]:
    """Discover all provider modules in career_ops_core.providers."""
    import career_ops_core.providers as pkg
    providers: dict[str, Provider] = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"career_ops_core.providers.{info.name}")
        # Convention: module-level variable with same name as module
        instance = getattr(mod, info.name, None)
        if isinstance(instance, Provider):
            providers[instance.id] = instance
    return providers


def _build_title_filter(title_filter: dict):
    positive = [k.lower() for k in (title_filter.get("positive") or [])]
    negative = [k.lower() for k in (title_filter.get("negative") or [])]

    def _filter(title: str) -> bool:
        lower = title.lower()
        has_pos = not positive or any(k in lower for k in positive)
        has_neg = any(k in lower for k in negative)
        return has_pos and not has_neg

    return _filter


def _build_location_filter(location_filter: Optional[dict]):
    if not location_filter:
        return lambda _: True
    allow = [k.lower() for k in (location_filter.get("allow") or [])]
    block = [k.lower() for k in (location_filter.get("block") or [])]

    def _filter(location: str) -> bool:
        if not location:
            return True
        lower = location.lower()
        if block and any(k in lower for k in block):
            return False
        if not allow:
            return True
        return any(k in lower for k in allow)

    return _filter


def _load_seen_urls(cfg: ProjectConfig) -> set[str]:
    seen: set[str] = set()
    # scan-history.tsv
    if cfg.scan_history_tsv.exists():
        for line in cfg.scan_history_tsv.read_text(encoding="utf-8").splitlines()[1:]:
            url = line.split("\t")[0]
            if url:
                seen.add(url)
    # pipeline.md
    if cfg.pipeline_md.exists():
        for m in re.finditer(r"- \[[ x]\] (https?://\S+)", cfg.pipeline_md.read_text(encoding="utf-8")):
            seen.add(m.group(1))
    # applications.md
    if cfg.applications_md.exists():
        for m in re.finditer(r"https?://[^\s|)]+", cfg.applications_md.read_text(encoding="utf-8")):
            seen.add(m.group(0))
    return seen


def _load_seen_company_roles(cfg: ProjectConfig) -> set[str]:
    seen: set[str] = set()
    if not cfg.applications_md.exists():
        return seen
    for m in re.finditer(
        r"\|[^|]+\|[^|]+\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|",
        cfg.applications_md.read_text(encoding="utf-8"),
    ):
        company = m.group(1).strip().lower()
        role = m.group(2).strip().lower()
        if company and role and company != "company":
            seen.add(f"{company}::{role}")
    return seen


def _append_pipeline(cfg: ProjectConfig, offers: list[JobListing]) -> None:
    if not offers:
        return
    pipeline = cfg.pipeline_md
    if not pipeline.exists():
        pipeline.write_text("# Pipeline — pending URLs\n\n## Pendientes\n\n", encoding="utf-8")
    text = pipeline.read_text(encoding="utf-8")
    marker = "## Pendientes"
    idx = text.find(marker)
    block = "\n" + "\n".join(f"- [ ] {o.url} | {o.company} | {o.title}" for o in offers) + "\n"
    if idx == -1:
        text = text.rstrip() + f"\n\n{marker}\n{block}\n"
    else:
        after = idx + len(marker)
        next_sec = text.find("\n## ", after)
        ins = next_sec if next_sec != -1 else len(text)
        text = text[:ins] + block + text[ins:]
    pipeline.write_text(text, encoding="utf-8")


async def run_scan(
    cfg: ProjectConfig,
    dry_run: bool = False,
    company_filter: Optional[str] = None,
) -> None:
    cfg.ensure_dirs()

    portals_path = cfg.portals_yml
    if not portals_path.exists():
        print("Error: portals.yml not found. Run onboarding first.")
        return

    providers = _load_providers()
    if not providers:
        print("Error: no providers loaded from career_ops_core.providers")
        return

    config = yaml.safe_load(portals_path.read_text(encoding="utf-8")) or {}
    companies_raw = config.get("tracked_companies") or []
    title_filter = _build_title_filter(config.get("title_filter") or {})
    location_filter = _build_location_filter(config.get("location_filter"))

    targets: list[tuple[PortalEntry, Provider]] = []
    skipped = 0
    for raw in companies_raw:
        if raw.get("enabled") is False:
            continue
        name = raw.get("name", "")
        if not name:
            continue
        if company_filter and company_filter.lower() not in name.lower():
            continue
        entry = PortalEntry(
            name=name,
            careers_url=raw.get("careers_url", ""),
            api=raw.get("api", ""),
            title_filter=raw.get("title_filter", {}),
            location_filter=raw.get("location_filter"),
        )
        # Resolve provider: explicit 'provider' field wins, else auto-detect
        explicit = raw.get("provider")
        if explicit:
            p = providers.get(explicit)
            if p:
                targets.append((entry, p))
            else:
                print(f"⚠️  {name}: unknown provider '{explicit}'")
        else:
            matched = next((p for p in providers.values() if p.detect(entry)), None)
            if matched:
                targets.append((entry, matched))
            else:
                skipped += 1

    print(f"Scanning {len(targets)} companies via providers ({skipped} skipped — no provider matched)")
    if dry_run:
        print("(dry run — no files will be written)\n")

    seen_urls = _load_seen_urls(cfg)
    seen_roles = _load_seen_company_roles(cfg)
    today = str(_date.today())

    total_found = total_title = total_loc = total_dupes = 0
    new_offers: list[JobListing] = []
    errors: list[tuple[str, str]] = []

    sem = asyncio.Semaphore(CONCURRENCY)

    async def fetch_company(entry: PortalEntry, provider: Provider) -> None:
        nonlocal total_found, total_title, total_loc, total_dupes
        async with sem:
            try:
                async with make_client() as client:
                    jobs = await provider.fetch(entry, client)
            except Exception as e:
                errors.append((entry.name, str(e)))
                return

        total_found += len(jobs)
        for job in jobs:
            if not title_filter(job.title):
                total_title += 1
                continue
            if not location_filter(job.location):
                total_loc += 1
                continue
            if job.url in seen_urls:
                total_dupes += 1
                continue
            key = f"{job.company.lower()}::{job.title.lower()}"
            if key in seen_roles:
                total_dupes += 1
                continue
            seen_urls.add(job.url)
            seen_roles.add(key)
            new_offers.append(job)

    await asyncio.gather(*(fetch_company(e, p) for e, p in targets))

    if not dry_run and new_offers:
        _append_pipeline(cfg, new_offers)
        history_rows = [
            ScanHistoryRow(
                url=o.url,
                first_seen=today,
                portal=f"{next(p.id for e2, p in targets if e2.company == o.company)}-api",
                title=o.title,
                company=o.company,
                status="added",
                location=o.location,
            )
            for o in new_offers
        ]
        append_scan_history(cfg.scan_history_tsv, history_rows)

    print(f"\n{'━' * 45}")
    print(f"Portal Scan — {today}")
    print(f"{'━' * 45}")
    print(f"Companies scanned:     {len(targets)}")
    print(f"Total jobs found:      {total_found}")
    print(f"Filtered by title:     {total_title} removed")
    print(f"Filtered by location:  {total_loc} removed")
    print(f"Duplicates:            {total_dupes} skipped")
    print(f"New offers added:      {len(new_offers)}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for name, msg in errors:
            print(f"  ✗ {name}: {msg}")

    if new_offers:
        print("\nNew offers:")
        for o in new_offers:
            print(f"  + {o.company} | {o.title} | {o.location or 'N/A'}")
        if dry_run:
            print("\n(dry run — run without --dry-run to save results)")
        else:
            print(f"\nResults saved to pipeline.md and scan-history.tsv")

    print("\n→ Run career-ops pipeline to evaluate new offers.")
