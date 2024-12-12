# Introduction

The `Docker Integration Tests` (aka `BDI`) is image for integration tests. Supposed that this image will not be used to execute integration tests directly 
but real images for integration tests will use this image as basic (`FROM` command in the particular docker file). BDI builds some `sandbox` which
includes `python` interpreter, Robot Framework, some useful tools such as `bash`, `shadow`, `vim`, `rsync`, `ttyd`, common custom Robot Framework libraries 
(for example, `PlatformLibrary`) and customized docker entry point script.

# Pre-installed tools

The `Docker Integration Tests` contains the following pre-installed Linux tools:

* `python` (version 3.10.13)
* `bash`
* `shadow`
* `vim`
* `rsync`
* `ttyd`

# Library documentation

`PlatformLibrary` documentation is autogenerated by Robot Framework libdoc tool. It can be found [here](/documentation/integration_tests_builtin_library_documentation/PlatformLibrary.html)
To generate new doc you should navigate to current project repository and execute the following command:

```bash
python -m robot.libdoc PlatformLibrary.py PlatformLibrary.html
```
 
and move `PlatformLibrary.html` file to documentation directory.

# Docker Entry point Script

A docker entry point script is a script which will be executed after docker container is created. If you override the image, its entry point script 
will be executed by default. But if you override the entry point as well, your own entry point will be run.
Docker Integration Tests contains simple and customized entry point script - `/docker-entrypoint.sh` with the following command (possible `CMD` arguments): 

* `run-robot` is a default `CMD` command which executes Robot Framework test cases, can resolve Robot Framework tags to be excluded, can create
`result.txt` file with parsed Robot Framework tests results in pretty format. After tests execution `ttyd` tool is started.

* `run-ttyd` command starts `ttyd` tool. `ttyd` is Web-console which rather useful for dev and troubleshooting purposes.

* `custom` command executes custom bash script if this script's path is provided. To provide custom script this script should exist within container
and environment variable `CUSTOM_ENTRYPOINT_SCRIPT` should contain path to the script. Actually, `custom` command is equivalent to overriding the entry point 
script but we recommend implementing custom script instead of entry point overriding.

Example of equivalent console command:

```bash
/docker-entrypoint.sh run-robot
```

Below is detailed description regarding `run-robot` command.

## run-robot description

`run-robot` command contains 4 customized steps:

* `service checker script`. Sometimes we want to make sure that "tested" service is ready for testing and start execution only for "ready" service.
For this purpose inheritor image should implement "service checker script" (python) which gives `timeout` argument in seconds (by default `timeout` is
300 second but can be overridden by `SERVICE_CHECKER_SCRIPT_TIMEOUT` environment variable) and checks if the service is ready. If the service is ready entry
point script goes to the next step. To specify "service checker script" `SERVICE_CHECKER_SCRIPT` environment variable should not be empty and should contain
path to custom python script. By default, `SERVICE_CHECKER_SCRIPT` is empty and current entry point script step is skipped.

* `excluded tags resolver`. Sometimes some Robot Framework tests can not be executed in given configuration. For example, test should check `Elasticsearch`
service but `elasticsearch` URL is not given and we want to skip this test. The Robot Framework paradigm supposed that this case should be resolved by tag
approach. We can point which tests should be skipped by its tags. For example, `robot -e my-excluded_tag ./tests`. Docker Integration Tests entry point script 
provides development approach to recognize which tests should be skipped before tests execution. Supposed that `.robot` files are contained some root 
folder (for, example `tests`). `robot_tags_resolver.py` script recursively bypasses all inner folder to look up all `tags_exclusion.py` modules. For each
found module `get_excluded_tags(environ)` function will be executed, where where environ is a list of environment variables. `get_excluded_tags` function should 
return list or dictionary of excluded tags. If list is returned, all tags will be added to result set of excluded tags. If dictionary is returned, all keys
will be added to result set of excluded tags and the particular dictionary will update result dictionary which will be printed to console as some map where
keys are excluded tags and values are reasons why these tags are excluded. Default tags resolver script is `robot_tags_resolver.py` but inheritor image
can override it by `TAGS_RESOLVER_SCRIPT` environment variable which contains path to custom tags resolver script. To skip excluded tags resolving process
environment variable `IS_TAGS_RESOLVER_ENABLED` should be `false` (it is `true` by default).

* `robot tests execution`. This step can not be skipped. It executes Robot Framework tests without excluded ones. If `TAGS` environment variable is
presented only these tags will be executed. This is an example of specifying only `first` and `second` tests from `first`, `second` and `third`:
```bash
firstORsecond
```       
If tag of test is contained in included and excluded tags it will not be executed.

* `analyze results`. Sometimes text file with Robot Framework results should be generated in pretty human readable format. For example, we want to copy
this result from Kubernetes Pod to Jenkins job and we want text results instead of all Pod's logs or `html` formatted file. For this purpose 
`analyze_result.py` module will be executed. This module creates `result.txt` file in `output` folder (with all Robot Framework results) with tests results
in pretty format. To skip this step environment variable `IS_ANALYZER_RESULT_ENABLED` should be `false` (it is `true` by default). Default analyzer 
script is `analyze_result.py` but inheritor image can override it by `ANALYZE_RESULT_SCRIPT` environment variable which contains path to custom 
analyzer script.

* `write status`. To integrate with deployer Jenkins Job status of integration tests should be set to watched by Jenkins Job Kubernetes entity. It can be
as custom resource (CR) as native Kubernetes entities (deployments, pods, etc.). The BDI provides an ability to write status of executed tests to some
Kubernetes entity out of the box. Status is written as Kubernetes status condition with the following fields:
- `lastTransitionTime` - timestamp.
- `message` - parsed results of Robot framework integration tests as string.
- `reason` - static field with `IntegrationTestsExecutionStatus` value.
- `status` - can be `True` or `False`. This field depends on `type` field. It is `True` if `type` is `Ready` or `Successful`
  and `False` if `type` is `Failed` or `In progress`.
