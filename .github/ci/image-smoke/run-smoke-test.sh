#!/bin/bash
# Checks the contract that downstream images rely on (see AGENTS.md) against a locally built image:
# the runtime layout, the bundled tools and Python packages, and the entrypoint modes.
#
# Usage: run-smoke-test.sh <image>

# Commands passed to in_image are single-quoted on purpose: they expand inside the container, not on the host.
# shellcheck disable=SC2016

set -euo pipefail

image="${1:?Usage: run-smoke-test.sh <image>}"
fixture_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_dir="$(mktemp -d)"
trap 'rm -rf "${output_dir}"' EXIT

failures=0

check() {
    local description="$1"
    shift
    if "$@"; then
        echo "PASS: ${description}"
    else
        echo "FAIL: ${description}"
        failures=$((failures + 1))
    fi
}

in_image() {
    docker run --rm --entrypoint /bin/bash "${image}" -c "$1"
}

# Runs the entrypoint as the 1000:0 user that downstream deployments use, with the smoke suite mounted.
run_entrypoint() {
    rm -rf "${output_dir:?}"/*
    docker run --rm --user 1000:0 \
        -v "${fixture_dir}/tests:/opt/robot/tests:ro" \
        -v "${output_dir}:/opt/robot/output" \
        "$@" \
        "${image}" run-robot-without-ttyd
}

chmod 0777 "${output_dir}"

echo "--- Runtime layout"
check "ROBOT_HOME is /opt/robot" in_image '[[ "${ROBOT_HOME}" == /opt/robot ]]'
check "working directory is ROBOT_HOME" in_image '[[ "$(pwd)" == "${ROBOT_HOME}" ]]'
check "user robot has UID 1000 and belongs to group 0" \
    in_image '[[ "$(id -u robot)" == 1000 ]] && id -G robot | tr " " "\n" | grep -qx 0'
check "ROBOT_HOME is owned by 1000:0" in_image '[[ "$(stat -c %u:%g "${ROBOT_HOME}")" == 1000:0 ]]'
check "helper scripts are in ROBOT_HOME" in_image \
    'cd "${ROBOT_HOME}" && test -f robot_tags_resolver.py -a -f analyze_result.py -a -f write_status.py \
        -a -x scripts/adapter-S3/adapter-S3-entrypoint.sh'

echo "--- Bundled tools"
for tool in bash rsync vim inotifywait; do
    check "${tool} is installed" in_image "command -v ${tool} >/dev/null"
done
check "ttyd runs" in_image 'ttyd --version'
check "s5cmd runs" in_image 's5cmd version'

echo "--- Python packages"
check "installed packages have compatible dependencies" in_image 'python -m pip check'
check "robot runs" in_image 'robot --version; [[ $? -eq 251 ]]'
check "keyword library modules import" in_image \
    'python -c "import PlatformLibrary, KubernetesClient, OpenShiftClient, MonitoringLibrary, OAuthLibrary, \
        S3BackupLibrary, s3_storage, FileSystemS3"'
check "third-party Robot libraries import" in_image \
    'python -c "import RequestsLibrary, allure_robotframework"'

echo "--- Entrypoint: run-robot-without-ttyd with passing tests"
if run_entrypoint -e TAGS=smoke; then
    check "exit code is 0" true
else
    check "exit code is 0" false
fi
check "result.txt reports success" grep -q "RESULT: TESTS PASSED" "${output_dir}/result.txt"
check "only the selected, non-excluded test ran" grep -q "Passed: 1"$'\t'"|"$'\t'"Failed: 0" "${output_dir}/result.txt"

echo "--- Entrypoint: run-robot-without-ttyd with a failing test"
if run_entrypoint -e TAGS=not_selected; then
    check "exit code is non-zero when a test fails" false
else
    check "exit code is non-zero when a test fails" true
fi
check "result.txt reports the failure" grep -q "RESULT: TESTS FAILED" "${output_dir}/result.txt"

if [[ ${failures} -ne 0 ]]; then
    echo "${failures} check(s) failed for ${image}"
    exit 1
fi
echo "All checks passed for ${image}"
