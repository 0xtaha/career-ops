# Migration Plan: career-ops → Python (core + cli + api) + React

## Context

career-ops currently runs on 14 Node.js .mjs scripts, a Go TUI dashboard, and a Robot Framework test suite (already Python). The goal is to:
- Replace all .mjs scripts with a **uv workspace** of three separate Python packages:
  - `packages/core/` — shared business logic, used by both CLI and API
  - `packages/cli/` — Typer-based CLI, depends on core
  - `packages/api/` — FastAPI server, depends on core
- Replace the Go TUI with a React web dashboard (Vite + TypeScript + TanStack Query + Tailwind)
- Keep `modes/*.md` AI prompt files completely unchanged

**User decisions:** Full .mjs replacement (no JS retained), Go dashboard removed, JWT/OAuth auth, Vite + React + TypeScript.

---

## New Directory Structure

```
career-ops/
├── pyproject.toml                      # uv workspace root (no code)
├── packages/
│   ├── core/                           # Package: career-ops-core
│   │   ├── pyproject.toml
│   │   └── career_ops_core/
│   │       ├── __init__.py
│   │       ├── config.py               # ProjectConfig(root: Path) — all path resolution
│   │       ├── data/                   # Pure parsers/writers — zero business logic
│   │       │   ├── applications.py     # parse_applications(), write_applications(), ApplicationRow
│   │       │   ├── scan_history.py
│   │       │   ├── pipeline_md.py
│   │       │   ├── states.py           # load_states_yml(), CANONICAL_STATUSES, ALIASES
│   │       │   ├── portals.py
│   │       │   └── normalize.py        # normalize_role(), role_fuzzy_match(), ROLE_STOPWORDS, etc.
│   │       ├── scripts/                # Business logic — 1:1 port of each .mjs script
│   │       │   ├── merge_tracker.py    # merge() + _detect_column_order() heuristic
│   │       │   ├── normalize_statuses.py
│   │       │   ├── dedup_tracker.py
│   │       │   ├── verify_pipeline.py
│   │       │   ├── generate_pdf.py     # Playwright Python (asyncio)
│   │       │   ├── scan.py             # provider discovery via importlib
│   │       │   ├── liveness_core.py    # classify_liveness() — pure function, no I/O
│   │       │   ├── check_liveness.py   # Playwright runner
│   │       │   ├── analyze_patterns.py
│   │       │   ├── followup_cadence.py
│   │       │   ├── doctor.py
│   │       │   ├── cv_sync_check.py
│   │       │   ├── update_system.py    # SYSTEM_PATHS updated to Python/React paths
│   │       │   └── gemini_eval.py
│   │       └── providers/              # Portal scanner backends
│   │           ├── _types.py           # Provider ABC: id, detect(), fetch()
│   │           ├── _http.py            # httpx.AsyncClient, 10s timeout, UA spoofing
│   │           ├── greenhouse.py       # SSRF allowlist preserved
│   │           ├── lever.py
│   │           └── ashby.py
│   │
│   ├── cli/                            # Package: career-ops-cli
│   │   ├── pyproject.toml              # depends on career-ops-core
│   │   └── career_ops_cli/
│   │       ├── __init__.py
│   │       └── main.py                 # Typer app — all commands + --root global flag
│   │
│   └── api/                            # Package: career-ops-api
│       ├── pyproject.toml              # depends on career-ops-core
│       └── career_ops_api/
│           ├── __init__.py
│           ├── app.py                  # FastAPI instance, lifespan, CORS, static mount
│           ├── auth.py                 # JWT HS256, /api/auth/token endpoint
│           ├── deps.py                 # get_current_user(), get_project_config()
│           ├── models.py               # Pydantic: ApplicationRow, PipelineMetrics, etc.
│           └── routers/
│               ├── tracker.py          # GET /api/tracker, PATCH /api/tracker/{num}/status
│               ├── pipeline.py         # GET /api/pipeline, GET /api/pipeline/metrics
│               ├── scan.py             # POST /api/scan (bg task), GET /api/scan/stream (SSE)
│               ├── reports.py          # GET /api/reports, GET /api/reports/{path:path}
│               ├── liveness.py         # POST /api/liveness
│               ├── patterns.py         # GET /api/patterns
│               ├── followup.py         # GET /api/followup
│               └── pdf.py              # POST /api/pdf (bg task), GET /api/pdf/{task_id}
│
├── frontend/                           # Vite + React + TypeScript (replaces dashboard/)
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── src/
│       ├── api/
│       │   ├── client.ts               # axios instance, token injection, 401 redirect
│       │   └── queries.ts              # TanStack Query hooks for all routes
│       ├── auth/
│       │   ├── AuthContext.tsx
│       │   └── LoginPage.tsx
│       ├── pages/
│       │   ├── PipelinePage.tsx        # Replaces Go Pipeline screen
│       │   ├── ViewerPage.tsx          # Replaces Go Viewer screen (react-markdown)
│       │   └── ProgressPage.tsx        # Replaces Go Progress screen (recharts)
│       ├── components/
│       │   ├── ApplicationTable.tsx
│       │   ├── StatusBadge.tsx
│       │   ├── MetricsCards.tsx
│       │   ├── FunnelChart.tsx
│       │   └── ScanProgress.tsx        # SSE consumer + "Run Scan" button
│       └── types/api.ts                # TypeScript interfaces mirroring Pydantic models
│
├── tests/robot/                        # RF tests — kept, invocation updated
│   ├── pyproject.toml                  # robotframework + career-ops-cli as deps
│   ├── resources/
│   │   ├── common.resource             # Run Script → career-ops --root ${ws} {cmd}
│   │   ├── liveness_wrapper.py         # NEW: replaces liveness_wrapper.mjs
│   │   └── fixtures/                   # Unchanged — data files are language-agnostic
│   └── *.robot                         # Updated: node → career-ops CLI commands
│
# REMOVED in Phase 4:
# dashboard/, *.mjs, package.json (root), node_modules/, test-all.mjs
```

