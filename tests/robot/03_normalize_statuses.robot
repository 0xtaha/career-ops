*** Settings ***
Documentation    Black-box characterization tests for normalize-statuses.mjs.
...
...    Captures the canonicalization rules: markdown bold stripping, Spanish alias
...    mapping, date removal, and alias-to-English conversion. Each test uses an
...    isolated workspace so mutations never bleed between cases.
Resource         resources/common.resource

*** Keywords ***
Workspace With Noncanonical Tracker
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_noncanonical.md    data/applications.md
    RETURN    ${ws}

Run Normalize
    [Arguments]    ${ws}    @{extra_args}
    ${r}=    Run Script    ${ws}    normalize-statuses.mjs    @{extra_args}
    RETURN    ${r}

*** Test Cases ***
No applications.md — exits 0 with informational message
    [Documentation]    Missing tracker file is not an error; script should report
    ...                "Nothing to normalize" and exit cleanly.
    ${ws}=    New Test Workspace
    ${r}=    Run Normalize    ${ws}
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to normalize
    [Teardown]    Remove Test Workspace    ${ws}

Already-canonical statuses — file content unchanged
    [Documentation]    Running normalize on a clean tracker must be a no-op; the
    ...                file bytes must be identical before and after.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_canonical.md    data/applications.md
    ${before}=    Get Applications Content    ${ws}
    Run Normalize    ${ws}
    ${after}=    Get Applications Content    ${ws}
    Should Be Equal    ${before}    ${after}
    [Teardown]    Remove Test Workspace    ${ws}

Bold status stripped — **Applied** becomes Applied
    [Documentation]    Markdown bold markers around a canonical status must be
    ...                removed without changing the status value.
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    **Applied**
    Should Contain        ${content}    Applied
    [Teardown]    Remove Test Workspace    ${ws}

Spanish alias mapped — aplicado becomes Applied
    [Documentation]    The Spanish alias "aplicado" (entry #2 in fixture) must be
    ...                replaced with the English canonical "Applied".
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    aplicado
    Should Contain        ${content}    Applied
    [Teardown]    Remove Test Workspace    ${ws}

Date stripped from status — Rechazado 2026-01-25 becomes Rejected
    [Documentation]    Trailing dates in the status cell (entry #3) must be removed
    ...                and the alias mapped to the canonical English label.
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    Rechazado 2026-01-25
    Should Contain        ${content}    Rejected
    [Teardown]    Remove Test Workspace    ${ws}

cerrada mapped to Discarded
    [Documentation]    The alias "cerrada" (entry #4) must become "Discarded".
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    cerrada
    Should Contain        ${content}    Discarded
    [Teardown]    Remove Test Workspace    ${ws}

MONITOR mapped to SKIP
    [Documentation]    The alias "MONITOR" (entry #5) must become "SKIP".
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    MONITOR
    Should Contain        ${content}    SKIP
    [Teardown]    Remove Test Workspace    ${ws}

Dry-run — exits 0, file not modified
    [Documentation]    --dry-run must preview changes without writing any files.
    ${ws}=    Workspace With Noncanonical Tracker
    ${before}=    Get Applications Content    ${ws}
    ${r}=    Run Normalize    ${ws}    --dry-run
    Script Should Exit 0    ${r}
    ${after}=    Get Applications Content    ${ws}
    Should Be Equal    ${before}    ${after}
    [Teardown]    Remove Test Workspace    ${ws}

All five noncanonical entries normalized in a single run
    [Documentation]    Running normalize on the fixture with 5 bad entries must
    ...                produce a file where none of the original bad values remain.
    ${ws}=    Workspace With Noncanonical Tracker
    Run Normalize    ${ws}
    ${content}=    Get Applications Content    ${ws}
    Should Not Contain    ${content}    **Applied**
    Should Not Contain    ${content}    aplicado
    Should Not Contain    ${content}    Rechazado 2026-01-25
    Should Not Contain    ${content}    cerrada
    Should Not Contain    ${content}    MONITOR
    [Teardown]    Remove Test Workspace    ${ws}
