"""ProjectConfig — all path resolution for career-ops."""
from pathlib import Path


class ProjectConfig:
    """Resolves all well-known paths from a project root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    # data files
    @property
    def applications_md(self) -> Path:
        candidate = self.root / "data" / "applications.md"
        if candidate.exists():
            return candidate
        return self.root / "applications.md"

    @property
    def pipeline_md(self) -> Path:
        return self.root / "data" / "pipeline.md"

    @property
    def scan_history_tsv(self) -> Path:
        return self.root / "data" / "scan-history.tsv"

    @property
    def follow_ups_md(self) -> Path:
        return self.root / "data" / "follow-ups.md"

    # batch
    @property
    def tracker_additions_dir(self) -> Path:
        return self.root / "batch" / "tracker-additions"

    @property
    def tracker_additions_merged_dir(self) -> Path:
        return self.tracker_additions_dir / "merged"

    @property
    def batch_input_tsv(self) -> Path:
        return self.root / "batch" / "batch-input.tsv"

    @property
    def batch_state_tsv(self) -> Path:
        return self.root / "batch" / "batch-state.tsv"

    # templates / config
    @property
    def states_yml(self) -> Path:
        candidate = self.root / "templates" / "states.yml"
        if candidate.exists():
            return candidate
        return self.root / "states.yml"

    @property
    def portals_yml(self) -> Path:
        return self.root / "portals.yml"

    @property
    def profile_yml(self) -> Path:
        return self.root / "config" / "profile.yml"

    @property
    def cv_md(self) -> Path:
        return self.root / "cv.md"

    @property
    def cv_template_html(self) -> Path:
        return self.root / "templates" / "cv-template.html"

    # output dirs
    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    def ensure_dirs(self) -> None:
        """Create all required directories if they don't exist."""
        for d in [
            self.root / "data",
            self.tracker_additions_dir,
            self.tracker_additions_merged_dir,
            self.reports_dir,
            self.output_dir,
            self.root / "config",
        ]:
            d.mkdir(parents=True, exist_ok=True)
