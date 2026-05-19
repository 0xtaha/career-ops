"""normalize_statuses — clean non-canonical statuses in applications.md.

Port of normalize-statuses.mjs.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from career_ops_core.config import ProjectConfig
from career_ops_core.data.states import normalize_status


def normalize_statuses(cfg: ProjectConfig, dry_run: bool = False) -> None:
    apps_file = cfg.applications_md
    if not apps_file.exists():
        print("No applications.md found. Nothing to normalize.")
        return

    lines = apps_file.read_text(encoding="utf-8").splitlines()
    changes = 0
    unknowns: list[dict] = []

    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # Format: ['', '#', 'date', 'company', 'role', 'score', 'STATUS', 'pdf', 'report', 'notes', '']
        if len(parts) < 9:
            continue
        if parts[1] in ("#", "---", ""):
            continue
        try:
            num = int(parts[1])
        except ValueError:
            continue

        raw_status = parts[6]
        canonical = normalize_status(raw_status)

        if canonical is None:
            unknowns.append({"num": num, "rawStatus": raw_status, "line": i + 1})
            continue

        if canonical == raw_status:
            continue  # already canonical

        old_status = raw_status
        parts[6] = canonical

        # Move DUPLICADO info to notes if applicable
        lower = raw_status.replace("**", "").strip().lower()
        if lower.startswith(("duplicado", "dup", "repost")):
            existing_notes = parts[9] if len(parts) > 9 else ""
            if raw_status.strip() not in existing_notes:
                parts[9] = raw_status.strip() + (". " + existing_notes if existing_notes else "")

        # Strip bold from score field too
        if len(parts) > 5:
            parts[5] = parts[5].replace("**", "")

        # Reconstruct — skip first/last empty strings from split
        lines[i] = "| " + " | ".join(parts[1:-1]) + " |"
        changes += 1
        print(f'#{num}: "{old_status}" → "{canonical}"')

    if unknowns:
        print(f"\n⚠️  {len(unknowns)} unknown statuses:")
        for u in unknowns:
            print(f'  #{u["num"]} (line {u["line"]}): "{u["rawStatus"]}"')

    print(f"\n📊 {changes} statuses normalized")

    if not dry_run and changes > 0:
        shutil.copy2(apps_file, str(apps_file) + ".bak")
        apps_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("✅ Written to applications.md (backup: applications.md.bak)")
    elif dry_run:
        print("(dry-run — no changes written)")
    else:
        print("✅ No changes needed")
