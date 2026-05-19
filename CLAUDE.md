# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
<!-- Add anything Claude Code specific that other agents don't need -->

---

> **Quick orientation:** `ARCHITECTURE.md` has the full developer reference. `MEMORY.md` tracks current branch state and decisions. `DATA_CONTRACT.md` is the authoritative user-layer / system-layer boundary.

---

## Development Commands

```bash
# Run the full test suite (63+ checks: syntax, scripts, data contract, personal data leak, mode integrity)
node test-all.mjs

# Skip the Go dashboard build for a faster run
node test-all.mjs --quick

# Robot Framework black-box tests (requires uv; 64 tests covering pipeline scripts)
cd tests/robot && uv run robot .

# Build and run the Go TUI dashboard
cd dashboard && go build -o career-dashboard .
./career-dashboard --path ..

# Setup validation (Node >= 18, Playwright chromium, required files, auto-creates data/output/reports/)
npm run doctor

# Pipeline health check (statuses, duplicates, broken report links)
npm run verify

# Run a single script directly
node verify-pipeline.mjs
node merge-tracker.mjs --dry-run
node normalize-statuses.mjs --dry-run
```

## Architecture

Career-ops is an **AI prompt + mode system**, not a traditional application. The runtime is the AI agent itself (Claude Code); the `.mjs` scripts are supporting utilities, not the core logic.

For the full developer architecture reference, see `ARCHITECTURE.md`.

**Core data flow:**
- `modes/_shared.md` — scoring engine, global rules; read by the agent at evaluation time
- `modes/_profile.md` — user-specific archetypes, comp targets, narrative (gitignored; never overwritten by updates)
- `modes/oferta.md`, `modes/pdf.md`, etc. — one file per skill mode; agent reads the relevant one
- `config/profile.yml` + `cv.md` — identity and CV, read live at evaluation time (never hardcoded)
- `batch/batch-prompt.md` — self-contained prompt bundled into headless worker invocations

**Data layers (critical distinction):**
- **User layer** (`cv.md`, `config/profile.yml`, `modes/_profile.md`, `data/*`, `reports/*`, `output/*`) — gitignored, never touched by `update-system.mjs apply`
- **System layer** (`modes/_shared.md`, all other `modes/*.md`, `*.mjs`, `templates/*`, `dashboard/*`) — safe to overwrite on update

**Evaluation pipeline (single offer):**
1. Agent reads JD → classifies archetype → runs 6-block evaluation (A–F) → scores across 10 dimensions
2. Report saved to `reports/{###}-{company-slug}-{YYYY-MM-DD}.md`
3. CV PDF generated via Playwright (`generate-pdf.mjs` → `templates/cv-template.html`)
4. Tracker entry written as TSV to `batch/tracker-additions/{num}-{slug}.tsv`
5. `merge-tracker.mjs` merges TSVs into `data/applications.md`

**Batch processing:** `batch-runner.sh` spawns N headless `claude -p` workers in parallel; each worker is self-contained and produces report + PDF + TSV; orchestrator manages state in `batch-state.tsv`.

**Dashboard:** Standalone Go TUI (`dashboard/`) using Bubble Tea. Reads `data/applications.md` directly — no server, no database.

**Update system:** `update-system.mjs` fetches system-layer files from upstream, creates a backup branch (`backup-pre-update-{version}`), and never touches user-layer files.

## Key Conventions for Contributors

- **Mode files go in `modes/`** (system layer). User personalizations go in `modes/_profile.md` (user layer). Never put user-specific content in `modes/_shared.md`.
- **Report numbering**: sequential 3-digit zero-padded (`001`, `002`, …). Always max-existing + 1.
- **Tracker TSV format**: 9 tab-separated columns — num, date, company, role, **status**, score, pdf, report-link, notes. Status comes before score in TSV; `merge-tracker.mjs` handles the column swap when writing to `applications.md`.
- **Canonical statuses** are defined in `templates/states.yml`. No bold, no dates, no extra text in the status column.
- **Never add entries to `data/applications.md` directly** — write TSV to `batch/tracker-additions/` and run `npm run merge`.
- All `.mjs` scripts must handle missing files gracefully (`existsSync` before `readFileSync`).
- Dashboard changes require `go build` and testing with real data before submitting.
- User files (`cv.md`, `config/profile.yml`, `data/applications.md`, `reports/`) must never be committed — they are gitignored.
- Scripts resolve data paths via `dirname(import.meta.url)` (not `process.cwd()`). Keep this in mind when writing tests — copy scripts to an isolated directory for full filesystem isolation.
