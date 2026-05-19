*** Settings ***
Documentation    Smoke tests: syntax validity and graceful behavior with no user data.
...              These tests run against the real project scripts via node --check (no execution)
...              and against isolated workspaces to verify scripts don't crash on missing data.
Resource         resources/common.resource

Suite Setup      Suite Setup
Suite Teardown   Remove Test Workspace    ${WS}

*** Variables ***
${WS}    ${EMPTY}

*** Keywords ***
Suite Setup
    ${ws}=    New Test Workspace
    Set Suite Variable    ${WS}    ${ws}

*** Test Cases ***
# ── Syntax checks (node --check reads the file without executing it) ──────────

Syntax - normalize-statuses.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/normalize-statuses.mjs
    Script Should Exit 0    ${r}

Syntax - merge-tracker.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/merge-tracker.mjs
    Script Should Exit 0    ${r}

Syntax - dedup-tracker.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/dedup-tracker.mjs
    Script Should Exit 0    ${r}

Syntax - verify-pipeline.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/verify-pipeline.mjs
    Script Should Exit 0    ${r}

Syntax - liveness-core.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/liveness-core.mjs
    Script Should Exit 0    ${r}

Syntax - scan.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/scan.mjs
    Script Should Exit 0    ${r}

Syntax - check-liveness.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/check-liveness.mjs
    Script Should Exit 0    ${r}

Syntax - analyze-patterns.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/analyze-patterns.mjs
    Script Should Exit 0    ${r}

Syntax - followup-cadence.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/followup-cadence.mjs
    Script Should Exit 0    ${r}

Syntax - update-system.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/update-system.mjs
    Script Should Exit 0    ${r}

Syntax - doctor.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/doctor.mjs
    Script Should Exit 0    ${r}

Syntax - cv-sync-check.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/cv-sync-check.mjs
    Script Should Exit 0    ${r}

Syntax - generate-pdf.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/generate-pdf.mjs
    Script Should Exit 0    ${r}

Syntax - generate-latex.mjs
    ${r}=    Run Process    ${NODE}    --check    ${PROJECT_ROOT}/generate-latex.mjs
    Script Should Exit 0    ${r}

# ── Graceful behavior with no user data ──────────────────────────────────────

Graceful - normalize-statuses exits 0 with no applications.md
    # Workspace has no data/applications.md — script should report nothing to do
    ${r}=    Run Script    ${WS}    normalize-statuses.mjs
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to normalize

Graceful - merge-tracker exits 0 with no TSV files
    # Workspace has empty batch/tracker-additions/ — nothing to merge
    ${r}=    Run Script    ${WS}    merge-tracker.mjs
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No pending additions

Graceful - dedup-tracker exits 0 with no applications.md
    ${r}=    Run Script    ${WS}    dedup-tracker.mjs
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to dedup

Graceful - verify-pipeline exits 0 with no applications.md
    ${r}=    Run Script    ${WS}    verify-pipeline.mjs
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No applications.md found

Graceful - update-system check exits without crashing
    # Exits 0 regardless of network state (up-to-date / offline / dismissed)
    ${r}=    Run Script    ${WS}    update-system.mjs    check
    # rc is 0 for all non-error outcomes; only crash = unexpected
    Should Not Contain    ${r.stderr}    SyntaxError
    Should Not Contain    ${r.stderr}    TypeError
    Should Not Contain    ${r.stderr}    ReferenceError
