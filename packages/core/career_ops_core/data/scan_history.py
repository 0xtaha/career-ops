"""Reader/writer for data/scan-history.tsv.

Columns (7 tab-separated):
    url  first_seen  portal  title  company  status  location
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_HEADER = "url\tfirst_seen\tportal\ttitle\tcompany\tstatus\tlocation"


@dataclass
class ScanHistoryRow:
    url: str
    first_seen: str
    portal: str
    title: str
    company: str
    status: str
    location: str


def read_scan_history(path: Path) -> list[ScanHistoryRow]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("url\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts += [""] * (7 - len(parts))
        rows.append(ScanHistoryRow(*parts[:7]))
    return rows


def append_scan_history(path: Path, rows: list[ScanHistoryRow]) -> None:
    if not path.exists():
        path.write_text(_HEADER + "\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(f"{r.url}\t{r.first_seen}\t{r.portal}\t{r.title}\t{r.company}\t{r.status}\t{r.location}\n")
