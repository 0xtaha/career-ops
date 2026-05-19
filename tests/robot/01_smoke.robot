*** Settings ***
Documentation    Smoke tests: importability and graceful behavior with no user data.
...              These tests verify each Python module imports without error
...              and that CLI commands exit cleanly on a fresh (empty) workspace.
Resource         resources/common.resource

Suite Setup      Suite Setup
Suite Teardown   Remove Test Workspace    ${WS}

*** Variables ***
${WS}    ${EMPTY}

*** Keywords ***
Suite Setup
    ${ws}=    New Test Workspace
    Set Suite Variable    ${WS}    ${ws}

Import Should Succeed
    [Arguments]    ${module}
    ${r}=    Run Process    ${PYTHON}    -c    import ${module}
    ...    stdout=PIPE    stderr=PIPE
    Should Be Equal As Integers    ${r.rc}    0
    ...    msg=Import failed for ${module}\nSTDERR:\n${r.stderr}

*** Test Cases ***
# ── Module import checks (replace node --check) ──────────────────────────────

Import - career_ops_core.scripts.normalize_statuses
    Import Should Succeed    career_ops_core.scripts.normalize_statuses

Import - career_ops_core.scripts.merge_tracker
    Import Should Succeed    career_ops_core.scripts.merge_tracker

Import - career_ops_core.scripts.dedup_tracker
    Import Should Succeed    career_ops_core.scripts.dedup_tracker

Import - career_ops_core.scripts.verify_pipeline
    Import Should Succeed    career_ops_core.scripts.verify_pipeline

Import - career_ops_core.scripts.liveness_core
    Import Should Succeed    career_ops_core.scripts.liveness_core

Import - career_ops_core.scripts.scan
    Import Should Succeed    career_ops_core.scripts.scan

Import - career_ops_core.scripts.check_liveness
    Import Should Succeed    career_ops_core.scripts.check_liveness

Import - career_ops_core.scripts.analyze_patterns
    Import Should Succeed    career_ops_core.scripts.analyze_patterns

Import - career_ops_core.scripts.followup_cadence
    Import Should Succeed    career_ops_core.scripts.followup_cadence

Import - career_ops_core.scripts.update_system
    Import Should Succeed    career_ops_core.scripts.update_system

Import - career_ops_core.scripts.doctor
    Import Should Succeed    career_ops_core.scripts.doctor

Import - career_ops_core.scripts.cv_sync_check
    Import Should Succeed    career_ops_core.scripts.cv_sync_check

Import - career_ops_core.scripts.generate_pdf
    Import Should Succeed    career_ops_core.scripts.generate_pdf

# ── Graceful behavior with no user data ──────────────────────────────────────

Graceful - normalize exits 0 with no applications.md
    # Workspace has no data/applications.md — command should report nothing to do
    ${r}=    Run Script    ${WS}    normalize
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to normalize

Graceful - merge exits 0 with no TSV files
    # Workspace has empty batch/tracker-additions/ — nothing to merge
    ${r}=    Run Script    ${WS}    merge
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No pending additions

Graceful - dedup exits 0 with no applications.md
    ${r}=    Run Script    ${WS}    dedup
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to dedup

Graceful - verify exits 0 with no applications.md
    ${r}=    Run Script    ${WS}    verify
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No applications.md found

Graceful - update check exits without crashing
    # Exits 0 regardless of network state (up-to-date / offline / dismissed)
    ${r}=    Run Script    ${WS}    update    check
    Should Not Contain    ${r.stderr}    Traceback
    Should Not Contain    ${r.stderr}    ImportError