---

## uv Workspace pyproject.toml Files

**Root** `pyproject.toml` (workspace declaration, no package):
```toml
[tool.uv.workspace]
members = ["packages/core", "packages/cli", "packages/api"]
```

**`packages/core/pyproject.toml`:**
```toml
[project]
name = "career-ops-core"
version = "1.9.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "httpx>=0.27",
    "playwright>=1.44",
    "google-generativeai>=0.8",
    "python-dotenv>=1.0",
]
```

**`packages/cli/pyproject.toml`:**
```toml
[project]
name = "career-ops-cli"
version = "1.9.0"
requires-python = ">=3.12"
dependencies = [
    "career-ops-core",
    "typer>=0.12",
    "rich>=13.7",
]

[project.scripts]
career-ops = "career_ops_cli.main:app"
```

**`packages/api/pyproject.toml`:**
```toml
[project]
name = "career-ops-api"
version = "1.9.0"
requires-python = ">=3.12"
dependencies = [
    "career-ops-core",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.29",
    "pydantic-settings>=2.3",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "sse-starlette>=2.1",
]

[project.scripts]
career-ops-api = "career_ops_api.app:serve"
```

Running `uv sync` at the workspace root installs all three packages with their dependencies, with `career-ops-core` shared.

---

## Critical Data Compatibility Notes

### Column-swap heuristic (most fragile piece — port first)
TSV additions (`batch/tracker-additions/`) use column order: `num | date | company | role | Status | Score | pdf | report | notes`
`applications.md` uses: `# | Date | Company | Role | Score | Status | PDF | Report | Notes` — **Status and Score are swapped**.

`_detect_column_order(col4: str, col5: str) -> tuple[str, str]` must detect which column is score (matches `\d+\.?\d*\/5`, `N/A`, or `DUP`) and which is status. Lives in `career_ops_core/scripts/merge_tracker.py`. **Unit-test with real fixture data before moving on.**

### Role fuzzy match (`normalize_role` + `role_fuzzy_match`)
`ROLE_STOPWORDS`, `SHORT_SPECIALTY`, `BASELINE_TOKENS` are load-bearing constants in `merge-tracker.mjs`. Port as module-level `frozenset`s in `career_ops_core/data/normalize.py`. Issue #633 edge case: "Staff SWE API" vs "Staff SWE Kubernetes Platform" must **not** match.

### Markdown bold stripping
Status and score cells can contain `**bold**` from AI agent output. All parsers must strip `**` before comparison.

### Pipe-delimited row parsing
`line.strip().strip('|').split('|')` then strip each field. Minimum 8 fields required. Skip: empty lines, `# ` headings, `---` separators, header rows containing `Company` or `Empresa`.

### Score format
Valid: `X/5`, `X.X/5`, `X.XX/5`, `N/A`, `DUP`. Store `score_raw: str` and `score: float | None` in Pydantic models.

---

## JWT Auth Design

**Token endpoint:** `POST /api/auth/token` — OAuth2PasswordRequestForm → HS256 JWT (8h expiry default)  
**Secret:** `CAREER_OPS_JWT_SECRET` env var  
**Users:** `CAREER_OPS_USERNAME` + `CAREER_OPS_PASSWORD_HASH` env vars (bcrypt). Single admin — no DB needed.  
**All `/api/` routes** (except `/api/auth/token`) require `Authorization: Bearer <token>`.  
**React:** Token in `localStorage`. Axios interceptor injects header. On 401 → clear token, redirect to `/login`.

