"""merge_tracker — merge batch/tracker-additions/*.tsv into data/applications.md.

Port of merge-tracker.mjs.

Column-swap heuristic:
  TSV additions use: num | date | company | role | Status | Score | pdf | report | notes
  applications.md uses: # | Date | Company | Role | Score | Status | PDF | Report | Notes
  _detect_column_order() detects which column is score vs status.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

from career_ops_core.config import ProjectConfig
from career_ops_core.data.applications import ApplicationRow, parse_applications, _row_to_line
from career_ops_core.data.normalize import normalize_company, role_fuzzy_match
from career_ops_core.data.states import normalize_status


def _detect_column_order(col4: str, col5: str) -> tuple[str, str]:
    """Return (status_val, score_val) from the two ambiguous TSV columns.

    TSV additions have status before score; applications.md has score before
    status. This heuristic detects which is which so both formats are handled.
    """
    score_re = re.compile(r"^\d+\.?\d*\/5$|^N\/A$|^DUP$")
    status_re = re.compile(
        r"^(evaluated|applied|responded|interview|offer|rejected|discarded|skip"
        r"|evaluada|aplicado|respondido|entrevista|oferta|rechazado|descartado"
        r"|no aplicar|cerrada|duplicado|repost|condicional|hold|monitor)",
        re.IGNORECASE,
    )

    c4_is_score = bool(score_re.match(col4.strip()))
    c5_is_score = bool(score_re.match(col5.strip()))
    c4_is_status = bool(status_re.match(col4.strip()))
    c5_is_status = bool(status_re.match(col5.strip()))

    if c4_is_status and not c4_is_score:
        return col4.strip(), col5.strip()   # standard: status, score
    if c4_is_score and c5_is_status:
        return col5.strip(), col4.strip()   # swapped: score first
    if c5_is_score and not c4_is_score:
        return col4.strip(), col5.strip()   # col5 is score → col4 is status
    return col4.strip(), col5.strip()       # default: standard


def _strip_bold(s: str) -> str:
    return s.replace("**", "").strip()


def _parse_score_float(raw: str) -> float:
    m = re.search(r"([\d.]+)", _strip_bold(raw))
    return float(m.group(1)) if m else 0.0


def _parse_tsv_content(content: str, filename: str) -> Optional[ApplicationRow]:
    """Parse a single TSV file content into an ApplicationRow."""
    content = content.strip()
    if not content:
        return None

    # Pipe-delimited (markdown table row)
    if content.startswith("|"):
        parts = [p.strip() for p in content.strip("|").split("|")]
        if len(parts) < 8:
            print(f"  ⚠️  Skipping malformed pipe-delimited {filename}: {len(parts)} fields")
            return None
        # Format from pipe rows: num | date | company | role | score | status | pdf | report | notes
        score_raw = _strip_bold(parts[4])
        status_raw = _strip_bold(parts[5])
        status = normalize_status(status_raw) or "Evaluated"
        try:
            num = int(parts[0])
        except ValueError:
            return None
        return ApplicationRow(
            num=num, date=parts[1], company=_strip_bold(parts[2]),
            role=_strip_bold(parts[3]), score_raw=score_raw,
            score=_parse_score_float(score_raw) if score_raw not in ("N/A", "DUP") else None,
            status=status, pdf=parts[6], report=parts[7],
            notes=parts[8] if len(parts) > 8 else "",
        )

    # Tab-separated
    parts = content.split("\t")
    if len(parts) < 8:
        print(f"  ⚠️  Skipping malformed TSV {filename}: {len(parts)} fields")
        return None

    status_raw, score_raw = _detect_column_order(parts[4], parts[5])
    status = normalize_status(status_raw) or "Evaluated"
    score_raw_clean = _strip_bold(score_raw)

    try:
        num = int(parts[0])
    except ValueError:
        return None

    return ApplicationRow(
        num=num, date=parts[1], company=_strip_bold(parts[2]),
        role=_strip_bold(parts[3]), score_raw=score_raw_clean,
        score=_parse_score_float(score_raw_clean) if score_raw_clean not in ("N/A", "DUP") else None,
        status=status, pdf=_strip_bold(parts[6]), report=_strip_bold(parts[7]),
        notes=_strip_bold(parts[8]) if len(parts) > 8 else "",
    )


def _extract_report_num(report_str: str) -> Optional[int]:
    m = re.search(r"\[(\d+)\]", report_str)
    return int(m.group(1)) if m else None


def merge(cfg: ProjectConfig, dry_run: bool = False, verify: bool = False) -> int:
    """Merge pending TSVs into applications.md. Returns exit code (0=ok, 1=verify failed)."""
    cfg.ensure_dirs()

    apps_file = cfg.applications_md
    additions_dir = cfg.tracker_additions_dir
    merged_dir = cfg.tracker_additions_merged_dir

    existing = parse_applications(apps_file) if apps_file.exists() else []
    max_num = max((r.num for r in existing), default=0)
    print(f"📊 Existing: {len(existing)} entries, max #{max_num}")

    tsv_files = sorted(additions_dir.glob("*.tsv"), key=lambda p: int(re.sub(r"\D", "", p.stem) or "0"))
    if not tsv_files:
        print("✅ No pending additions to merge.")
        return 0

    print(f"📥 Found {len(tsv_files)} pending additions")

    # Keep the lines from applications.md so we can do in-place updates
    app_lines = apps_file.read_text(encoding="utf-8").splitlines() if apps_file.exists() else []

    added = updated = skipped = 0
    new_lines: list[str] = []

    for tsv_path in tsv_files:
        addition = _parse_tsv_content(tsv_path.read_text(encoding="utf-8"), tsv_path.name)
        if addition is None:
            skipped += 1
            continue

        report_num = _extract_report_num(addition.report)
        norm_company = normalize_company(addition.company)

        # Find duplicate by: 1) report number, 2) entry number, 3) company+role
        duplicate: Optional[ApplicationRow] = None
        if report_num:
            duplicate = next(
                (r for r in existing if _extract_report_num(r.report) == report_num), None
            )
        if not duplicate:
            duplicate = next((r for r in existing if r.num == addition.num), None)
        if not duplicate:
            duplicate = next(
                (r for r in existing
                 if normalize_company(r.company) == norm_company
                 and role_fuzzy_match(addition.role, r.role)),
                None,
            )

        if duplicate:
            new_score = addition.score or 0.0
            old_score = duplicate.score or 0.0
            if new_score > old_score:
                print(f"🔄 Update: #{duplicate.num} {addition.company} — {addition.role} ({old_score}→{new_score})")
                updated_line = (
                    f"| {duplicate.num} | {addition.date} | {addition.company} | {addition.role} | "
                    f"{addition.score_raw} | {duplicate.status} | {duplicate.pdf} | {addition.report} | "
                    f"Re-eval {addition.date} ({old_score}→{new_score}). {addition.notes} |"
                )
                for i, line in enumerate(app_lines):
                    if line == duplicate.raw_line:
                        app_lines[i] = updated_line
                        break
                updated += 1
            else:
                print(f"⏭️  Skip: {addition.company} — {addition.role} (existing #{duplicate.num} {old_score} >= new {new_score})")
                skipped += 1
        else:
            entry_num = addition.num if addition.num > max_num else max_num + 1
            if addition.num > max_num:
                max_num = addition.num
            else:
                max_num = entry_num
            addition.num = entry_num
            new_lines.append(_row_to_line(addition))
            added += 1
            print(f"➕ Add #{entry_num}: {addition.company} — {addition.role} ({addition.score_raw})")

    # Insert new rows after separator line
    if new_lines:
        sep_idx = next((i for i, l in enumerate(app_lines) if l.startswith("|") and re.match(r"^\|[-\s|]+\|", l)), -1)
        if sep_idx >= 0:
            for j, new_line in enumerate(new_lines):
                app_lines.insert(sep_idx + 1 + j, new_line)
        else:
            app_lines.extend(new_lines)

    if not dry_run:
        apps_file.parent.mkdir(parents=True, exist_ok=True)
        apps_file.write_text("\n".join(app_lines) + "\n", encoding="utf-8")
        merged_dir.mkdir(parents=True, exist_ok=True)
        for tsv_path in tsv_files:
            shutil.move(str(tsv_path), merged_dir / tsv_path.name)
        print(f"\n✅ Moved {len(tsv_files)} TSVs to merged/")

    print(f"\n📊 Summary: +{added} added, 🔄{updated} updated, ⏭️{skipped} skipped")
    if dry_run:
        print("(dry-run — no changes written)")

    if verify and not dry_run:
        from career_ops_core.scripts.verify_pipeline import verify_pipeline
        ok = verify_pipeline(cfg)
        return 0 if ok else 1

    return 0
