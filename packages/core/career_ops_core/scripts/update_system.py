"""update_system — check for and apply system updates.

Port of update-system.mjs. SYSTEM_PATHS updated to Python/React layout.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from career_ops_core.config import ProjectConfig

# Files that are safe to auto-overwrite on update (system layer)
SYSTEM_PATHS = [
    "modes/_shared.md",
    "modes/oferta.md",
    "modes/ofertas.md",
    "modes/auto-pipeline.md",
    "modes/pdf.md",
    "modes/scan.md",
    "modes/batch.md",
    "modes/apply.md",
    "modes/contacto.md",
    "modes/deep.md",
    "modes/tracker.md",
    "modes/pipeline.md",
    "modes/patterns.md",
    "modes/followup.md",
    "modes/interview-prep.md",
    "modes/training.md",
    "modes/project.md",
    "modes/latex.md",
    "templates/states.yml",
    "templates/cv-template.html",
    "templates/cv-template.tex",
    "templates/portals.example.yml",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "VERSION",
    # Python packages (system layer in new stack)
    "packages/core/",
    "packages/cli/",
    "packages/api/",
    "pyproject.toml",
    "batch/batch-prompt.md",
    "batch/batch-runner.sh",
]

# User-layer paths — NEVER overwrite these
USER_PATHS = [
    "cv.md",
    "config/profile.yml",
    "modes/_profile.md",
    "portals.yml",
    "data/",
    "reports/",
    "output/",
    "jds/",
    "interview-prep/",
    "writing-samples/",
    "article-digest.md",
]


def _is_user_path(path: str) -> bool:
    return any(path.startswith(u) for u in USER_PATHS)


def update_system(cfg: ProjectConfig, action: str = "check") -> None:
    if action == "check":
        _check(cfg)
    elif action == "apply":
        _apply(cfg)
    elif action == "rollback":
        _rollback(cfg)
    elif action == "dismiss":
        _dismiss(cfg)
    else:
        print(f"Unknown action: {action}. Use check | apply | rollback | dismiss")


def _read_version(cfg: ProjectConfig) -> Optional[str]:
    version_file = cfg.root / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return None


def _check(cfg: ProjectConfig) -> None:
    local = _read_version(cfg)
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin"],
            capture_output=True, text=True, timeout=10, cwd=cfg.root,
        )
        tags = re.findall(r"refs/tags/v?([\d.]+)$", result.stdout, re.MULTILINE)
        if not tags:
            print(json.dumps({"status": "no-remote-version"}))
            return
        latest = sorted(tags, key=lambda v: [int(x) for x in v.split(".")])[-1]
        if local and local.lstrip("v") == latest:
            print(json.dumps({"status": "up-to-date", "version": local}))
        else:
            print(json.dumps({"status": "update-available", "local": local, "remote": latest}))
    except Exception:
        print(json.dumps({"status": "offline"}))


def _apply(cfg: ProjectConfig) -> None:
    print("⚠️  update apply: fetch from upstream and overwrite system files")
    print("    (Not yet implemented in Python port — use git pull for now)")


def _rollback(cfg: ProjectConfig) -> None:
    print("⚠️  update rollback: restore from backup branch")
    print("    (Not yet implemented in Python port — use git checkout for now)")


def _dismiss(cfg: ProjectConfig) -> None:
    version = _read_version(cfg)
    dismiss_file = cfg.root / ".update-dismissed"
    dismiss_file.write_text(version or "unknown", encoding="utf-8")
    print(json.dumps({"status": "dismissed", "version": version}))