- `type` - can be `Ready`, `Successful`, `Failed` or `In progress`.

For example,
```
lastTransitionTime: "2021-04-21T11:21:31.332Z"
message: <Robot Framework parsed results>
reason: IntegrationTestsExecutionStatus
status: "True"
type: Ready
```  

In some cases, it is necessary to have `status` field as `boolean` instead of `string`. 

For example,
```
lastTransitionTime: "2021-04-21T11:21:31.332Z"
message: <Robot Framework parsed results>
reason: IntegrationTestsExecutionStatus
status: true
type: Ready
```  

To support this, environment variable `IS_STATUS_BOOLEAN` must be set to `true`.
By default, `IS_STATUS_BOOLEAN` is considered to be `false`.

**Note!** For using feature `write status` in restricted environment, the user or service account used by the Deployer should have
permissions on entity group with the verbs `get`, `patch` and resources `<resource_plural>/status` in current the namespace or project.
For example, permissions for write status in Custom Resource:
```
- apiGroups:
  - qubership.org
  resources:
  - platformmonitorings/status
  verbs:
  - get
  - patch
```

To write status to some k8s entity you should specify the entity. There are two ways to do this. The first one is to specify
full path. For example, you have `ZooKeeperService` custom resource which has
`metadata.selfLink` field with value - `/apis/qubership.org/v1/namespaces/zookeeper-service/zookeeperservices/zookeeper`,
in the current approach you should specify `STATUS_CUSTOM_RESOURCE_PATH` environment variable with value from `selfLink` without
`apis` prefix and `namespaces` part:
```
STATUS_CUSTOM_RESOURCE_PATH=qubership.org/v1/zookeeper-service/zookeeperservices/zookeeper
```
The second approach is to point the path in parts using the following environment variables:
```
STATUS_CUSTOM_RESOURCE_GROUP=qubership.org
STATUS_CUSTOM_RESOURCE_VERSION=v1 
STATUS_CUSTOM_RESOURCE_NAMESPACE=zookeeper-service
STATUS_CUSTOM_RESOURCE_PLURAL=zookeeperservices 
STATUS_CUSTOM_RESOURCE_NAME=zookeeper
```
If your k8s pod with integration tests always writes status to well-known custom resource you can override all this environment
variables (excluding `STATUS_CUSTOM_RESOURCE_NAMESPACE`) in your docker file and set namespace in helm chart.

Both of this approaches work with native k8s entities too. For example,
```
STATUS_CUSTOM_RESOURCE_GROUP=apps
STATUS_CUSTOM_RESOURCE_VERSION=v1
STATUS_CUSTOM_RESOURCE_NAMESPACE=zookeeper-service
STATUS_CUSTOM_RESOURCE_PLURAL=deployments
STATUS_CUSTOM_RESOURCE_NAME=zookeeper-1
```

If feature is available `write_status.py` script is called two times. The first time immediately after docker entrypoint script
was started to set `In progress` condition. The second time after tests are finished and parsed by `analyze results` script
to set in the `message` field tests results. Default analyzer script is `write_status.py` but inheritor image can override it 
by `WRITE_STATUS_SCRIPT` environment variable which contains path to custom "write status" script.

By default, if all tests are passed BDI set `Ready` value to `type` condition field. There is an ability to deploy only
integration tests without any component (component was installed before). In this case you should set `ONLY_INTEGRATION_TESTS` 
environment variable as `true` and BDI will set `Successful` as value of `type` condition field.

The `message` field in the status condition by default contains first line from `result.txt` file (which is generated in the 
previous step). To write full parsed result you should set `IS_SHORT_STATUS_MESSAGE` environment variable to `false`.

**Important!** If you use custom script to parse result (`ANALYZE_RESULT_SCRIPT` is not empty) please pay attention that result
should be placed in the `result.txt` file and the first line will be used as short status message. 

**Note!** This feature (write status to k8s entities) is disabled by default! To turn on it please set the `STATUS_WRITING_ENABLED` environment variable to `true`.
For example in your docker file as
```
ENV STATUS_WRITING_ENABLED=true
```
  

# Environment Variables

Docker Integration Tests uses the following environment variables:

* DEBUG 
* TTYD_PORT 
* CUSTOM_ENTRYPOINT_SCRIPT  
* SERVICE_CHECKER_SCRIPT 
* SERVICE_CHECKER_SCRIPT_TIMEOUT 
* IS_TAGS_RESOLVER_ENABLED 
* IS_ANALYZER_RESULT_ENABLED 
* ANALYZE_RESULT_SCRIPT
* STATUS_CUSTOM_RESOURCE_GROUP
* STATUS_CUSTOM_RESOURCE_VERSION
* STATUS_CUSTOM_RESOURCE_NAMESPACE
* STATUS_CUSTOM_RESOURCE_PLURAL
* STATUS_CUSTOM_RESOURCE_NAME
* ONLY_INTEGRATION_TESTS
* STATUS_CUSTOM_RESOURCE_PATH
* STATUS_WRITING_ENABLED
* WRITE_STATUS_SCRIPT
* IS_SHORT_STATUS_MESSAGE  
* TAGS
* IS_STATUS_BOOLEAN

All of them instead of `TAGS`, `ONLY_INTEGRATION_TESTS`, `STATUS_CUSTOM_RESOURCE_NAMESPACE`, `STATUS_CUSTOM_RESOURCE_PATH` and maybe `DEBUG` 
we recommend overriding in the docker file and do not forward them to the integration tests deployment environment.    