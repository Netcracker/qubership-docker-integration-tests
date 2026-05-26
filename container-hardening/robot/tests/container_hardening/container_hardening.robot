*** Settings ***
Library    PlatformLibrary
Library    OperatingSystem
Library    Collections
Library    String

*** Variables ***
${PART_OF}          %{PART_OF=}
${EXCLUSIONS_JSON}  %{EXCLUSIONS_JSON=}
${NAMESPACE}  %{KUBE_NAMESPACE=}

*** Test Cases ***
Test Container Hardening
    [Documentation]    Verifies container the security hardening rules CH1–CH12 for pods in the
    ...                current namespace. When PART_OF is set (comma-separated), only pods
    ...                whose app.kubernetes.io/part-of label matches are checked. When PART_OF
    ...                is empty, all pods in the namespace are checked.
    [Tags]    container_hardening
    ${part_of}=    Set Variable    ${NONE}
    IF    '${PART_OF}' != ''
        ${part_of}=    Split String    ${PART_OF}    ,
    END
    ${exclusions}=    Evaluate    json.loads('${EXCLUSIONS_JSON}') if '${EXCLUSIONS_JSON}' else {}    json
    Check Container Hardening    ${part_of}    ${NAMESPACE}    ${exclusions}
