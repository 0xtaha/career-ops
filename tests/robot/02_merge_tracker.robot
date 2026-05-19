*** Settings ***
Documentation    Black-box characterization tests for merge.
...
...    Verifies observable behavior: exit codes, stdout messages, file mutations,
...    TSV archival, and status normalization. Each test gets an isolated workspace.
Resource         resources/common.resource

*** Keywords ***
Setup Workspace With Tracker
    [Arguments]    ${fixture}=applications_empty.md
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    ${fixture}    data/applications.md
    RETURN    ${ws}

*** Test Cases ***
No pending TSVs — exits 0 and reports nothing to merge
    [Documentation]    With an empty tracker-additions/ directory the script should
    ...                report success without modifying applications.md.
    ${ws}=    Setup Workspace With Tracker
    ${before}=    Get Applications Content    ${ws}
    ${r}=    Run Script    ${ws}    merge
    Script Should Exit 0    ${r}
    Should Contain    ${r.stdout}    No pending additions
    ${after}=    Get Applications Content    ${ws}
    Should Be Equal    ${before}    ${after}
    [Teardown]    Remove Test Workspace    ${ws}

Valid 9-column TSV — entry appended to applications.md
    [Documentation]    A well-formed 9-column TSV in tracker-additions/ is merged
    ...                into the tracker table and moved to merged/.
    ${ws}=    Setup Workspace With Tracker
    Install Fixture    ${ws}    tracker_valid.tsv    batch/tracker-additions/010-testco.tsv
    ${r}=    Run Script    ${ws}    merge
    Script Should Exit 0    ${r}
    ${content}=    Get Applications Content    ${ws}
    Should Contain    ${content}    TestCo
    Should Contain    ${content}    Staff Engineer
    Should Contain    ${content}    4.1/5
    Should Contain    ${content}    Evaluated
    [Teardown]    Remove Test Workspace    ${ws}

Valid TSV — source file moved to merged/ after merge
    [Documentation]    After a successful merge the processed TSV must appear in
    ...                batch/tracker-additions/merged/ and be gone from the root.
    ${ws}=    Setup Workspace With Tracker
    Install Fixture    ${ws}    tracker_valid.tsv    batch/tracker-additions/010-testco.tsv
    Run Script    ${ws}    merge
    File Should Not Exist    ${ws}/batch/tracker-additions/010-testco.tsv
    File Should Exist        ${ws}/batch/tracker-additions/merged/010-testco.tsv
    [Teardown]    Remove Test Workspace    ${ws}

Dry-run — exits 0, applications.md unchanged, TSV stays in place
    [Documentation]    --dry-run must not write any files.
    ${ws}=    Setup Workspace With Tracker
    Install Fixture    ${ws}    tracker_valid.tsv    batch/tracker-additions/010-testco.tsv
    ${before}=    Get Applications Content    ${ws}
    ${r}=    Run Script    ${ws}    merge    --dry-run
    Script Should Exit 0    ${r}
    ${after}=    Get Applications Content    ${ws}
    Should Be Equal    ${before}    ${after}
    File Should Exist    ${ws}/batch/tracker-additions/010-testco.tsv
    File Should Not Exist    ${ws}/batch/tracker-additions/merged/010-testco.tsv
    [Teardown]    Remove Test Workspace    ${ws}

Alias status in TSV — normalized to canonical label in applications.md
    [Documentation]    The Spanish alias "aplicado" must be normalized to "Applied"
    ...                in the resulting tracker table row.
    ${ws}=    Setup Workspace With Tracker
    Install Fixture    ${ws}    tracker_alias_status.tsv    batch/tracker-additions/011-aliasco.tsv
    Run Script    ${ws}    merge
    ${content}=    Get Applications Content    ${ws}
    Should Contain       ${content}    Applied
    Should Not Contain   ${content}    aplicado
    [Teardown]    Remove Test Workspace    ${ws}

Merge into pre-existing tracker — row appended, existing rows preserved
    [Documentation]    Pre-existing entries in applications.md must survive intact
    ...                after a merge.
    ${ws}=    New Test Workspace
    Install Fixture    ${ws}    applications_canonical.md    data/applications.md
    Install Fixture    ${ws}    tracker_valid.tsv    batch/tracker-additions/010-testco.tsv
    Run Script    ${ws}    merge
    ${content}=    Get Applications Content    ${ws}
    # Pre-existing entries still present
    Should Contain    ${content}    Acme Corp
    Should Contain    ${content}    Beta Labs
    Should Contain    ${content}    Gamma Inc
    # New entry also present
    Should Contain    ${content}    TestCo
    [Teardown]    Remove Test Workspace    ${ws}
