"""career-ops CLI — Typer-based entry point.

All commands accept --root to override the project root (default: cwd).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="career-ops",
    help="AI job search pipeline — manage your application tracker.",
    no_args_is_help=True,
)
console = Console()

_root_option = typer.Option(
    None,
    "--root",
    help="Project root directory (default: current working directory).",
    show_default=False,
)


def _cfg(root: Optional[Path]) -> "ProjectConfig":
    from career_ops_core.config import ProjectConfig
    resolved = Path(root).resolve() if root else Path.cwd()
    return ProjectConfig(resolved)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

@app.command()
def merge(
    root: Optional[Path] = _root_option,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
    verify: bool = typer.Option(False, "--verify", help="Run verify-pipeline after merging."),
) -> None:
    """Merge batch/tracker-additions/*.tsv into data/applications.md."""
    from career_ops_core.scripts.merge_tracker import merge as _merge
    cfg = _cfg(root)
    exit_code = _merge(cfg, dry_run=dry_run, verify=verify)
    raise typer.Exit(exit_code)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

@app.command()
def normalize(
    root: Optional[Path] = _root_option,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
) -> None:
    """Normalize non-canonical statuses in data/applications.md."""
    from career_ops_core.scripts.normalize_statuses import normalize_statuses
    cfg = _cfg(root)
    normalize_statuses(cfg, dry_run=dry_run)


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------

@app.command()
def dedup(
    root: Optional[Path] = _root_option,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
) -> None:
    """Remove duplicate entries from data/applications.md."""
    from career_ops_core.scripts.dedup_tracker import dedup_tracker
    cfg = _cfg(root)
    dedup_tracker(cfg, dry_run=dry_run)


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

@app.command()
def verify(
    root: Optional[Path] = _root_option,
) -> None:
    """Check pipeline integrity (statuses, scores, report links, duplicates)."""
    from career_ops_core.scripts.verify_pipeline import verify_pipeline
    cfg = _cfg(root)
    ok = verify_pipeline(cfg)
    raise typer.Exit(0 if ok else 1)


# ---------------------------------------------------------------------------
# Remaining commands (Phase 2) — stubs that will be filled in
# ---------------------------------------------------------------------------

@app.command()
def pdf(
    root: Optional[Path] = _root_option,
    input_html: Optional[Path] = typer.Argument(None, help="Input HTML file."),
    output_pdf: Optional[Path] = typer.Argument(None, help="Output PDF path."),
    fmt: str = typer.Option("a4", "--format", help="Page format: a4 or letter."),
) -> None:
    """Generate a PDF from an HTML CV template using Playwright."""
    from career_ops_core.scripts.generate_pdf import generate_pdf
    cfg = _cfg(root)
    generate_pdf(cfg, input_html=input_html, output_pdf=output_pdf, page_format=fmt)


@app.command()
def scan(
    root: Optional[Path] = _root_option,
    dry_run: bool = typer.Option(False, "--dry-run"),
    company: Optional[str] = typer.Option(None, "--company"),
) -> None:
    """Scan configured job portals for new openings."""
    import asyncio
    from career_ops_core.scripts.scan import run_scan
    cfg = _cfg(root)
    asyncio.run(run_scan(cfg, dry_run=dry_run, company_filter=company))


@app.command()
def liveness(
    root: Optional[Path] = _root_option,
    urls: Optional[list[str]] = typer.Argument(None),
    file: Optional[Path] = typer.Option(None, "--file"),
) -> None:
    """Check whether job postings are still active."""
    import asyncio
    from career_ops_core.scripts.check_liveness import run_liveness
    cfg = _cfg(root)
    all_urls: list[str] = list(urls or [])
    if file:
        all_urls.extend(line.strip() for line in file.read_text().splitlines() if line.strip())
    ok = asyncio.run(run_liveness(cfg, all_urls))
    raise typer.Exit(0 if ok else 1)


@app.command()
def patterns(
    root: Optional[Path] = _root_option,
    summary: bool = typer.Option(False, "--summary"),
    min_threshold: int = typer.Option(2, "--min-threshold"),
) -> None:
    """Analyse rejection and success patterns in the tracker."""
    from career_ops_core.scripts.analyze_patterns import analyze_patterns
    cfg = _cfg(root)
    analyze_patterns(cfg, summary=summary, min_threshold=min_threshold)


@app.command()
def followup(
    root: Optional[Path] = _root_option,
    summary: bool = typer.Option(False, "--summary"),
    overdue_only: bool = typer.Option(False, "--overdue-only"),
    applied_days: int = typer.Option(14, "--applied-days"),
) -> None:
    """Show follow-up cadence for active applications."""
    from career_ops_core.scripts.followup_cadence import followup_cadence
    cfg = _cfg(root)
    followup_cadence(cfg, summary=summary, overdue_only=overdue_only, applied_days=applied_days)


@app.command()
def doctor(
    root: Optional[Path] = _root_option,
) -> None:
    """Run setup validation (Python, uv, Playwright, required files)."""
    from career_ops_core.scripts.doctor import run_doctor
    cfg = _cfg(root)
    ok = run_doctor(cfg)
    raise typer.Exit(0 if ok else 1)


@app.command(name="sync-check")
def sync_check(
    root: Optional[Path] = _root_option,
) -> None:
    """Validate consistency between cv.md and config/profile.yml."""
    from career_ops_core.scripts.cv_sync_check import cv_sync_check
    cfg = _cfg(root)
    cv_sync_check(cfg)


@app.command()
def update(
    root: Optional[Path] = _root_option,
    action: str = typer.Argument("check", help="check | apply | rollback | dismiss"),
) -> None:
    """Check for or apply system updates."""
    from career_ops_core.scripts.update_system import update_system
    cfg = _cfg(root)
    update_system(cfg, action=action)


@app.command(name="gemini-eval")
def gemini_eval(
    root: Optional[Path] = _root_option,
    jd_text: Optional[str] = typer.Argument(None, help="Job description text."),
    file: Optional[Path] = typer.Option(None, "--file", help="File containing JD text."),
) -> None:
    """Evaluate a job description using the Gemini API."""
    from career_ops_core.scripts.gemini_eval import gemini_eval as _eval
    cfg = _cfg(root)
    text = jd_text or (file.read_text() if file else None)
    if not text:
        console.print("[red]Provide JD text as argument or via --file[/red]")
        raise typer.Exit(1)
    _eval(cfg, jd_text=text)


if __name__ == "__main__":
    app()
