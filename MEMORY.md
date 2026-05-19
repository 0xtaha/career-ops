# Project Memory

> Living document. Update this file as the project evolves. It captures decisions, current state, and context that isn't obvious from code or history alone.

---

## Current State

| Item | Value |
|------|-------|
| **Version** | 1.8.0 |
| **Branch** | `feature/migrating-to-python` |
| **Base** | `main` |
| **Date** | 2026-05-19 |

---

## Active Branch: `feature/migrating-to-python`

**Purpose:** Adds a Robot Framework black-box characterization test suite in `tests/robot/`.  The branch name reflects the addition of Python tooling (via `uv`) to an otherwise Node.js + Go project.

**Changes vs `main`:**
- `CLAUDE.md` — updated with test commands and references to `ARCHITECTURE.md` / `MEMORY.md`
- `ARCHITECTURE.md` — new file at project root (developer/contributor architecture reference)
- `MEMORY.md` — this file (new)
- `tests/robot/` — new directory:
  - 6 Robot Framework test suites (64 tests total)
  - `pyproject.toml` + `uv.lock` — Python dependency management
  - `resources/common.resource` — shared keywords and workspace isolation helper
  - `resources/liveness_wrapper.mjs` — CLI shim for `classifyLiveness()`
  - `resources/fixtures/` — 4 fixture `.md` files + 2 fixture `.tsv` files

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
