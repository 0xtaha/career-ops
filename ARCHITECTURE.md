# Architecture

> **Conceptual model:** career-ops is an **AI prompt + mode system**, not a traditional application. The runtime is the AI agent (Claude Code, Gemini CLI, Codex, etc.); the pipeline scripts handle data plumbing. The intelligence lives in `modes/`.

> **Migration status (Phase 1 complete):** The `.mjs` scripts are being replaced by a uv Python workspace (`packages/core`, `packages/cli`, `packages/api`) and a React frontend (`frontend/`). See the migration plan at `.claude/plans/imperative-questing-dewdrop.md`. Phase 1 delivers the core data layer and four CLI commands (`merge`, `normalize`, `dedup`, `verify`). The `.mjs` files and Go dashboard remain on the branch until Phase 4.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component Map](#2-component-map)
3. [Data Layers](#3-data-layers)
4. [Directory Reference](#4-directory-reference)
5. [Script Reference](#5-script-reference)
6. [Mode System](#6-mode-system)
7. [Language Variants](#7-language-variants)
8. [Evaluation Pipeline](#8-evaluation-pipeline)
9. [Batch Processing](#9-batch-processing)
10. [Dashboard (Go TUI)](#10-dashboard-go-tui)
11. [Update System](#11-update-system)
12. [Provider Layer](#12-provider-layer)
13. [Test Infrastructure](#13-test-infrastructure)
14. [Data Formats](#14-data-formats)
15. [Security Notes](#15-security-notes)

---

## 1. System Overview

```
User intent  →  AI Agent  →  modes/*.md  →  action
                   │
                   ├── reads cv.md + config/profile.yml    (identity)
                   ├── reads modes/_profile.md              (archetypes)
                   ├── reads modes/_shared.md               (scoring rules)
                   ├── reads modes/<skill>.md               (task instructions)
                   └── calls .mjs utilities as needed       (data I/O)
```

The agent never stores state between calls — it re-reads the relevant files on every interaction. The scripts manage persistence (tracker table, scan history, PDFs, reports).

---

## 2. Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                        AI Agent Runtime                          │
│               (Claude Code / Gemini CLI / Codex …)              │
└──────┬──────────────────┬──────────────────────────┬────────────┘
       │                  │                           │
  Single eval        Portal scan                Batch process
  (auto-pipeline)    (scan.mjs)                 (batch-runner.sh)
       │                  │                           │
       │         data/pipeline.md              N headless workers
       │         data/scan-history.tsv               │
       │                  │                           │
       └──────────────────▼───────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │      Output layer      │
              │  reports/{num}-*.md    │  ← evaluation report (blocks A–G)
              │  output/cv-*.pdf       │  ← ATS-optimised CV (Playwright)
              │  batch/tracker-        │  ← one TSV per evaluation
              │    additions/{n}.tsv   │
              └───────────┬────────────┘
                          │  merge-tracker.mjs
              ┌───────────▼────────────┐
              │  data/applications.md  │  ← canonical tracker (markdown table)
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  dashboard/ (Go TUI)   │  ← reads applications.md directly
              └────────────────────────┘
```

---

## 3. Data Layers

The **user layer** and **system layer** are the critical boundary. `update-system.mjs` respects it strictly; contributors must too.

### User Layer — NEVER auto-updated, personalization goes here

| Path | Purpose |
|------|---------|
| `cv.md` | Canonical CV in markdown — source of truth for all PDFs |
| `config/profile.yml` | Identity, target roles, comp range, narrative, location |
| `modes/_profile.md` | Archetypes, adaptive framing, negotiation scripts, proof points |
| `portals.yml` | Company list for scanner (copied from `templates/portals.example.yml`) |
| `article-digest.md` | Compact proof points from portfolio (optional) |
| `data/applications.md` | Application tracker — markdown table, managed by merge-tracker |
| `data/pipeline.md` | URL inbox — managed by scan.mjs |
| `data/scan-history.tsv` | Dedup history for scanner |
| `data/follow-ups.md` | Follow-up notes |
| `interview-prep/story-bank.md` | Accumulated STAR+R stories |
| `interview-prep/{company}-{role}.md` | Company-specific interview intel |
| `reports/*` | Evaluation reports |
| `output/*` | Generated PDFs |
| `jds/*` | Saved job descriptions |
| `writing-samples/*` | Personal writing samples (except `writing-samples/README.md`) |

### System Layer — safe to auto-update

| Path | Purpose |
|------|---------|
| `modes/_shared.md` | Scoring engine, global rules, tool config |
| `modes/*.md` | One file per skill mode |
| `modes/{de,fr,ja,pt,ru,tr}/` | Localised mode variants |
| `*.mjs` | Utility scripts |
| `providers/` | Portal scanner providers (Greenhouse, Lever, Ashby) |
| `templates/` | CV templates, states.yml |
| `dashboard/` | Go TUI |
| `batch/batch-prompt.md` | Headless worker system prompt |
| `batch/batch-runner.sh` | Batch orchestrator |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | Agent instructions |
| `docs/` | User-facing documentation |
| `fonts/` | Self-hosted web fonts for CV template |
| `VERSION` | Semver string (single line) |

Full contract: [`DATA_CONTRACT.md`](DATA_CONTRACT.md)

---

## 4. Directory Reference

```
career-ops/
├── pyproject.toml          # uv workspace root (no code — declares members)
├── packages/
│   ├── core/               # career-ops-core: shared business logic
│   │   └── career_ops_core/
│   │       ├── config.py                  # ProjectConfig — all path resolution
│   │       ├── data/                      # Pure parsers/writers (no I/O side effects)
│   │       │   ├── applications.py        # ApplicationRow, parse_applications(), write_applications()
│   │       │   ├── states.py              # CANONICAL_STATUSES, ALIASES, normalize_status()
│   │       │   ├── normalize.py           # ROLE_STOPWORDS, role_fuzzy_match()
│   │       │   ├── pipeline_md.py         # pipeline.md reader/writer
│   │       │   └── scan_history.py        # scan-history.tsv reader/writer
│   │       ├── scripts/                   # Business logic (1:1 port of .mjs scripts)
│   │       │   ├── merge_tracker.py       # merge() + _detect_column_order()
│   │       │   ├── normalize_statuses.py
│   │       │   ├── dedup_tracker.py
│   │       │   └── verify_pipeline.py
│   │       └── providers/                 # Portal scanner backends (Phase 2)
│   ├── cli/                # career-ops-cli: Typer CLI (depends on core)
│   │   └── career_ops_cli/main.py         # Typer app — all commands + --root global flag
│   └── api/                # career-ops-api: FastAPI server (Phase 3)
├── modes/                  # Mode files (system layer)
│   ├── _shared.md          # Scoring engine — read on every evaluation
│   ├── _profile.md         # User archetypes — GITIGNORED (user layer)
│   ├── _profile.template.md # Template to bootstrap _profile.md
│   ├── oferta.md           # Single-offer evaluation (blocks A–G)
│   ├── ofertas.md          # Multi-offer comparison
│   ├── auto-pipeline.md    # Auto-detect mode when JD is pasted
│   ├── pdf.md              # CV PDF generation
│   ├── scan.md             # Portal scanner instructions
│   ├── batch.md            # Batch processing instructions
│   ├── apply.md            # Application form assistant
│   ├── contacto.md         # LinkedIn outreach (recruiter/HM/peer)
│   ├── deep.md             # Company research
│   ├── tracker.md          # Tracker query/update
│   ├── pipeline.md         # Process pending URLs
│   ├── patterns.md         # Rejection pattern analysis
│   ├── followup.md         # Follow-up cadence
│   ├── interview-prep.md   # Interview preparation
│   ├── training.md         # Course/cert evaluation
│   ├── project.md          # Portfolio project evaluation
│   ├── latex.md            # LaTeX CV export
│   ├── de/                 # German (DACH market)
│   ├── fr/                 # French (FR/BE/CH/LU)
│   ├── ja/                 # Japanese
│   ├── pt/                 # Portuguese
│   ├── ru/                 # Russian
│   └── tr/                 # Turkish
├── providers/              # Portal scanner backends
│   ├── _http.mjs           # Shared HTTP utilities (timeout, UA spoofing)
│   ├── _types.js           # TypeScript-style JSDoc type definitions
│   ├── greenhouse.mjs      # Greenhouse job-boards API
│   ├── lever.mjs           # Lever jobs API
│   └── ashby.mjs           # Ashby careers page scraper → API
├── templates/
│   ├── cv-template.html    # HTML CV template (Playwright → PDF)
│   ├── cv-template.tex     # LaTeX CV template (tectonic/pdflatex)
│   ├── portals.example.yml # 45+ pre-configured companies
│   └── states.yml          # Canonical application status definitions
├── dashboard/              # Go TUI (Bubble Tea)
│   ├── main.go
│   ├── go.mod / go.sum
│   └── internal/
│       ├── data/           # applications.md parser + metrics
│       ├── model/          # Domain types (Application, Metrics)
│       ├── theme/          # Catppuccin Mocha / Latte themes
│       └── ui/screens/     # Pipeline, Viewer, Progress screens
├── batch/
│   ├── batch-runner.sh     # Parallel worker orchestrator
│   ├── batch-prompt.md     # Self-contained headless worker prompt
│   ├── tracker-additions/  # Per-evaluation TSV files (pre-merge)
│   │   └── merged/         # Archived after merge-tracker.mjs
│   └── logs/               # Per-worker log files
├── config/
│   ├── profile.example.yml # Copy → profile.yml and fill in
│   └── profile.yml         # GITIGNORED (user layer)
├── data/                   # GITIGNORED (user layer)
├── reports/                # GITIGNORED (user layer)
├── output/                 # GITIGNORED (user layer)
├── jds/                    # GITIGNORED (user layer)
├── interview-prep/         # GITIGNORED (user layer)
├── writing-samples/        # GITIGNORED (user layer, except README.md)
├── tests/
│   └── robot/              # Robot Framework black-box tests (64 tests)
│       ├── pyproject.toml  # uv-managed Python env (robotframework>=7.0)
│       ├── resources/
│       │   ├── common.resource      # Shared keywords + workspace isolation
│       │   ├── liveness_wrapper.mjs # CLI shim for classifyLiveness()
│       │   └── fixtures/            # Fixture data files (.md, .tsv)
│       └── *.robot                  # Test suites (01–06)
├── docs/                   # User-facing documentation
│   ├── ARCHITECTURE.md     # High-level architecture overview
│   ├── SCRIPTS.md          # Full script reference
│   ├── SETUP.md            # Quick-start guide
│   └── CUSTOMIZATION.md    # Profile and mode customisation guide
└── fonts/                  # Self-hosted web fonts (Inter, JetBrains Mono)
```

---

## 5. Script Reference

All scripts live in the project root as ESM modules. They resolve data paths via `dirname(import.meta.url)` — always relative to the script file, not the working directory. All scripts handle missing files gracefully (`existsSync` before `readFileSync`).

### Pipeline scripts

| Script | `npm run` alias | Flags | Exit codes |
|--------|----------------|-------|------------|
| `merge-tracker.mjs` | `merge` | `--dry-run` `--verify` | `0` success / `1` verify failed |
| `normalize-statuses.mjs` | `normalize` | `--dry-run` | `0` always |
| `dedup-tracker.mjs` | `dedup` | `--dry-run` | `0` always |
| `verify-pipeline.mjs` | `verify` | — | `0` clean / `1` errors |

### Generation scripts

| Script | `npm run` alias | Args | Output |
|--------|----------------|------|--------|
| `generate-pdf.mjs` | `pdf` | `<input.html> <output.pdf> [--format=letter\|a4]` | `output/*.pdf` |
| `generate-latex.mjs` | — | `<input.tex> [output.pdf]` | compiled PDF via tectonic/pdflatex |

### Scanner and liveness

| Script | `npm run` alias | Flags | Notes |
|--------|----------------|-------|-------|
| `scan.mjs` | `scan` | `--dry-run` `--company <name>` | Appends to `data/pipeline.md` and `data/scan-history.tsv` |
| `check-liveness.mjs` | `liveness` | `<url…>` or `--file <file>` | Uses Playwright; exit `0` all active, `1` any expired |
| `liveness-core.mjs` | — | (library export) | `classifyLiveness({status, finalUrl, bodyText, applyControls})` → `{result, reason}` |

### Analysis scripts

| Script | `npm run` alias | Flags | Output |
|--------|----------------|-------|--------|
| `analyze-patterns.mjs` | — | `--summary` `--min-threshold N` | JSON or human-readable table to stdout |
| `followup-cadence.mjs` | — | `--summary` `--overdue-only` `--applied-days N` | JSON or markdown table to stdout |
| `gemini-eval.mjs` | `gemini:eval` | `"<JD text>"` or `--file <path>` | Evaluation report to stdout; requires `GEMINI_API_KEY` |

### Setup and maintenance

| Script | `npm run` alias | Notes |
|--------|----------------|-------|
| `doctor.mjs` | `doctor` | Node >= 18, Playwright, required files; auto-creates `data/output/reports/` |
| `cv-sync-check.mjs` | `sync-check` | Validates `cv.md` + `config/profile.yml` consistency |
| `update-system.mjs check` | `update:check` | JSON output: `up-to-date` / `update-available` / `dismissed` / `offline` |
| `update-system.mjs apply` | `update` | Fetches system-layer files; creates `backup-pre-update-{version}` branch |
| `update-system.mjs rollback` | `rollback` | Restores from backup branch |
| `update-system.mjs dismiss` | — | Suppresses update nag for current version |
| `test-all.mjs` | — | `--quick` skips Go build; exit `0` pass / `1` fail |

---

## 6. Mode System

The agent selects a mode file based on user intent. Each mode file is a plain-English instruction document that tells the agent what to do and in what sequence.

```
User message
     │
     ▼
Auto-pipeline (auto-pipeline.md)
  detects intent and routes to:
     │
     ├─ JD pasted/URL → oferta.md (evaluation + report + PDF + tracker)
     ├─ "scan portals" → scan.md
     ├─ "compare offers" → ofertas.md
     ├─ "outreach" → contacto.md
     ├─ "research company" → deep.md
     ├─ "interview prep" → interview-prep.md
     ├─ "generate CV/PDF" → pdf.md / latex.md
     ├─ "tracker status" → tracker.md
     ├─ "patterns" → patterns.md
     ├─ "follow-up" → followup.md
     ├─ "batch" → batch.md
     └─ "training/cert" → training.md
```

### Mode file anatomy

Each mode `.md` file contains:
- **Trigger conditions** — when to enter this mode
- **Step sequence** — ordered instructions for the agent
- **Output spec** — exact format of reports, tables, filenames
- **Edge cases** — how to handle ambiguous input

`_shared.md` is always in scope and defines the scoring engine, archetype table, tool config, and global rules. `_profile.md` (user layer) extends and overrides `_shared.md` with personal archetypes and framing.

---

## 7. Language Variants

| Directory | Market | Modes included |
|-----------|--------|----------------|
| `modes/de/` | DACH (DE/AT/CH) | `_shared.md`, `angebot.md`, `bewerben.md`, `pipeline.md` |
| `modes/fr/` | FR/BE/CH/LU | `_shared.md`, `offre.md`, `postuler.md`, `pipeline.md` |
| `modes/ja/` | Japan | `_shared.md`, `kyujin.md`, `oubo.md`, `pipeline.md` |
| `modes/pt/` | PT/BR | `_shared.md`, `oferta.md`, `aplicar.md`, `pipeline.md` |
| `modes/ru/` | Russia/CIS | `_shared.md`, `oferta.md`, `apply.md`, `interview-prep.md`, `pipeline.md` |
| `modes/tr/` | Turkey | `_shared.md`, `is-ilani.md`, `basvuru.md`, `pipeline.md` |

**Selection logic** (in order of precedence):
1. `language.modes_dir` set in `config/profile.yml` → always use that directory
2. User explicitly says "use German/French/… modes" in conversation
3. JD language detected → suggest switching; use English unless confirmed
4. Default: `modes/` (English)

---

## 8. Evaluation Pipeline

### Single-offer flow

```
1. Input          User pastes JD text or URL
2. Verify         Playwright → browser_navigate + browser_snapshot
                  (confirms posting is still live — NEVER WebFetch for this)
3. Classify       Detect archetype from modes/_profile.md archetype table
4. Evaluate       6 blocks:
                  A — Role summary (title, company, type, location, comp)
                  B — CV match (strengths, gaps, mitigation)
                  C — Level strategy (positioning advice)
                  D — Comp research (WebSearch → market range)
                  E — CV personalisation plan (tailored bullet suggestions)
                  F — Interview prep (3–5 STAR+R stories)
5. Score          Weighted average across 10 dimensions (1.0–5.0)
6. Block G        Posting legitimacy assessment (tier I–IV)
7. Save report    reports/{###}-{company-slug}-{YYYY-MM-DD}.md
                  Header: Score · URL · Legitimacy · PDF
8. Generate PDF   generate-pdf.mjs → templates/cv-template.html → Playwright
                  output/cv-{candidate}-{slug}-{date}.pdf
9. Track          Write 9-col TSV to batch/tracker-additions/{num}-{slug}.tsv
10. Merge         merge-tracker.mjs → data/applications.md
```

### Report numbering

Reports use sequential 3-digit zero-padded numbers (`001`, `002`, …). Always `max(existing) + 1`. Never reuse numbers. Check `reports/` directory and `data/applications.md` to find the current max.

### Score dimensions

Evaluations score across 10 weighted dimensions (defined in `modes/_shared.md`). Profiles in `modes/_profile.md` can override weights. A score ≥ 4.0 is strong; < 4.0 should not be applied to without a specific reason.

---

## 9. Batch Processing

```
batch-input.tsv        batch-runner.sh          headless CLI workers
(id, url, source,  →   reads input,         →   N in parallel
 notes)                manages state                │
                        batch-state.tsv            ├── report .md
                        (pending /                 ├── PDF
                         processing /              └── tracker TSV
                         completed /
                         failed)
                                │
                        merge-tracker.mjs
                                │
                        data/applications.md
```

Workers are spawned via the appropriate CLI command for the active agent runtime:

| CLI | Command |
|-----|---------|
| Claude Code | `claude -p "prompt"` |
| Gemini CLI | `gemini -p "prompt"` |
| Codex | `codex exec "prompt"` |
| OpenCode | `opencode run "prompt"` |
| Qwen | `qwen -p "prompt"` |

Each worker is completely self-contained: it receives a bundled `batch-prompt.md` containing the full system prompt, the specific URL, and the report number. Workers cannot share state; the orchestrator tracks progress in `batch-state.tsv`.

**`--model` flag:** `batch-runner.sh` accepts `--model <name>` to override the default model per worker invocation.
**`--min-score` flag:** skips report/PDF generation for offers below the threshold.

---

## 10. Dashboard (Go TUI)

A standalone terminal UI built with [Bubble Tea](https://github.com/charmbracelet/bubbletea). No server, no database — reads `data/applications.md` directly.

```bash
cd dashboard && go build -o career-dashboard .
./career-dashboard --path ..    # point at project root
```

**Screens:**
- **Pipeline** — filterable/sortable application list
  - Tabs: All · Evaluated · Applied · Interview · Top ≥4 · SKIP
  - Sort: Score · Date · Company · Status
  - Grouped (by status) or flat view
- **Viewer** — inline report preview (lazy-loaded from `reports/`)
- **Progress** — analytics (funnel, stage counts, conversion rates)

**Themes:** Catppuccin Mocha (dark, default) and Catppuccin Latte (light, auto-detected from terminal background).

**Keyboard shortcuts:** `Tab` cycle filters · `s` sort · `g` toggle grouped · `r` refresh · `Enter` open viewer · `q` quit.

**Data contract:** The parser reads the pipe-delimited markdown table. Column order is `# | Date | Company | Role | Score | Status | PDF | Report | Notes` — the `Score` column always comes before `Status`. Do not reorder columns.

---

## 11. Update System

`update-system.mjs` provides safe, non-destructive system updates.

### Safety model

1. Before applying, creates git branch `backup-pre-update-{version}` containing the current state of all system files.
2. Applies update by writing only paths listed in `SYSTEM_PATHS` (defined inside the script).
3. Validates that no user-layer paths were touched. If a safety violation is detected, reverts the write and releases the lock.
4. Uses a `.update-lock` file to prevent concurrent runs.

### Commands

```bash
node update-system.mjs check    # JSON output, never modifies anything
node update-system.mjs apply    # Downloads and applies latest release
node update-system.mjs rollback # Restores from backup branch
node update-system.mjs dismiss  # Suppresses update prompt for current version
```

### Version check in AGENTS.md

On session start the agent silently runs `node update-system.mjs check`. Outcomes:
- `update-available` → prompt user to update
- `up-to-date` / `dismissed` / `offline` / `no-remote-version` → silent

---

## 12. Provider Layer

`scan.mjs` uses pluggable provider modules in `providers/` to query job boards without an LLM.

```
portals.yml (careers_url)
       │
       ▼
scan.mjs → detect provider by URL pattern
       │
       ├─ greenhouse.io → providers/greenhouse.mjs → job-boards API
       ├─ lever.com     → providers/lever.mjs      → Lever JSON API
       ├─ ashby.com     → providers/ashby.mjs      → Ashby HTML scrape → API
       └─ (unknown)     → skip, log warning
```

All providers return `[{title, url, company, location}]`. `providers/_http.mjs` provides shared fetch utilities with timeout and User-Agent spoofing. `providers/_types.js` contains JSDoc type annotations.

**Security:** Greenhouse URLs are validated against an allowlist to prevent SSRF (#602).

**Dedup:** `data/scan-history.tsv` tracks seen URLs. The scanner skips URLs already present in `data/applications.md` or the scan history.

**`--dry-run`:** Runs all fetches and computes new offers but writes nothing to disk. Useful for auditing without side effects.

---

## 13. Test Infrastructure

### Node.js test suite (`test-all.mjs`)

```bash
node test-all.mjs           # full suite (63+ checks)
node test-all.mjs --quick   # skip Go dashboard build
```

10 categories: syntax, script execution, liveness classification, dashboard build, data contract, user-file gitignore, personal data leak, absolute path, mode file integrity, AGENTS.md and VERSION.

CI: GitHub Actions runs `test-all.mjs --quick` on every PR. Dashboard build only runs on direct pushes to `main`.

### Go tests (`dashboard/`)

```bash
cd dashboard && go test ./...
```

Unit tests for `data.ParseApplications`, pipeline screen, viewer screen.

### Robot Framework black-box tests (`tests/robot/`)

```bash
cd tests/robot
uv run robot .              # run all 64 tests
uv run robot 01_smoke.robot # run one suite
```

64 characterization tests across 6 suites:

| Suite | Target | Description |
|-------|--------|-------------|
| `01_smoke.robot` | All `.mjs` | `node --check` syntax + graceful exit with no user data |
| `02_merge_tracker.robot` | `merge-tracker.mjs` | No-op, append, TSV archival, `--dry-run`, alias normalization |
| `03_normalize_statuses.robot` | `normalize-statuses.mjs` | Bold strip, alias map, date removal, `--dry-run` |
| `04_dedup_tracker.robot` | `dedup-tracker.mjs` | Score-based dedup, backup creation, `--dry-run` |
| `05_verify_pipeline.robot` | `verify-pipeline.mjs` | Each error condition exits 1; warnings exit 0 |
| `06_liveness_core.robot` | `liveness-core.mjs` | expired/active/uncertain pattern matching |

**Isolation:** each test copies all scripts and system files to a fresh temp directory (scripts use `import.meta.url` for paths, so copying provides full filesystem isolation).

**Dependency management:** `uv` + `pyproject.toml` in `tests/robot/` (no system Python required).

---

## 14. Data Formats

### applications.md (tracker table)

```markdown
| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
|---|------|---------|------|-------|--------|-----|--------|-------|
| 42 | 2026-05-19 | Acme Corp | ML Engineer | 4.3/5 | Applied | ✅ | [42](reports/042-acme-corp-2026-05-19.md) | Strong fit |
```

Column order is fixed: `Score` comes before `Status`. Scripts parse by column index; do not reorder.

### Tracker addition TSV (pre-merge)

9 tab-separated columns — note **Status comes before Score** in TSV (merge script handles the swap):

```
{num}\t{date}\t{company}\t{role}\t{status}\t{score}/5\t{pdf_emoji}\t[{num}](reports/{...}.md)\t{notes}
```

### Canonical statuses (`templates/states.yml`)

| Label | Aliases |
|-------|---------|
| `Evaluated` | evaluada, condicional, hold, evaluar, verificar |
| `Applied` | aplicado, enviada, aplicada, applied, sent |
| `Responded` | respondido |
| `Interview` | entrevista |
| `Offer` | oferta |
| `Rejected` | rechazado, rechazada |
| `Discarded` | descartado, descartada, cerrada, cancelada |
| `SKIP` | no aplicar, no_aplicar, skip, monitor |

**Rules:** no markdown bold, no dates, no extra text in the status cell. Use the notes column for context.

### scan-history.tsv

7 tab-separated columns:
```
url\tfirst_seen\tportal\ttitle\tcompany\tstatus\tlocation
```

---

## 15. Security Notes

- **Never submit applications automatically.** The `apply.md` mode fills forms and prepares drafts but always stops before clicking Submit. The user makes the final call.
- **SSRF protection:** `providers/greenhouse.mjs` validates the `careers_url` hostname against an allowlist before making HTTP requests.
- **No secrets in system layer.** `config/profile.yml` (gitignored) holds personal data. System files contain no PII. `test-all.mjs` runs a `git grep` scan to enforce this.
- **API key hygiene:** `gemini-eval.mjs` redacts the `GEMINI_API_KEY` from error logs.
- **Update integrity:** `update-system.mjs` only writes paths in `SYSTEM_PATHS`; a safety check fires if any user-layer path is touched.
- **Private vulnerability reporting:** see [`SECURITY.md`](SECURITY.md).

---

*For user-facing documentation, setup guides, and customization walkthroughs, see [`docs/`](docs/).*
*For data layer details, see [`DATA_CONTRACT.md`](DATA_CONTRACT.md).*
*For contribution guidelines, see [`CONTRIBUTING.md`](CONTRIBUTING.md).*
