*** Settings ***
Documentation    Black-box characterization tests for verify-pipeline.mjs.
...
...    Verifies the seven health checks: canonical statuses, duplicates, report
...    links, score format, row format, pending TSVs, and bold in scores.
...    Exit code contract: 0 = clean or warnings-only, 1 = at least one error.
Resource         resources/common.resource

*** Keywords ***
Run Verify
    [Arguments]    ${ws}
    ${r}=    Run Script    ${ws}    verify-pipeline.mjs
    RETURN    ${r}

*** Test Cases ***
No applications.md — exits 0 with fresh-setup message
    [Documentation]    Missing tracker is normal for a new setup; script reports
    ...                it gracefully and exits 0.
    ${ws}=    New Test Workspace
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No applications.md found
    [Teardown]    Remove Test Workspace    ${ws}

Empty tracker — all checks pass, exits 0
    [Documentation]    A header-only tracker has nothing to check; all checks
    ...                must report OK and the exit code must be 0.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_empty.md    data/applications.md
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Pipeline is clean
    [Teardown]    Remove Test Workspace    ${ws}

Canonical statuses, no report links — exits 0
    [Documentation]    Entries with correct statuses and empty report cells pass
    ...                all checks.  Missing report cell is not an error because
    ...                the script only validates links that contain a markdown URL.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_canonical.md    data/applications.md
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    All statuses are canonical
    [Teardown]    Remove Test Workspace    ${ws}

Non-canonical status — exits 1 with error message
    [Documentation]    A tracker containing a completely unrecognised status (not
    ...                canonical and not an alias) must cause exit 1.
    ${ws}=    New Test Workspace
    # Write a tracker with one row that has a genuinely unknown status
    ${bad_tracker}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | 3.0/5 | UNKNOWN_STATUS | | | |
    Create File    ${ws}/data/applications.md    ${bad_tracker}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit Non-Zero    ${r}
    Should Contain    ${r.stdout}    ❌
    [Teardown]    Remove Test Workspace    ${ws}

Bold in status — exits 1 with error for bold marker
    [Documentation]    A status cell containing markdown bold (**) is an error.
    ${ws}=    New Test Workspace
    ${bold_tracker}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | 3.0/5 | **Applied** | | | |
    Create File    ${ws}/data/applications.md    ${bold_tracker}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit Non-Zero    ${r}
    Should Contain    ${r.stdout}    markdown bold
    [Teardown]    Remove Test Workspace    ${ws}

Date in status — exits 1 with error
    [Documentation]    A status cell containing a date string (YYYY-MM-DD) is an
    ...                error; dates belong in the date column.
    ${ws}=    New Test Workspace
    ${dated_tracker}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | 3.0/5 | Applied 2026-01-10 | | | |
    Create File    ${ws}/data/applications.md    ${dated_tracker}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit Non-Zero    ${r}
    Should Contain    ${r.stdout}    Status contains date
    [Teardown]    Remove Test Workspace    ${ws}

Invalid score format — exits 1 with error
    [Documentation]    A score that doesn't match X/5 or X.X/5 must be flagged.
    ${ws}=    New Test Workspace
    ${bad_score}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | excellent | Applied | | | |
    Create File    ${ws}/data/applications.md    ${bad_score}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit Non-Zero    ${r}
    Should Contain    ${r.stdout}    Invalid score format
    [Teardown]    Remove Test Workspace    ${ws}

Valid report link pointing to existing file — no error
    [Documentation]    A report link that resolves to an existing file must pass
    ...                the report-link check.
    ${ws}=    New Test Workspace
    Create File    ${ws}/reports/001-fooco-2026-05-19.md    # Report stub
    ${with_report}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | 3.5/5 | Applied | | [1](reports/001-fooco-2026-05-19.md) | |
    Create File    ${ws}/data/applications.md    ${with_report}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    All report links valid
    [Teardown]    Remove Test Workspace    ${ws}

Report link pointing to missing file — exits 1
    [Documentation]    A markdown report link whose target file does not exist must
    ...                trigger an error and exit 1.
    ${ws}=    New Test Workspace
    ${missing_report}=    Catenate    SEPARATOR=\n
    ...    \# Applications Tracker
    ...    ${EMPTY}
    ...    | \# | Date | Company | Role | Score | Status | PDF | Report | Notes |
    ...    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    ...    | 1 | 2026-05-19 | FooCo | Engineer | 3.5/5 | Applied | | [1](reports/001-missing.md) | |
    Create File    ${ws}/data/applications.md    ${missing_report}\n
    ${r}=    Run Verify    ${ws}
    Script Should Exit Non-Zero    ${r}
    Should Contain    ${r.stdout}    Report not found
    [Teardown]    Remove Test Workspace    ${ws}

Duplicate entries — exits 0 with warning (not error)
    [Documentation]    Duplicates in the tracker are warnings, not hard errors,
    ...                so exit code must be 0.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_with_dups.md    data/applications.md
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    ⚠️
    [Teardown]    Remove Test Workspace    ${ws}

Pending TSV in tracker-additions — exits 0 with warning
    [Documentation]    Un-merged TSVs are a warning, not an error; exit code
    ...                must be 0 but stdout must mention the pending file.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_canonical.md    data/applications.md
    Install Fixture    ${ws}    tracker_valid.tsv    batch/tracker-additions/010-testco.tsv
    ${r}=    Run Verify    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    pending TSVs
    [Teardown]    Remove Test Workspace    ${ws}
