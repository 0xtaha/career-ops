"""Reader/writer for data/pipeline.md (URL inbox)."""
from __future__ import annotations

from pathlib import Path


def read_pipeline_urls(path: Path) -> list[str]:
    """Return all non-empty, non-header lines from pipeline.md."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.startswith("#") and not line.startswith("---")
    ]


def append_pipeline_urls(path: Path, urls: list[str]) -> None:
    """Append new URLs to pipeline.md, creating the file if needed."""
    if not path.exists():
        path.write_text("# Pipeline — pending URLs\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")
