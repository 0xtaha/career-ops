"""followup_cadence — follow-up cadence calculator.

Port of followup-cadence.mjs.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Optional

from career_ops_core.config import ProjectConfig
from career_ops_core.data.states import ALIASES

_ACTIONABLE = {"applied", "responded", "interview"}
_CADENCE = {
    "applied_first": 7,
    "applied_subsequent": 7,
    "applied_max_followups": 2,
    "responded_initial": 1,
    "responded_subsequent": 3,
    "interview_thankyou": 1,
}


def _normalize_status(raw: str) -> str:
    clean = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", raw.replace("**", "").strip().lower())
    return ALIASES.get(clean, clean)


def _parse_date(s: str) -> Optional[date]:
    s = s.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _days_since(d: date) -> int:
    return (date.today() - d).days


def followup_cadence(
    cfg: ProjectConfig,
    summary: bool = False,
    overdue_only: bool = False,
    applied_days: int = 7,
) -> None:
    cadence = {**_CADENCE, "applied_first": applied_days}
    apps_file = cfg.applications_md
    if not apps_file.exists():
        print(json.dumps({"error": "No applications.md found."}))
        return

    entries = []
    for line in apps_file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 9:
            continue
        try:
            num = int(parts[1])
        except ValueError:
            continue
        status = _normalize_status(parts[6])
        if status not in _ACTIONABLE:
            continue
        d = _parse_date(parts[2])
        if not d:
            continue
        days_since = _days_since(d)
        overdue = False
        next_followup: Optional[str] = None

        if status == "applied":
            if days_since >= cadence["applied_first"]:
                overdue = True
                next_followup = "Initial follow-up overdue"
            else:
                next_day = d + timedelta(days=cadence["applied_first"])
                next_followup = str(next_day)
        elif status == "responded":
            if days_since >= cadence["responded_initial"]:
                overdue = True
                next_followup = "Response follow-up overdue"
            else:
                next_followup = str(d + timedelta(days=cadence["responded_initial"]))
        elif status == "interview":
            if days_since >= cadence["interview_thankyou"]:
                overdue = True
                next_followup = "Thank-you note overdue"
            else:
                next_followup = str(d + timedelta(days=cadence["interview_thankyou"]))

        if overdue_only and not overdue:
            continue

        entries.append({
            "num": num,
            "date": str(d),
            "company": parts[3],
            "role": parts[4],
            "status": parts[6],
            "daysSince": days_since,
            "overdue": overdue,
            "nextFollowup": next_followup,
        })

    result = {"applications": entries, "total": len(entries), "overdue": sum(1 for e in entries if e["overdue"])}

    if summary:
        _print_summary(result)
    else:
        print(json.dumps(result, indent=2))


def _print_summary(result: dict) -> None:
    apps = result["applications"]
    print(f"\n{'=' * 60}")
    print(f"  Follow-up Cadence — {result['total']} active, {result['overdue']} overdue")
    print(f"{'=' * 60}\n")
    for e in sorted(apps, key=lambda x: -x["daysSince"]):
        flag = "🔴" if e["overdue"] else "🟡"
        print(f"{flag} #{e['num']} {e['company']} — {e['role']}")
        print(f"   Status: {e['status']} | Days since: {e['daysSince']} | Next: {e['nextFollowup']}")
    print("")
