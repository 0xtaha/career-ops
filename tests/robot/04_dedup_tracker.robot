*** Settings ***
Documentation    Black-box characterization tests for dedup.
...
...    Verifies: graceful exit on missing data, no-op on clean trackers, removal
...    of the lower-scored duplicate, backup file creation, and --dry-run safety.
Resource         resources/common.resource

*** Keywords ***
Workspace With Dups
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_with_dups.md    data/applications.md
    RETURN    ${ws}

*** Test Cases ***
No applications.md — exits 0 with informational message
    [Documentation]    Missing tracker is not an error; script exits cleanly.
    ${ws}=    New Test Workspace
    ${r}=    Run Script    ${ws}    dedup
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    Nothing to dedup
    [Teardown]    Remove Test Workspace    ${ws}

No duplicates — exits 0, file content unchanged
    [Documentation]    A clean tracker with unique company+role pairs must not be
    ...                modified.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_canonical.md    data/applications.md
    ${before}=    Get File    ${ws}/data/applications.md
    ${r}=    Run Script    ${ws}    dedup
    Script Should Exit 0    ${r}
    ${after}=    Get File    ${ws}/data/applications.md
    Should Be Equal    ${before}    ${after}
    [Teardown]    Remove Test Workspace    ${ws}

Duplicate entries — lower-scored entry removed
    [Documentation]    The fixture has Acme Corp / Machine Learning Engineer twice
    ...                (scores 3.5/5 and 4.2/5).  The lower-scored entry (#1,
    ...                3.5/5) must be gone after dedup.
    ${ws}=    Workspace With Dups
    Run Script    ${ws}    dedup
    ${content}=    Get File    ${ws}/data/applications.md
    Should Not Contain    ${content}    3.5/5
    Should Contain        ${content}    4.2/5
    [Teardown]    Remove Test Workspace    ${ws}

Duplicate entries — unique entries untouched
    [Documentation]    Beta Labs / Data Analyst (entry #2) is not a duplicate and
    ...                must remain in the tracker after dedup.
    ${ws}=    Workspace With Dups
    Run Script    ${ws}    dedup
    ${content}=    Get File    ${ws}/data/applications.md
    Should Contain    ${content}    Beta Labs
    Should Contain    ${content}    Data Analyst
    [Teardown]    Remove Test Workspace    ${ws}

Backup file created alongside applications.md
    [Documentation]    The script creates a timestamped backup before rewriting the
    ...                tracker.  At least one .backup-* file must exist in data/.
    ${ws}=    Workspace With Dups
    Run Script    ${ws}    dedup
    @{backups}=    List Files In Directory    ${ws}/data    applications.md.backup-*
    Should Not Be Empty    ${backups}
    ...    msg=Expected at least one backup file in data/ after dedup
    [Teardown]    Remove Test Workspace    ${ws}

Dry-run — exits 0, applications.md unchanged
    [Documentation]    --dry-run must not write any changes to applications.md.
    ${ws}=    Workspace With Dups
    ${before}=    Get File    ${ws}/data/applications.md
    ${r}=    Run Script    ${ws}    dedup    --dry-run
    Script Should Exit 0    ${r}
    ${after}=    Get File    ${ws}/data/applications.md
    Should Be Equal    ${before}    ${after}
    [Teardown]    Remove Test Workspace    ${ws}

Empty tracker — exits 0, nothing to dedup
    [Documentation]    Header-only tracker with no data rows is a valid no-op.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_empty.md    data/applications.md
    ${r}=    Run Script    ${ws}    dedup
    Script Should Exit 0    ${r}
    [Teardown]    Remove Test Workspace    ${ws}
