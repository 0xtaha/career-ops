*** Settings ***
Documentation    Black-box characterization tests for liveness-core.mjs.
...
...    classifyLiveness() is a pure function with no I/O, exercised here through
...    liveness_wrapper.mjs (a thin CLI shim).  Tests cover the three result
...    values — expired / active / uncertain — across multiple trigger patterns.
Resource         resources/common.resource
Library          String

Suite Setup      Initialize Suite Workspace
Suite Teardown   Remove Test Workspace    ${WS}

*** Variables ***
${WS}    ${EMPTY}

*** Keywords ***
Initialize Suite Workspace
    ${ws}=    New Test Workspace
    Set Suite Variable    ${WS}    ${ws}

*** Keywords ***
Classify
    [Documentation]    Runs liveness_wrapper.mjs with the given JSON payload and
    ...                returns the parsed result string (active/expired/uncertain).
    [Arguments]    ${payload_json}
    ${r}=    Run Script    ${WS}    liveness_wrapper.mjs    ${payload_json}
    Script Should Exit 0    ${r}
    ${result_obj}=    Evaluate    __import__('json').loads("""${r.stdout.strip()}""")
    RETURN    ${result_obj}

Result Should Be
    [Arguments]    ${result_obj}    ${expected}
    Should Be Equal    ${result_obj}[result]    ${expected}
    ...    msg=Expected result="${expected}", got "${result_obj}[result]" (reason: ${result_obj.get('reason','')})

*** Test Cases ***
Expired — hard-coded "job is no longer available" pattern
    [Documentation]    Body text matching a HARD_EXPIRED_PATTERNS entry must yield
    ...                result="expired".
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/123","bodyText":"Sorry, this job is no longer available.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Expired — "position has been filled" pattern
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/456","bodyText":"This position has been filled.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Expired — "applications are closed" pattern
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/789","bodyText":"Applications are closed for this role.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Expired — "this job has expired" pattern
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/000","bodyText":"This job has expired.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Expired — "no longer accepting applications" pattern
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/001","bodyText":"We are no longer accepting applications for this role.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Expired — HTTP 404 with empty body
    [Documentation]    A 404 response with no body should resolve as expired.
    ${payload}=    Set Variable
    ...    {"status":404,"finalUrl":"https://example.com/job/404","bodyText":"","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    expired

Active — apply controls present
    [Documentation]    When applyControls contains a button text the posting is
    ...                active regardless of body content.
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/live","bodyText":"Join our team as a Software Engineer.","applyControls":["Apply for this job"]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    active

Active — multiple apply controls
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/live2","bodyText":"We are hiring.","applyControls":["Apply Now","Easy Apply"]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    active

Uncertain — rich body but no apply controls and no expired patterns
    [Documentation]    A page with substantive content but no apply button and no
    ...                closure language should be uncertain.
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/careers","bodyText":"We are a fast-growing startup. Our team is passionate about technology. Learn more about our culture and values. We care about diversity and inclusion.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    uncertain

Uncertain — listing page pattern (many jobs found)
    [Documentation]    A page that looks like a job-listing index (e.g. "42 jobs found")
    ...                rather than a single posting should not be treated as active.
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://careers.example.com/search","bodyText":"42 jobs found matching your search.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Result Should Be    ${obj}    uncertain

Expired result includes non-empty reason string
    [Documentation]    The reason field must explain why the result was reached;
    ...                it must not be an empty string.
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/999","bodyText":"This job listing is closed.","applyControls":[]}
    ${obj}=    Classify    ${payload}
    Should Not Be Empty    ${obj}[reason]
    ...    msg=classifyLiveness must always return a non-empty reason

Active result includes non-empty reason string
    ${payload}=    Set Variable
    ...    {"status":200,"finalUrl":"https://example.com/job/live3","bodyText":"Join us!","applyControls":["Apply"]}
    ${obj}=    Classify    ${payload}
    Should Not Be Empty    ${obj}[reason]