---

## 5-Tier URL Enrichment (replicate from Go dashboard, in `GET /api/tracker`)

1. Parse `**URL:**` from first 1000 bytes of the linked report file
2. `**Batch ID:**` in report header → lookup in `batch/batch-input.tsv` notes
3. Report number → `batch-state.tsv` completed rows
4. `scan-history.tsv` — company+title fuzzy match (strip Inc/LLC/Corp/etc. suffixes)
5. Fallback: `batch-input.tsv` company+role word-overlap scoring

This logic lives in `career_ops_core/data/applications.py` (pure function, no I/O beyond the file reads the router already did).

---

## FastAPI SSE Pattern (scan progress)

```python
# app.state.scan_queues: dict[str, asyncio.Queue]
# POST /api/scan  → creates queue, starts bg task, returns {"task_id": "..."}
# bg task         → puts {"type": "progress", "company": "...", "found": N} into queue
# GET /api/scan/stream?task_id=... → EventSourceResponse reading from queue
# cleanup         → queue removed when client disconnects (finally block in generator)
```

---

## Robot Framework Test Migration

**`common.resource` — key change to `Run Script`:**
```robotframework
Run Script
    [Arguments]    ${workspace}    ${command}    @{args}
    ${result}=    Run Process    career-ops    --root    ${workspace}
    ...    ${command}    @{args}    stdout=PIPE    stderr=PIPE
    RETURN    ${result}
```

**`New Test Workspace`:** No longer copies `.mjs` files. Creates standard dirs (`data/`, `batch/tracker-additions/merged/`, `output/`, `reports/`, `config/`), copies `templates/` and `modes/`. The installed `career-ops-cli` is used from the venv via `--root` flag.

**`liveness_wrapper.py`** (replaces `liveness_wrapper.mjs`):
```python
#!/usr/bin/env python3
import sys, json
from career_ops_core.scripts.liveness_core import classify_liveness
payload = json.loads(sys.argv[1])
result = classify_liveness(**payload)
print(json.dumps({"result": result.result, "reason": result.reason}))
```

**Per-suite command mapping:**

| Suite | Old | New |
|-------|-----|-----|
| 01 smoke | `node --check {script}.mjs` | `python -c "import career_ops_core.scripts.{module}"` |
| 02 merge | `node merge-tracker.mjs` | `career-ops merge` |
| 03 normalize | `node normalize-statuses.mjs` | `career-ops normalize` |
| 04 dedup | `node dedup-tracker.mjs` | `career-ops dedup` |
| 05 verify | `node verify-pipeline.mjs` | `career-ops verify` |
| 06 liveness | `node liveness_wrapper.mjs` | `python liveness_wrapper.py` |

---

## Phase Breakdown

### Phase 1 — Core Package + Data CLI Commands (Week 1)
**Deliverable:** uv workspace with `core` and `cli` packages; `merge`, `normalize`, `dedup`, `verify` commands work.

- Root `pyproject.toml` (workspace)
- `packages/core/pyproject.toml` + `career_ops_core/config.py`
- `career_ops_core/data/states.py` — load `templates/states.yml`
- `career_ops_core/data/normalize.py` — `ROLE_STOPWORDS`, `SHORT_SPECIALTY`, `BASELINE_TOKENS`, `normalize_role()`, `role_fuzzy_match()`
- `career_ops_core/data/applications.py` — full parser + writer with column-swap heuristic and 5-tier URL enrichment
- `career_ops_core/scripts/merge_tracker.py`, `normalize_statuses.py`, `dedup_tracker.py`, `verify_pipeline.py`
- `packages/cli/pyproject.toml` + `career_ops_cli/main.py` — Typer app, four commands + `--root` global option
- Update RF `common.resource` + suites 02–05 to call `career-ops` CLI

**Verification:** `uv run career-ops normalize --root /tmp/ws --dry-run` exits 0; RF suites 02–05 pass.

---

### Phase 2 — Remaining Scripts + Providers (Week 2)
**Deliverable:** All 14 script equivalents in core; CLI fully feature-complete.

