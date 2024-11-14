*** Variables ***
${MY_VARIABLE}        variable

*** Settings ***
Library  PlatformLibrary

*** Keywords ***
Sample Keyword
    Log To Console  this is sample keyword

*** Test Cases ***
Sample Test Case
    [Tags]  sample_test
    ${service}=  Get Service  elasticsearch  elasticsearch-service
    Log To Console  ${service}

Second Sample Test
    [Tags]  second_sample_test
    ${service}=  Get Service  zookeeper-1  zookeeper-service
    Log To Console  ${service}

Third Sample Test
    [Tags]  third
    ${service}=  Get Service  zookeeper-2  zookeeper-service
    Log To Console  ${service}