#!/bin/bash

export ROBOT_OPTIONS="--loglevel=info --outputdir output"
export ROBOT_SYSLOG_FILE=./output/syslog.txt
export ROBOT_SYSLOG_LEVEL=DEBUG

if [[ "$READONLY_CONTAINER_FILE_SYSTEM_ENABLED" == "true" ]]; then
    echo "Read-only file system configuration enabled, copying test files from temp directory..."
    TMP_FOLDER_READ_FS="/opt/robot_tmp"
    cp -r "${TMP_FOLDER_READ_FS}/." "${ROBOT_HOME}/"
fi

if [[ "$DEBUG" == true ]]; then
    set -x
    printenv
fi

run_custom_script() {
    if [[ -n "$CUSTOM_ENTRYPOINT_SCRIPT" ]]; then
        ${CUSTOM_ENTRYPOINT_SCRIPT}
    fi
}

create_tags_resolver_array() {
    tags_resolver_script="robot_tags_resolver.py"
    if [[ -n "$TAGS_RESOLVER_SCRIPT" ]]; then
        tags_resolver_script=${TAGS_RESOLVER_SCRIPT}
    fi
    tags_resolver_array=()
    while
        IFS=";"
        read -r -d ";" line
    do
        tags_resolver_array+=("$line")
    done < <(python "${tags_resolver_script}")
}

run_robot() {
    status_writing_script="write_status.py"
    if [[ ${STATUS_WRITING_ENABLED} == "true" ]]; then
        if [[ -n "$WRITE_STATUS_SCRIPT" ]]; then
            status_writing_script=${WRITE_STATUS_SCRIPT}
        fi
        if ! python "$status_writing_script" "in_progress"; then
            echo "Can not set in progress status for integration tests"
        fi
    fi

    if [[ -n "$SERVICE_CHECKER_SCRIPT" ]]; then
        timeout=300
        if [[ -n "$SERVICE_CHECKER_SCRIPT_TIMEOUT" ]]; then
            timeout=${SERVICE_CHECKER_SCRIPT_TIMEOUT}
        fi
        if ! python "${SERVICE_CHECKER_SCRIPT}" "${timeout}"; then
            echo "Service is not ready at least $timeout seconds or some exception occurred"
            exit 1
        fi
    fi

    excluded_tags=""
    if [[ ${IS_TAGS_RESOLVER_ENABLED} == "true" ]]; then
        create_tags_resolver_array
        echo "Included tags: ${TAGS}"
        echo "Excluded tags: ${tags_resolver_array[0]}"
        echo "${tags_resolver_array[1]}" # print all excluded tags with matched reason
        excluded_tags=${tags_resolver_array[0]}
    fi

    # Build args exactly like the standard (non-ATP) branch does:
    # - pass TAGS as a single -i expression (so NOT/OR/AND semantics are identical)
    # - pass excluded_tags as-is (it's produced like: "-e tag1ORtag2")
    robot_args=()
    if [[ -n "$TAGS" ]]; then
        robot_args+=("-i" "$TAGS")
    fi
    if [[ -n "$excluded_tags" ]]; then
        # robot_tags_resolver.py emits "-e tag1ORtag2..."; pass as two argv tokens (no unquoted expansion).
        if [[ "$excluded_tags" =~ ^-e[[:space:]]+(.*)$ ]]; then
            robot_args+=("-e" "${BASH_REMATCH[1]}")
        else
            robot_args+=("-e" "$excluded_tags")
        fi
    fi
    robot_args+=("./tests")

    : "${ATP_REPORT_ENABLED:=false}"
    if [[ "${ATP_REPORT_ENABLED}" == "true" ]]; then
        echo "Calling adapter-S3-entrypoint.sh with arguments: ${robot_args[*]}"
        "${ROBOT_HOME}/scripts/adapter-S3/adapter-S3-entrypoint.sh" "${robot_args[@]}"
    else
        echo "ATP report adapter disabled (ATP_REPORT_ENABLED!=true); running robot like upstream image"
        robot "${robot_args[@]}"
    fi

    robot_result=$?
    if [[ ${robot_result} -ne 0 ]]; then
        touch ./output/result.txt
        echo "Robot framework process was interrupted with code - ${robot_result}"
    fi

    analyze_result_script="analyze_result.py"
    if [[ ${IS_ANALYZER_RESULT_ENABLED} == "true" ]]; then
        if [[ -n "$ANALYZE_RESULT_SCRIPT" ]]; then
            analyze_result_script=${ANALYZE_RESULT_SCRIPT}
        fi
        python "${analyze_result_script}"
    fi

    if [[ ${STATUS_WRITING_ENABLED} == "true" ]]; then
        if [[ ${IS_ANALYZER_RESULT_ENABLED} != "true" ]]; then
            python "${analyze_result_script}"
        fi

        if ! python "$status_writing_script" "update"; then
            echo "Can not update status for integration tests"
        fi
    fi
    return ${robot_result}
}

# Process some known arguments to run integration tests
case "$1" in
custom)
    run_custom_script
    ;;
run-robot)
    echo "Starting ttyd immediately to satisfy liveness probe..."
    # 1. We run ttyd immediately so port 8080 opens instantly.
    # 2. ttyd runs a bash subshell that executes tests, then drops to an interactive shell.
    exec ttyd -p "${TTYD_PORT:-8080}" bash -c '
        run_robot
        echo "Robot tests finished. Keeping ttyd session alive for debugging..."
        bash
    '
    ;;
run-robot-without-ttyd)
    run_robot
    ;;
run-ttyd)
    exec ttyd -p "${TTYD_PORT:-8080}" bash
    ;;
esac

# Otherwise just run the specified command
exec "$@"