- `career_ops_core/providers/_types.py`, `_http.py`, `greenhouse.py`, `lever.py`, `ashby.py`
- `career_ops_core/scripts/scan.py` — provider discovery via `importlib`
- `career_ops_core/scripts/liveness_core.py` — all regex patterns from `liveness-core.mjs`
- `career_ops_core/scripts/check_liveness.py` — `async_playwright()` runner
- `career_ops_core/scripts/generate_pdf.py` — Playwright Python + ATS text normalization
- `career_ops_core/scripts/analyze_patterns.py`, `followup_cadence.py`
- `career_ops_core/scripts/doctor.py` — checks Python/uv/playwright (not Node)
- `career_ops_core/scripts/cv_sync_check.py`, `update_system.py` (SYSTEM_PATHS → Python/React paths), `gemini_eval.py`
- Remaining CLI commands: `pdf`, `scan`, `liveness`, `patterns`, `followup`, `doctor`, `sync-check`, `update`, `gemini-eval`
- `tests/robot/resources/liveness_wrapper.py`; update RF suite 06

**Verification:** `uv run career-ops doctor` passes; `uv run career-ops scan --dry-run` exits 0; all RF suites pass.

---

### Phase 3 — FastAPI Server Package (Week 3)
**Deliverable:** REST API with JWT auth, background tasks, SSE. Verified via curl — no UI yet.

- `packages/api/pyproject.toml`
- `career_ops_api/models.py` — all Pydantic models (mirrors Go `CareerApplication`, `PipelineMetrics`, `ProgressMetrics`)
- `career_ops_api/auth.py` — JWT tokens, `/api/auth/token`
- `career_ops_api/deps.py` — FastAPI dependencies
- All routers in `career_ops_api/routers/`
- `career_ops_api/app.py` — lifespan (`scan_queues` dict), CORS (localhost:5173 + prod), static mount placeholder
- `career-ops-api` entry point: `uvicorn career_ops_api.app:app --port 8000`

**Verification:** Token endpoint returns JWT; all `/api/*` routes return 401 without token; tracker returns data; SSE stream works on scan.

---

### Phase 4 — React Frontend + Cleanup (Week 4)
**Deliverable:** Full web dashboard. All Node.js + Go code removed.

- `frontend/` — Vite + React + TypeScript scaffold
- `frontend/src/api/client.ts`, `queries.ts`
- Auth flow: `AuthContext.tsx`, `LoginPage.tsx`
- Pages: `PipelinePage.tsx`, `ViewerPage.tsx`, `ProgressPage.tsx`
- Components: table, status badge, recharts charts, SSE scan progress
- `frontend/src/types/api.ts` — TypeScript interfaces matching Pydantic models
- `vite build` → `frontend/dist/`; API mounts at `/`
- **Remove:** `dashboard/`, all `*.mjs`, root `package.json`, `node_modules/`, `test-all.mjs`
- Update `.gitignore`: remove Node/Go entries, add Python + frontend entries
- Update `ARCHITECTURE.md`, `CLAUDE.md`, `MEMORY.md` to reflect new stack

**Verification:** `career-ops-api` → browser at `http://localhost:8000` → login → pipeline → viewer → progress → scan with live SSE progress bar.

---

### Phase 5 — Test Hardening (runs in parallel with Phases 2–4)
**Deliverable:** All 64 RF tests passing; `test-all.mjs` removed.

- Update `tests/robot/pyproject.toml`: add `career-ops-cli` as workspace dep
- Migrate `01_smoke.robot` from `node --check` to Python import checks
- Confirm all 6 suites pass
- Remove `test-all.mjs`

---

## Dependency Graph

```
career-ops-core    (no internal deps)
     ├── career-ops-cli   (depends on core)
     └── career-ops-api   (depends on core)

frontend           (depends on API over HTTP only)
tests/robot        (depends on career-ops-cli)
```

---

## Phase Sequencing

```
Phase 1 (core data layer + 4 CLI commands)
    └── Phase 2 (remaining scripts + providers → full CLI)
            ├── Phase 3 (FastAPI — depends on all core scripts)
            │       └── Phase 4 (React — depends on stable API routes)
            └── Phase 5 (RF test migration — can start after Phase 1)
```

---

## Critical Files to Read Before Implementation

| File | Why |
|------|-----|
| [merge-tracker.mjs](merge-tracker.mjs) | Column-swap heuristic + role fuzzy match → `core/scripts/merge_tracker.py` + `core/data/normalize.py` |
| [dashboard/internal/data/career.go](dashboard/internal/data/career.go) | 5-tier URL enrichment + metrics computation → `core/data/applications.py` + API routers |
| [liveness-core.mjs](liveness-core.mjs) | All regex patterns → `core/scripts/liveness_core.py` |
| [tests/robot/resources/common.resource](tests/robot/resources/common.resource) | Test harness kernel — one change unlocks all 6 suites |
| [dashboard/internal/model/career.go](dashboard/internal/model/career.go) | Canonical types → Pydantic models + TypeScript interfaces |
| [scan.mjs](scan.mjs) + [providers/_http.mjs](providers/_http.mjs) | Provider loading pattern + HTTP utilities → `core/providers/` |
