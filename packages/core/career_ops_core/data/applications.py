"""Parser, writer and models for data/applications.md.

Handles:
- Pipe-delimited markdown table parsing
- Markdown bold stripping in all fields
- Column order: # | Date | Company | Role | Score | Status | PDF | Report | Notes
- Score formats: X/5, X.X/5, X.XX/5, N/A, DUP
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ApplicationRow:
    num: int
    date: str
    company: str
    role: str
    score_raw: str          # e.g. "4.2/5", "N/A", "DUP"
    score: Optional[float]  # parsed float or None
    status: str
    pdf: str
    report: str
    notes: str
    url: str = ""           # populated by 5-tier URL enrichment
    raw_line: str = ""      # original markdown line (for in-place updates)


def _strip_bold(s: str) -> str:
    return s.replace("**", "").strip()


def _parse_score(raw: str) -> Optional[float]:
    s = _strip_bold(raw)
    if s in ("N/A", "DUP", ""):
        return None
    m = re.search(r"([\d.]+)", s)
    return float(m.group(1)) if m else None


# Lines to skip when iterating the markdown table
_SKIP_PATTERNS = re.compile(
    r"^\s*$"                      # blank
    r"|^#\s"                      # heading
    r"|^\|[-\s|]+\|"              # separator row (---|...)
    r"|Company|Empresa",          # header row
    re.IGNORECASE,
)


def parse_applications(path: Path) -> list[ApplicationRow]:
    """Parse applications.md and return all valid data rows."""
    if not path.exists():
        return []

    rows: list[ApplicationRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        if _SKIP_PATTERNS.search(line):
            continue

        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 8:
            continue

        try:
            num = int(parts[0])
        except ValueError:
            continue
        if num == 0:
            continue

        score_raw = _strip_bold(parts[4])
        rows.append(
            ApplicationRow(
                num=num,
                date=parts[1],
                company=_strip_bold(parts[2]),
                role=_strip_bold(parts[3]),
                score_raw=score_raw,
                score=_parse_score(score_raw),
                status=_strip_bold(parts[5]),
                pdf=parts[6],
                report=parts[7],
                notes=parts[8] if len(parts) > 8 else "",
                raw_line=line,
            )
        )
    return rows


def _row_to_line(row: ApplicationRow) -> str:
    return (
        f"| {row.num} | {row.date} | {row.company} | {row.role} | "
        f"{row.score_raw} | {row.status} | {row.pdf} | {row.report} | {row.notes} |"
    )


def write_applications(path: Path, rows: list[ApplicationRow]) -> None:
    """Rewrite applications.md preserving the header and separator, replacing data rows."""
    if not path.exists():
        header = (
            "# Applications Tracker\n\n"
            "| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n"
            "|---|------|---------|------|-------|--------|-----|--------|-------|\n"
        )
        path.write_text(header + "\n".join(_row_to_line(r) for r in rows) + "\n", encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Find separator line index
    sep_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and re.match(r"^\|[-\s|]+\|", line):
            sep_idx = i
            break

    if sep_idx == -1:
        # No separator — append all rows at end
        path.write_text(content.rstrip() + "\n" + "\n".join(_row_to_line(r) for r in rows) + "\n")
        return

    # Keep everything up to and including separator, then write rows
    header_lines = lines[: sep_idx + 1]
    new_content = "\n".join(header_lines) + "\n" + "\n".join(_row_to_line(r) for r in rows) + "\n"
    path.write_text(new_content, encoding="utf-8")
