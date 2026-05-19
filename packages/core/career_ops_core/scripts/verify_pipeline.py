"""verify_pipeline — pipeline health check.

Port of verify-pipeline.mjs.
Returns True if no errors, False otherwise.
"""
from __future__ import annotations

import re
from pathlib import Path

from career_ops_core.config import ProjectConfig
from career_ops_core.data.states import CANONICAL_STATUSES, ALIASES


def verify_pipeline(cfg: ProjectConfig) -> bool:
    apps_file = cfg.applications_md

    if not apps_file.exists():
        print("\n📊 No applications.md found. Normal for a fresh setup.\n")
        return True

    content = apps_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    entries = []
    for line in lines:
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 9:
            continue
        try:
            num = int(parts[1])
        except ValueError:
            continue
        entries.append({
            "num": num,
            "date": parts[2],
            "company": parts[3],
            "role": parts[4],
            "score": parts[5],
            "status": parts[6],
            "pdf": parts[7],
            "report": parts[8],
            "notes": parts[9] if len(parts) > 9 else "",
        })

    print(f"\n📊 Checking {len(entries)} entries in applications.md\n")

    errors = 0
    warnings = 0
    canonical_lower = {s.lower() for s in CANONICAL_STATUSES}

    def error(msg: str) -> None:
        nonlocal errors
        print(f"❌ {msg}")
        errors += 1

    def warn(msg: str) -> None:
        nonlocal warnings
        print(f"⚠️  {msg}")
        warnings += 1

    def ok(msg: str) -> None:
        print(f"✅ {msg}")

    # 1. Canonical statuses
    bad_statuses = 0
    for e in entries:
        clean = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", e["status"].replace("**", "").strip().lower())
        if clean not in canonical_lower and clean not in ALIASES:
            error(f'#{e["num"]}: Non-canonical status "{e["status"]}"')
            bad_statuses += 1
        if "**" in e["status"]:
            error(f'#{e["num"]}: Status contains markdown bold: "{e["status"]}"')
            bad_statuses += 1
        if re.search(r"\d{4}-\d{2}-\d{2}", e["status"]):
            error(f'#{e["num"]}: Status contains date: "{e["status"]}"')
            bad_statuses += 1
    if bad_statuses == 0:
        ok("All statuses are canonical")

    # 2. Duplicates
    company_role_map: dict[str, list] = {}
    dupes = 0
    for e in entries:
        key = re.sub(r"[^a-z0-9]", "", e["company"].lower()) + "::" + re.sub(r"[^a-z0-9 ]", "", e["role"].lower())
        company_role_map.setdefault(key, []).append(e)
    for group in company_role_map.values():
        if len(group) > 1:
            nums = ", ".join(f'#{g["num"]}' for g in group)
            warn(f"Possible duplicates: {nums} ({group[0]['company']} — {group[0]['role']})")
            dupes += 1
    if dupes == 0:
        ok("No exact duplicates found")

    # 3. Report links
    broken_reports = 0
    for e in entries:
        m = re.search(r"\]\(([^)]+)\)", e["report"])
        if not m:
            continue
        report_path = cfg.root / m.group(1)
        if not report_path.exists():
            error(f'#{e["num"]}: Report not found: {m.group(1)}')
            broken_reports += 1
    if broken_reports == 0:
        ok("All report links valid")

    # 4. Score format
    score_re = re.compile(r"^\d+\.?\d*\/5$")
    bad_scores = 0
    for e in entries:
        s = e["score"].replace("**", "").strip()
        if not score_re.match(s) and s not in ("N/A", "DUP"):
            error(f'#{e["num"]}: Invalid score format: "{e["score"]}"')
            bad_scores += 1
    if bad_scores == 0:
        ok("All scores valid")

    # 5. Row format
    bad_rows = 0
    for line in lines:
        if not line.startswith("|"):
            continue
        if "---" in line or "Empresa" in line or "Company" in line:
            continue
        if line.count("|") < 9:
            error(f"Row with <9 columns: {line[:80]}")
            bad_rows += 1
    if bad_rows == 0:
        ok("All rows properly formatted")

    # 6. Pending TSVs
    pending = list(cfg.tracker_additions_dir.glob("*.tsv")) if cfg.tracker_additions_dir.exists() else []
    if pending:
        warn(f"{len(pending)} pending TSVs in tracker-additions/ (not merged)")
    else:
        ok("No pending TSVs")

    # 7. Bold in scores
    bold_scores = 0
    for e in entries:
        if "**" in e["score"]:
            warn(f'#{e["num"]}: Score has markdown bold: "{e["score"]}"')
            bold_scores += 1
    if bold_scores == 0:
        ok("No bold in scores")

    print("\n" + "=" * 50)
    print(f"📊 Pipeline Health: {errors} errors, {warnings} warnings")
    if errors == 0 and warnings == 0:
        print("🟢 Pipeline is clean!")
    elif errors == 0:
        print("🟡 Pipeline OK with warnings")
    else:
        print("🔴 Pipeline has errors — fix before proceeding")

    return errors == 0
