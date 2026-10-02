*** Settings ***
Documentation     Smoke suite for the image test in CI. The test that runs checks the runtime from inside
...               Robot Framework; the other two must never run, because TAGS or tags_exclusion.py
...               filter them out.
Library           OperatingSystem
Library           RequestsLibrary

*** Test Cases ***
Robot Runtime Works
    [Tags]    smoke
    ${robot_home}=    Get Environment Variable    ROBOT_HOME
    Should Be Equal    ${robot_home}    /opt/robot
    Directory Should Exist    ${robot_home}/output
    ${platform_library}=    Evaluate    importlib.import_module('PlatformLibrary')    modules=importlib
    Should Not Be Equal    ${platform_library}    ${NONE}

Excluded By Tags Resolver
    [Tags]    smoke    excluded_by_resolver
    Fail    tags_exclusion.py must exclude this test

Not Selected By TAGS
    [Tags]    not_selected
    Fail    TAGS=smoke must not select this test
