*** Settings ***
Library    OperatingSystem
Library    Process
Library    String
Library    Collections

*** Variables ***
# Three levels up from tests/robot/resources/ → project root
${PROJECT_ROOT}    ${CURDIR}/../../..
${PYTHON}          python
${FIXTURES}        ${CURDIR}/fixtures

*** Keywords ***
New Test Workspace
    [Documentation]    Creates an isolated temp directory with the standard directory
    ...    structure for career-ops. The installed career-ops-cli package is used via
    ...    the --root flag, so no scripts need to be copied.
    ${tmp}=    Evaluate    __import__('tempfile').mkdtemp(prefix='career_ops_test_')
    Copy Directory    ${PROJECT_ROOT}/templates    ${tmp}/templates
    Copy Directory    ${PROJECT_ROOT}/modes    ${tmp}/modes
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
    [Arguments]    ${workspace}    ${command}    @{args}
    ${result}=    Run Process    career-ops    --root    ${workspace}
    ...    ${command}    @{args}    stdout=PIPE    stderr=PIPE
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
