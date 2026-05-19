"""dedup_tracker — remove duplicate entries from applications.md.

Port of dedup-tracker.mjs.
Keeps entry with highest score; if discarded entry had more advanced status,
promotes that status to the keeper.
"""
from __future__ import annotations

import re
import shutil
from typing import Optional

from career_ops_core.config import ProjectConfig
from career_ops_core.data.applications import parse_applications, ApplicationRow
from career_ops_core.data.normalize import normalize_company
from career_ops_core.data.states import STATUS_RANK

_ROLE_STOPWORDS = frozenset([
    "senior", "junior", "lead", "staff", "principal", "head", "chief",
    "manager", "director", "associate", "intern", "contractor",
    "remote", "hybrid", "onsite", "engineer", "engineering",
])

_LOCATION_STOPWORDS = frozenset([
    "tokyo", "japan", "london", "berlin", "paris", "singapore",
    "york", "francisco", "angeles", "seattle", "austin", "boston",
    "chicago", "denver", "toronto", "amsterdam", "dublin", "sydney",
    "remote", "global", "emea", "apac", "latam",
])


def _role_tokens(role: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9 /]", "", role.lower()).strip()
    return [
        w for w in normalized.split()
        if len(w) > 2 and w not in _ROLE_STOPWORDS and w not in _LOCATION_STOPWORDS
    ]


def _role_match(a: str, b: str) -> bool:
    words_a = _role_tokens(a)
    words_b = _role_tokens(b)
    if not words_a or not words_b:
        return False
    set_b = set(words_b)
    overlap = [w for w in words_a if w in set_b]
    smaller = min(len(words_a), len(words_b))
    return len(overlap) >= 2 and len(overlap) / smaller >= 0.6


def dedup_tracker(cfg: ProjectConfig, dry_run: bool = False) -> None:
    apps_file = cfg.applications_md
    if not apps_file.exists():
        print("No applications.md found. Nothing to dedup.")
        return

    entries = parse_applications(apps_file)
    print(f"📊 {len(entries)} entries loaded")

    # Map raw_line → line index for in-place edits
    content = apps_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    line_index: dict[str, int] = {}
    for i, line in enumerate(lines):
        line_index[line] = i

    # Group by company
    by_company: dict[str, list[ApplicationRow]] = {}
    for entry in entries:
        key = normalize_company(entry.company)
        by_company.setdefault(key, []).append(entry)

    removed = 0
    lines_to_remove: set[int] = set()

    for _company, group in by_company.items():
        if len(group) < 2:
            continue

        processed: set[int] = set()
        for i, entry in enumerate(group):
            if i in processed:
                continue
            cluster = [entry]
            processed.add(i)
            for j in range(i + 1, len(group)):
                if j in processed:
                    continue
                if _role_match(entry.role, group[j].role):
                    cluster.append(group[j])
                    processed.add(j)

            if len(cluster) < 2:
                continue

            # Keep highest-scored entry
            cluster.sort(key=lambda r: r.score or 0.0, reverse=True)
            keeper = cluster[0]

            # Find the most advanced status across all cluster members
            best_rank = STATUS_RANK.get(keeper.status.lower(), 0)
            best_status = keeper.status
            for dup in cluster[1:]:
                rank = STATUS_RANK.get(dup.status.lower(), 0)
                if rank > best_rank:
                    best_rank = rank
                    best_status = dup.status

            # Promote keeper's status if needed
            if best_status != keeper.status:
                idx = line_index.get(keeper.raw_line)
                if idx is not None:
                    parts = lines[idx].split("|")
                    parts[6] = f" {best_status} "
                    lines[idx] = "|".join(parts)
                    print(f'  📝 #{keeper.num}: status promoted to "{best_status}"')

            # Mark duplicates for removal
            for dup in cluster[1:]:
                idx = line_index.get(dup.raw_line)
                if idx is not None:
                    lines_to_remove.add(idx)
                    removed += 1
                    print(f"🗑️  Remove #{dup.num} ({dup.company} — {dup.role}, {dup.score_raw}) → kept #{keeper.num} ({keeper.score_raw})")

    # Remove lines in reverse order
    for idx in sorted(lines_to_remove, reverse=True):
        lines.pop(idx)

    print(f"\n📊 {removed} duplicates removed")

    if not dry_run and removed > 0:
        shutil.copy2(apps_file, str(apps_file) + ".bak")
        apps_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("✅ Written to applications.md (backup: applications.md.bak)")
    elif dry_run:
        print("(dry-run — no changes written)")
    else:
        print("✅ No duplicates found")
