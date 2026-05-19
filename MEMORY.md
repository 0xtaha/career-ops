# Project Memory

> Living document. Update this file as the project evolves. It captures decisions, current state, and context that isn't obvious from code or history alone.

---

## Current State

| Item | Value |
|------|-------|
| **Version** | 1.9.0-dev |
| **Branch** | `feature/migrating-to-python` |
| **Base** | `main` |
| **Date** | 2026-05-19 |
| **Migration** | Phase 1 complete (core data layer + 4 CLI commands) |

---

## Active Branch: `feature/migrating-to-python`

**Purpose:** Full migration from Node.js `.mjs` scripts + Go TUI → Python uv workspace + React frontend.
Migration plan: `.claude/plans/imperative-questing-dewdrop.md`

### Phase 1 — Complete ✅
- `pyproject.toml` — uv workspace root (members: core, cli, api)
- `packages/core/` — `career-ops-core` package:
  - `career_ops_core/config.py` — `ProjectConfig` with all path resolution
  - `career_ops_core/data/` — states.py, normalize.py, applications.py, pipeline_md.py, scan_history.py
  - `career_ops_core/scripts/` — merge_tracker.py, normalize_statuses.py, dedup_tracker.py, verify_pipeline.py
- `packages/cli/` — `career-ops-cli` package (Typer, `career-ops` entrypoint)
  - `merge`, `normalize`, `dedup`, `verify` commands working
  - Stub commands for Phase 2 (pdf, scan, liveness, patterns, followup, doctor, sync-check, update, gemini-eval)
- `tests/robot/` updated:
  - `common.resource` — `Run Script` now calls `career-ops --root ${ws} {cmd}` (not `node {script}`)
  - `01_smoke.robot` — Python import checks replace `node --check` syntax checks
  - Suites 02-05 — script names updated to CLI command names (merge/normalize/dedup/verify)
  - `pyproject.toml` — `career-ops-cli` added as workspace dep

### Phase 2 — Pending
Port remaining scripts + providers; complete CLI.

### Phase 3 — Pending
FastAPI server package.

### Phase 4 — Pending
React frontend + remove Node.js/Go code.

### Phase 5 — Parallel with 2-4
RF test hardening (all 6 suites passing).

---

## Recent Releases

| Version | Date | Highlights |
|---------|------|------------|
| **1.8.0** | 2026-05-15 | `location_filter` in `portals.yml`, batch workers now read `_profile.md`, Gemini model updates, merge-tracker short-specialty fix (#633) |
| 1.7.1 | 2026-05-12 | Hotfix: `.agents/` in SYSTEM_PATHS |
| 1.7.0 | 2026-05-06 | Block G (posting legitimacy), Gemini CLI integration, LaTeX CV export, scan.mjs portal scanner, writing-samples, follow-up tracker, interview-prep split by audience |
| 1.6.0 | earlier | Dashboard progress screen, Catppuccin Latte light theme, contacto mode by contact type |

Full history: [`CHANGELOG.md`](CHANGELOG.md)

---

## Architecture Decisions

### Scripts use `import.meta.url` for path resolution

All `.mjs` scripts resolve data paths via `dirname(fileURLToPath(import.meta.url))` rather than `process.cwd()`. This means data files are found relative to the script's own location. Consequence: for test isolation, copy the scripts to a temp directory (as the Robot Framework suite does) rather than trying to set `cwd`.

### Tracker column order differs between TSV and applications.md

In `batch/tracker-additions/*.tsv`: `Status` comes before `Score`.
In `data/applications.md`: `Score` comes before `Status`.
`merge-tracker.mjs` handles this swap automatically. This asymmetry exists for historical reasons — do not "fix" it without updating all consumers.

### Modal system over single monolithic prompt

Skill modes are separate files so they can be updated independently without requiring the user to re-onboard. `_shared.md` holds shared rules; modes hold task-specific instructions. This allows partial updates (e.g. improving `oferta.md`) without touching the scoring engine.

### Batch workers are stateless

Each batch worker receives a fully self-contained prompt and writes its outputs (report, PDF, TSV) independently. The orchestrator (`batch-runner.sh`) manages state in `batch-state.tsv`. Workers never communicate with each other. This allows parallel execution and clean failure recovery.

---

## Known Issues / Watch Items

| # | Area | Description |
|---|------|-------------|
| - | Batch | Workers require the AI CLI binary in PATH; missing binary fails silently with no helpful error |
| - | PDF generation | Requires Playwright chromium; first-run setup via `npx playwright install chromium` |
| - | Dashboard | Go build required separately; `test-all.mjs --quick` skips it |
| - | Liveness check | Playwright-based; does not work in batch/headless mode — uses WebFetch fallback with "unconfirmed" marker in report header |

---

## Test Status

| Suite | Tests | Last run | Status |
|-------|-------|----------|--------|
| `test-all.mjs` | 63+ | CI on PRs | passing on `main` |
| Go `go test ./...` | ~10 | CI on PRs | passing on `main` |
| RF `tests/robot/` | 64 | manual | dry-run validated ✅ |

---

## What "feature/migrating-to-python" Needs Before Merge

- [ ] Run full Robot Framework suite against a real workspace (not just `--dryrun`)
- [ ] Confirm `uv` is available in CI or add installation step to `.github/workflows/test.yml`
- [ ] Decide if RF tests should run on every PR or only on changes to `*.mjs`
- [ ] Update `test-all.mjs` check count if RF suite is added to CI

---

## File Ownership Quick Reference

| File | Layer | Can agent edit? |
|------|-------|----------------|
| `modes/_shared.md` | System | Yes (shared defaults only, no personal data) |
| `modes/_profile.md` | User | Yes (this is the intended personalization target) |
| `config/profile.yml` | User | Yes (agent fills this during onboarding and updates) |
| `cv.md` | User | Yes (agent creates/edits on request) |
| `data/applications.md` | User | Only to UPDATE existing entries; new entries go via TSV |
| `portals.yml` | User | Yes |
| `templates/states.yml` | System | Only to add/rename canonical states (rare) |
| `ARCHITECTURE.md` | System | Yes (keep up-to-date as features are added) |
| `MEMORY.md` | System | Yes (update when significant decisions are made) |
| `CLAUDE.md` | System | Yes (add Claude-specific guidance) |
