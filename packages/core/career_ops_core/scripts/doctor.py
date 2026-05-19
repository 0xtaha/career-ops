"""doctor — setup validation for career-ops Python stack.

Port of doctor.mjs updated for the Python/uv/Playwright environment.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from career_ops_core.config import ProjectConfig


def run_doctor(cfg: ProjectConfig) -> bool:
    print("\ncareer-ops doctor")
    print("================\n")
    cfg.ensure_dirs()

    checks: list[tuple[bool, str, str]] = []  # (pass, label, fix)

    # Python version
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 12:
        checks.append((True, f"Python >= 3.12 (v{major}.{minor})", ""))
    else:
        checks.append((False, f"Python >= 3.12 required (found {major}.{minor})", "Install Python 3.12+ from https://python.org"))

    # uv
    if shutil.which("uv"):
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip()
            checks.append((True, f"uv installed ({version})", ""))
        except Exception:
            checks.append((True, "uv installed", ""))
    else:
        checks.append((False, "uv not installed", "Install from https://docs.astral.sh/uv/"))

    # Playwright chromium
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            exec_path = pw.chromium.executable_path
            if Path(exec_path).exists():
                checks.append((True, "Playwright chromium installed", ""))
            else:
                checks.append((False, "Playwright chromium not installed", "Run: uv run playwright install chromium"))
    except Exception:
        checks.append((False, "Playwright not installed", "Run: uv sync && uv run playwright install chromium"))

    # Required user files
    for label, path in [
        ("cv.md found", cfg.cv_md),
        ("config/profile.yml found", cfg.profile_yml),
        ("portals.yml found", cfg.portals_yml),
        ("templates/states.yml found", cfg.states_yml),
        ("cv-template.html found", cfg.cv_template_html),
    ]:
        checks.append((path.exists(), label, f"Create {path.relative_to(cfg.root) if path.is_relative_to(cfg.root) else path}"))

    # Auto-created dirs (already done by ensure_dirs)
    for name in ("data", "output", "reports"):
        d = cfg.root / name
        checks.append((d.exists(), f"{name}/ directory ready", ""))

    # Fonts
    fonts_dir = cfg.root / "fonts"
    if fonts_dir.exists() and any(fonts_dir.iterdir()):
        checks.append((True, "Fonts directory ready", ""))
    else:
        checks.append((False, "fonts/ directory missing or empty", "The fonts/ directory is required for PDF generation"))

    failures = 0
    for passed, label, fix in checks:
        if passed:
            print(f"✓ {label}")
        else:
            failures += 1
            print(f"✗ {label}")
            if fix:
                print(f"  → {fix}")

    print("")
    if failures > 0:
        print(f"Result: {failures} issue(s) found. Fix them and run `career-ops doctor` again.")
        return False
    else:
        print("Result: All checks passed. Run `career-ops` to start.")
        return True
