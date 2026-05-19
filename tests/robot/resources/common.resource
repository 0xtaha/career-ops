*** Settings ***
Library    OperatingSystem
Library    Process
Library    String
Library    Collections

*** Variables ***
# Three levels up from tests/robot/resources/ → project root
${PROJECT_ROOT}    ${CURDIR}/../../..
${NODE}            node
${FIXTURES}        ${CURDIR}/fixtures

*** Keywords ***
New Test Workspace
    [Documentation]    Copies scripts and system files to an isolated temp directory.
    ...    Scripts resolve data paths via import.meta.url (relative to the script
    ...    file itself), so copying them gives full filesystem isolation.
    ${tmp}=    Evaluate    __import__('tempfile').mkdtemp(prefix='career_ops_test_')
    Copy Files    ${PROJECT_ROOT}/*.mjs    ${tmp}/
    Copy Directory    ${PROJECT_ROOT}/templates    ${tmp}/templates
    Copy Directory    ${PROJECT_ROOT}/modes    ${tmp}/modes
    Copy Directory    ${PROJECT_ROOT}/providers    ${tmp}/providers
    Copy File    ${CURDIR}/liveness_wrapper.mjs    ${tmp}/liveness_wrapper.mjs
    ${version_exists}=    Run Keyword And Return Status
    ...    File Should Exist    ${PROJECT_ROOT}/VERSION
    IF    ${version_exists}
        Copy File    ${PROJECT_ROOT}/VERSION    ${tmp}/VERSION
    END
    Create Directory    ${tmp}/data
    Create Directory    ${tmp}/batch/tracker-additions
    Create Directory    ${tmp}/batch/tracker-additions/merged
    Create Directory    ${tmp}/output
    Create Directory    ${tmp}/reports
    Create Directory    ${tmp}/config
    RETURN    ${tmp}

Remove Test Workspace
    [Arguments]    ${workspace}
    Remove Directory    ${workspace}    recursive=True

Run Script
    [Arguments]    ${workspace}    ${script}    @{args}
    ${result}=    Run Process    ${NODE}    ${workspace}/${script}    @{args}
    ...    cwd=${workspace}    stdout=PIPE    stderr=PIPE
    RETURN    ${result}

Script Should Exit 0
    [Arguments]    ${result}
    Should Be Equal As Integers    ${result.rc}    0
    ...    msg=Expected rc=0, got ${result.rc}\nSTDOUT:\n${result.stdout}\nSTDERR:\n${result.stderr}

Script Should Exit Non-Zero
    [Arguments]    ${result}
    Should Not Be Equal As Integers    ${result.rc}    0
    ...    msg=Expected non-zero rc, got 0\nSTDOUT:\n${result.stdout}\nSTDERR:\n${result.stderr}

Install Fixture
    [Arguments]    ${workspace}    ${fixture}    ${dest}
    Copy File    ${FIXTURES}/${fixture}    ${workspace}/${dest}

Get Applications Content
    [Arguments]    ${workspace}
    ${content}=    Get File    ${workspace}/data/applications.md
    RETURN    ${content}
