"""analyze_patterns — rejection and success pattern analysis.

Port of analyze-patterns.mjs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from career_ops_core.config import ProjectConfig
from career_ops_core.data.states import ALIASES


def _normalize_status(raw: str) -> str:
    clean = raw.replace("**", "").strip().lower()
    clean = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", clean).strip()
    return ALIASES.get(clean, clean)


def _classify_outcome(status: str) -> str:
    s = _normalize_status(status)
    if s in ("interview", "offer", "responded", "applied"):
        return "positive"
    if s in ("rejected", "discarded"):
        return "negative"
    if s == "skip":
        return "self_filtered"
    return "pending"


def _parse_tracker(cfg: ProjectConfig) -> list[dict]:
    apps_file = cfg.applications_md
    if not apps_file.exists():
        return []
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
        entries.append({
            "num": num, "date": parts[2], "company": parts[3],
            "role": parts[4], "score": parts[5], "status": parts[6],
            "pdf": parts[7], "report": parts[8], "notes": parts[9] if len(parts) > 9 else "",
        })
    return entries


def _parse_report(report_path: Path) -> Optional[dict]:
    if not report_path.exists():
        return None
    content = report_path.read_text(encoding="utf-8")
    plain = content.replace("**", "")

    def _first_match(pattern: str) -> Optional[str]:
        m = re.search(pattern, plain, re.IGNORECASE)
        return m.group(1).strip() if m else None

    scores = {}
    for label, key in [
        (r"CV Match|Match con CV", "cvMatch"),
        (r"North Star", "northStar"),
        (r"\bComp\b", "comp"),
        (r"Cultural signals|Cultural", "cultural"),
        (r"Red flags", "redFlags"),
        (r"\bGlobal\b", "global"),
    ]:
        m = re.search(rf"\|\s*(?:{label})\s*\|\s*([-\d.]+)(?:/5)?\s*\|", plain, re.IGNORECASE)
        if m:
            try:
                scores[key] = float(m.group(1))
            except ValueError:
                pass

    # Parse gaps
    gaps = []
    gap_block = re.search(r"\|\s*Gap\s*\|\s*Severity\s*\|.*?\n\|[-|\s]+\n([\s\S]*?)(?:\n\n|\n##|\n\*\*|$)", content, re.IGNORECASE)
    if gap_block:
        for row in gap_block.group(1).splitlines():
            if not row.startswith("|"):
                continue
            cols = [c.strip() for c in row.strip("|").split("|")]
            if len(cols) >= 2:
                gaps.append({"description": cols[0], "severity": cols[1].lower(), "mitigation": cols[2] if len(cols) > 2 else ""})

    return {
        "archetype": _first_match(r"\|\s*(?:Archetype|Arquetipo)\s*\|\s*(.*?)\s*\|"),
        "seniority": _first_match(r"\|\s*(?:Seniority|Nivel|Level)\s*\|\s*(.*?)\s*\|"),
        "remote": _first_match(r"\|\s*(?:Remote|Remoto|Location)\s*\|\s*(.*?)\s*\|"),
        "teamSize": _first_match(r"\|\s*(?:Team|Team size|Equipo)\s*\|\s*(.*?)\s*\|"),
        "comp": _first_match(r"\|\s*(?:Comp|Salary|Salario|Listed salary)\s*\|\s*(.*?)\s*\|"),
        "domain": _first_match(r"\|\s*(?:Domain|Dominio|Industry)\s*\|\s*(.*?)\s*\|"),
        "scores": scores,
        "gaps": gaps,
    }


def _classify_remote(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    lower = raw.lower()
    if re.search(r"\b(us[- ]?only|canada[- ]?only|residents only|usa only|us residents)\b", lower):
        return "geo-restricted"
    if re.search(r"\b(hybrid|on-?site|office|relocat)\b", lower):
        return "hybrid/onsite"
    if re.search(r"\b(global|anywhere|worldwide|work from anywhere)\b", lower):
        return "global remote"
    if re.search(r"\b(remote|latam|americas|brazil|fully remote)\b", lower):
        return "regional remote"
    return "unknown"


def _classify_company_size(team: Optional[str]) -> str:
    if not team:
        return "unknown"
    lower = team.lower()
    nums = re.findall(r"[\d,]+", lower)
    if nums:
        mx = max(int(n.replace(",", "")) for n in nums)
        if mx <= 50:
            return "startup"
        if mx <= 500:
            return "scaleup"
        return "enterprise"
    if re.search(r"\b(small|elite|tiny|founding)\b", lower):
        return "startup"
    if re.search(r"\b(large|enterprise|global)\b", lower):
        return "enterprise"
    return "unknown"


def _blocker_type(gap: dict) -> Optional[str]:
    desc = gap["description"].lower()
    sev = gap["severity"].lower()
    if "nice" in sev or "soft" in sev:
        return None
    if re.search(r"\b(residency|us[- ]?only|canada|location|visa|geo|country|region)\b", desc):
        return "geo-restriction"
    if re.search(r"\b(javascript|typescript|python|ruby|java|go|rust|node|react|angular|vue|django|flask|rails)\b", desc):
        return "stack-mismatch"
    if re.search(r"\b(senior|staff|lead|principal|director|manager|head)\b", desc):
        return "seniority-mismatch"
    if re.search(r"\b(hybrid|on-?site|office|relocat)\b", desc):
        return "onsite-requirement"
    return "other"


def _score_stats(scores: list[float]) -> dict:
    if not scores:
        return {"avg": 0, "min": 0, "max": 0, "count": 0}
    avg = sum(scores) / len(scores)
    return {"avg": round(avg, 2), "min": min(scores), "max": max(scores), "count": len(scores)}


def analyze_patterns(cfg: ProjectConfig, summary: bool = False, min_threshold: int = 5) -> None:
    entries = _parse_tracker(cfg)
    if not entries:
        print(json.dumps({"error": "No applications found in tracker."}, indent=2))
        return

    enriched = []
    for e in entries:
        report_match = re.search(r"\]\(([^)]+)\)", e["report"])
        report_path = (cfg.root / report_match.group(1)) if report_match else None
        report_data = _parse_report(report_path) if report_path else None
        outcome = _classify_outcome(e["status"])
        score_raw = re.sub(r"\*\*", "", e["score"])
        m = re.search(r"[\d.]+", score_raw)
        score = float(m.group()) if m else 0.0
        enriched.append({
            **e,
            "normalizedStatus": _normalize_status(e["status"]),
            "outcome": outcome,
            "score": score,
            "reportData": report_data,
            "remoteBucket": _classify_remote((report_data or {}).get("remote") or e["notes"]),
            "companySize": _classify_company_size((report_data or {}).get("teamSize")),
        })

    beyond_eval = [e for e in enriched if e["normalizedStatus"] != "evaluated"]
    if len(beyond_eval) < min_threshold:
        result = {
            "error": f"Not enough data: {len(beyond_eval)}/{min_threshold} applications beyond 'Evaluated'.",
            "current": len(beyond_eval),
            "threshold": min_threshold,
        }
        print(json.dumps(result, indent=2))
        return

    funnel: dict[str, int] = {}
    for e in enriched:
        funnel[e["normalizedStatus"]] = funnel.get(e["normalizedStatus"], 0) + 1

    by_outcome: dict[str, list[float]] = {"positive": [], "negative": [], "self_filtered": [], "pending": []}
    for e in enriched:
        if e["score"] > 0:
            by_outcome[e["outcome"]].append(e["score"])

    score_comparison = {k: _score_stats(v) for k, v in by_outcome.items()}

    # Archetype breakdown
    arch_map: dict[str, dict] = {}
    for e in enriched:
        arch = (e["reportData"] or {}).get("archetype") or "Unknown"
        if arch not in arch_map:
            arch_map[arch] = {"total": 0, "positive": 0, "negative": 0, "self_filtered": 0, "pending": 0}
        arch_map[arch]["total"] += 1
        arch_map[arch][e["outcome"]] += 1
    archetype_breakdown = sorted(
        [{"archetype": k, **v, "conversionRate": round(v["positive"] / v["total"] * 100) if v["total"] else 0} for k, v in arch_map.items()],
        key=lambda x: -x["total"],
    )

    # Blocker analysis
    blocker_counts: dict[str, int] = {}
    for e in enriched:
        for gap in (e["reportData"] or {}).get("gaps") or []:
            bt = _blocker_type(gap)
            if bt:
                blocker_counts[bt] = blocker_counts.get(bt, 0) + 1
    blocker_analysis = sorted(
        [{"blocker": k, "frequency": v, "percentage": round(v / len(enriched) * 100)} for k, v in blocker_counts.items()],
        key=lambda x: -x["frequency"],
    )

    dates = sorted(e["date"] for e in enriched if e["date"])

    result = {
        "metadata": {
            "total": len(enriched),
            "dateRange": {"from": dates[0] if dates else "", "to": dates[-1] if dates else ""},
            "byOutcome": {k: sum(1 for e in enriched if e["outcome"] == k) for k in ["positive", "negative", "self_filtered", "pending"]},
        },
        "funnel": funnel,
        "scoreComparison": score_comparison,
        "archetypeBreakdown": archetype_breakdown,
        "blockerAnalysis": blocker_analysis,
    }

    if summary:
        _print_summary(result)
    else:
        print(json.dumps(result, indent=2))


def _print_summary(result: dict) -> None:
    meta = result["metadata"]
    print(f"\n{'=' * 60}")
    print(f"  Pattern Analysis — {meta.get('analysisDate', '')}")
    print(f"  {meta['total']} applications")
    print(f"{'=' * 60}\n")
    print("CONVERSION FUNNEL")
    print("-" * 40)
    for status, count in sorted(result["funnel"].items(), key=lambda x: -x[1]):
        pct = round(count / meta["total"] * 100)
        print(f"  {status:<15} {count:>3} ({pct}%)")
    print("\nSCORE BY OUTCOME")
    print("-" * 40)
    for group, stats in result["scoreComparison"].items():
        if stats["count"] > 0:
            print(f"  {group:<15} avg {stats['avg']}/5  ({stats['count']} entries)")
    if result["blockerAnalysis"]:
        print("\nTOP BLOCKERS")
        print("-" * 40)
        for b in result["blockerAnalysis"]:
            print(f"  {b['blocker']:<20} {b['frequency']:>2}x ({b['percentage']}%)")
    print("")
