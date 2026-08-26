#!/bin/bash

# Generate JSON Results from Test Data (Based on generate-email-notification-file.sh)
#
# This script generates a JSON file with test results in a predefined format
# without using templates. The full payload is built with jq so string fields
# (test names, URLs, env names) are correctly JSON-escaped.
#
# Usage: ./generate-email-notification-json.sh
#
# Optional overrides (for tests / local runs):
# - ALLURE_RESULTS_DIR — Allure results directory (default: /tmp/clone/allure-results)
# - EMAIL_NOTIFICATION_OUTPUT_DIR — output directory (default: /tmp/clone/scripts/email-notification-generated)
#
# Dependencies:
# - calculate-email-notification-variables.sh (for test statistics)
# - jq

# Function to generate email notification JSON results
generate_email_notification_json() {
    # Logging functions
    log_info() {
        echo "ℹ️ $1"
    }

    log_success() {
        echo "✅ $1"
    }
    # shellcheck disable=SC2329
    log_warning() {
        echo "⚠️ $1"
    }
    # shellcheck disable=SC2329
    log_error() {
        echo "❌ $1"
    }

    # Get script directory
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    local allure_results_dir="${ALLURE_RESULTS_DIR:-/tmp/clone/allure-results}"
    local output_dir="${EMAIL_NOTIFICATION_OUTPUT_DIR:-/tmp/clone/scripts/email-notification-generated}"
    mkdir -p "$output_dir"

    local output_file="$output_dir/email-notification-results-generated.json"

    log_info "Generating JSON results file"

    # Calculate pass rate and test details (may return non-zero when no results;
    # finalize_once pre-seeds FAILED stats in that case).
    source "$SCRIPT_DIR/calculate-email-notification-variables.sh" "$allure_results_dir" || true
    unset TEST_DETAILS_STRING

    # Defaults when calculate did not export stats (e.g. missing allure dir)
    TEST_OVERALL_STATUS="${TEST_OVERALL_STATUS:-FAILED}"
    TEST_PASS_RATE="${TEST_PASS_RATE:-0}"
    TEST_PASS_RATE_ROUNDED="${TEST_PASS_RATE_ROUNDED:-0}"
    TEST_TOTAL_COUNT="${TEST_TOTAL_COUNT:-0}"
    TEST_PASSED_COUNT="${TEST_PASSED_COUNT:-0}"
    TEST_FAILED_COUNT="${TEST_FAILED_COUNT:-0}"
    TEST_SKIPPED_COUNT="${TEST_SKIPPED_COUNT:-0}"

    # Calculate additional metrics
    if [ -n "${TEST_TOTAL_COUNT:-}" ] && [ "$TEST_TOTAL_COUNT" -gt 0 ]; then
        TEST_FAILURE_RATE=$(awk -v failed="$TEST_FAILED_COUNT" -v total="$TEST_TOTAL_COUNT" \
        'BEGIN { if (total > 0) printf "%.2f", failed * 100 / total; else print "0.00" }')
    else
        TEST_FAILURE_RATE="0.00"
    fi

    # Set default values for optional variables
    EXECUTION_DATE="${EXECUTION_DATE:-$(date '+%Y-%m-%d %H:%M:%S')}"
    TEST_COVERAGE="${TEST_COVERAGE:-100.00}"
    ATP_REPORT_VIEW_UI_URL="${ATP_REPORT_VIEW_UI_URL:-https://example.com}"
    if [[ "${ATP_REPORT_VIEW_UI_URL}" == Test\ not\ started* ]]; then
        ALLURE_REPORT_URL="${ATP_REPORT_VIEW_UI_URL}"
    else
        ALLURE_REPORT_URL="${ATP_REPORT_VIEW_UI_URL}/Report/${ENVIRONMENT_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/allure-report/index.html"
    fi
    TIMESTAMP="${TIMESTAMP:-$(date '+%Y-%m-%d %H:%M:%S UTC')}"

    log_info "Building JSON structure..."

    # stream test_details from allure files; never round-trip TEST_DETAILS_STRING
    local test_details_json=""
    local test_details_rc=0
    local test_details_failed=false
    if [ -d "$allure_results_dir" ] && compgen -G "$allure_results_dir/*-result.json" > /dev/null 2>&1; then
        test_details_json=$(
            find "$allure_results_dir" -maxdepth 1 -name '*-result.json' -print0 |
                xargs -0 -r cat -- |
                jq -s '[
                    group_by(
                        if (.historyId // "") != "" then .historyId
                        elif (.fullName // "") != "" then .fullName
                        else .uuid end
                    )
                    | .[]
                    | (max_by(.stop // .start // 0)) as $w
                    | (length - 1) as $retries
                    | (
                        if $w.status == "passed" then "PASSED"
                        elif $w.status == "failed" then "FAILED"
                        elif $w.status == "skipped" then "SKIPPED"
                        else "UNKNOWN" end
                    ) as $base
                    | {
                        status: (
                            if $retries == 0 then $base
                            elif $retries == 1 then "\($base) (1 retry)"
                            else "\($base) (\($retries) retries)" end
                        ),
                        test_name: $w.name,
                        emoji: (
                            if $w.status == "passed" then "✅"
                            elif $w.status == "failed" then "❌"
                            elif $w.status == "skipped" then "⚠️"
                            else "❓" end
                        )
                    }
                ]'
        ) || test_details_rc=$?
    fi
    if [ "$test_details_rc" -ne 0 ]; then
        log_error "Failed to build test_details from Allure results (jq exit $test_details_rc)"
        test_details_failed=true
        test_details_json='[]'
    elif [ -z "$test_details_json" ]; then
        test_details_json='[]'
    fi

    write_email_notification_json() {
        local target_file="$1"
        local details_json="$2"

        jq -n \
            --arg overall_status "$TEST_OVERALL_STATUS" \
            --argjson pass_rate "$TEST_PASS_RATE" \
            --argjson pass_rate_rounded "$TEST_PASS_RATE_ROUNDED" \
            --argjson total_count "$TEST_TOTAL_COUNT" \
            --argjson passed_count "$TEST_PASSED_COUNT" \
            --argjson failed_count "$TEST_FAILED_COUNT" \
            --argjson skipped_count "$TEST_SKIPPED_COUNT" \
            --argjson failure_rate "$TEST_FAILURE_RATE" \
            --argjson coverage "$TEST_COVERAGE" \
            --arg execution_date "$EXECUTION_DATE" \
            --arg timestamp "$TIMESTAMP" \
            --arg environment_name "${ENVIRONMENT_NAME:-Unknown}" \
            --arg atp_report_view_ui_url "$ATP_REPORT_VIEW_UI_URL" \
            --arg allure_report_url "$ALLURE_REPORT_URL" \
            --argjson test_details "$details_json" \
            --arg env_pass_rate "$TEST_PASS_RATE" \
            --arg env_pass_rate_rounded "$TEST_PASS_RATE_ROUNDED" \
            --arg env_total_count "$TEST_TOTAL_COUNT" \
            --arg env_passed_count "$TEST_PASSED_COUNT" \
            --arg env_failed_count "$TEST_FAILED_COUNT" \
            --arg env_skipped_count "$TEST_SKIPPED_COUNT" \
            --arg env_overall_status "$TEST_OVERALL_STATUS" \
            --arg env_failure_rate "$TEST_FAILURE_RATE" \
            --arg env_coverage "$TEST_COVERAGE" \
            '{
                test_results: {
                    overall_status: $overall_status,
                    pass_rate: $pass_rate,
                    pass_rate_rounded: $pass_rate_rounded,
                    total_count: $total_count,
                    passed_count: $passed_count,
                    failed_count: $failed_count,
                    skipped_count: $skipped_count,
                    failure_rate: $failure_rate,
                    coverage: $coverage
                },
                execution_info: {
                    execution_date: $execution_date,
                    timestamp: $timestamp,
                    environment_name: $environment_name,
                    atp_report_view_ui_url: $atp_report_view_ui_url,
                    allure_report_url: $allure_report_url
                },
                test_details: $test_details,
                environment_variables: {
                    TEST_PASS_RATE: $env_pass_rate,
                    TEST_PASS_RATE_ROUNDED: $env_pass_rate_rounded,
                    TEST_TOTAL_COUNT: $env_total_count,
                    TEST_PASSED_COUNT: $env_passed_count,
                    TEST_FAILED_COUNT: $env_failed_count,
                    TEST_SKIPPED_COUNT: $env_skipped_count,
                    TEST_OVERALL_STATUS: $env_overall_status,
                    TEST_FAILURE_RATE: $env_failure_rate,
                    TEST_COVERAGE: $env_coverage,
                    EXECUTION_DATE: $execution_date,
                    ENVIRONMENT_NAME: $environment_name,
                    ATP_REPORT_VIEW_UI_URL: $atp_report_view_ui_url,
                    ALLURE_REPORT_URL: $allure_report_url,
                    TIMESTAMP: $timestamp
                },
                environment_variables_description: {
                    description: "Variables used in email notification json file",
                    variables: {
                        TEST_OVERALL_STATUS: "Overall test status (PASSED/PARTIAL/FAILED)",
                        TEST_PASS_RATE: "Pass rate percentage with 2 decimal places",
                        TEST_TOTAL_COUNT: "Total number of tests",
                        TEST_PASSED_COUNT: "Number of passed tests",
                        TEST_FAILED_COUNT: "Number of failed tests",
                        TEST_SKIPPED_COUNT: "Number of skipped tests",
                        TEST_FAILURE_RATE: "Failure rate percentage",
                        TEST_COVERAGE: "Test coverage percentage",
                        EXECUTION_DATE: "Test execution date and time",
                        ENVIRONMENT_NAME: "Environment name (dev/staging/prod)",
                        ATP_REPORT_VIEW_UI_URL: "Base URL for viewing reports",
                        ALLURE_REPORT_URL: "Full URL to Allure report",
                        TIMESTAMP: "Current timestamp",
                        TEST_DETAILS: "Details of all tests"
                    }
                },
                status_logic: {
                    description: "Logic for determining overall test status",
                    rules: {
                        PASSED: "100% of tests passed successfully",
                        PARTIAL: "80-99% of tests passed successfully",
                        FAILED: "Less than 80% of tests passed successfully"
                    }
                }
            }' > "$target_file"
    }

    write_minimal_failed_json() {
        local target_file="$1"
        local message="${2:-JSON generation failed}"
        jq -n \
            --arg message "$message" \
            --arg execution_date "${EXECUTION_DATE:-$(date '+%Y-%m-%d %H:%M:%S')}" \
            --arg timestamp "${TIMESTAMP:-$(date '+%Y-%m-%d %H:%M:%S UTC')}" \
            --arg environment_name "${ENVIRONMENT_NAME:-Unknown}" \
            '{
                test_results: {
                    overall_status: "FAILED",
                    pass_rate: 0,
                    pass_rate_rounded: 0,
                    total_count: 0,
                    passed_count: 0,
                    failed_count: 0,
                    skipped_count: 0,
                    failure_rate: 0,
                    coverage: 0
                },
                execution_info: {
                    execution_date: $execution_date,
                    timestamp: $timestamp,
                    environment_name: $environment_name,
                    atp_report_view_ui_url: $message,
                    allure_report_url: $message
                },
                test_details: [],
                environment_variables: {
                    TEST_PASS_RATE: "0",
                    TEST_PASS_RATE_ROUNDED: "0",
                    TEST_TOTAL_COUNT: "0",
                    TEST_PASSED_COUNT: "0",
                    TEST_FAILED_COUNT: "0",
                    TEST_SKIPPED_COUNT: "0",
                    TEST_OVERALL_STATUS: "FAILED",
                    TEST_FAILURE_RATE: "0",
                    TEST_COVERAGE: "0",
                    EXECUTION_DATE: $execution_date,
                    ENVIRONMENT_NAME: $environment_name,
                    ATP_REPORT_VIEW_UI_URL: $message,
                    ALLURE_REPORT_URL: $message,
                    TIMESTAMP: $timestamp
                },
                environment_variables_description: {
                    description: "Variables used in email notification json file",
                    variables: {
                        TEST_OVERALL_STATUS: "Overall test status (PASSED/PARTIAL/FAILED)",
                        TEST_PASS_RATE: "Pass rate percentage with 2 decimal places",
                        TEST_TOTAL_COUNT: "Total number of tests",
                        TEST_PASSED_COUNT: "Number of passed tests",
                        TEST_FAILED_COUNT: "Number of failed tests",
                        TEST_SKIPPED_COUNT: "Number of skipped tests",
                        TEST_FAILURE_RATE: "Failure rate percentage",
                        TEST_COVERAGE: "Test coverage percentage",
                        EXECUTION_DATE: "Test execution date and time",
                        ENVIRONMENT_NAME: "Environment name (dev/staging/prod)",
                        ATP_REPORT_VIEW_UI_URL: "Base URL for viewing reports",
                        ALLURE_REPORT_URL: "Full URL to Allure report",
                        TIMESTAMP: "Current timestamp",
                        TEST_DETAILS: "Details of all tests"
                    }
                },
                status_logic: {
                    description: "Logic for determining overall test status",
                    rules: {
                        PASSED: "100% of tests passed successfully",
                        PARTIAL: "80-99% of tests passed successfully",
                        FAILED: "Less than 80% of tests passed successfully"
                    }
                }
            }' > "$target_file"
    }

    if [ "$test_details_failed" = true ]; then
        write_minimal_failed_json "$output_file" "Failed to build test details" || true
        export JSON_FILE="$output_file"
        return 1
    fi

    if ! write_email_notification_json "$output_file" "$test_details_json"; then
        log_error "jq failed while writing email notification JSON"
        write_minimal_failed_json "$output_file" "JSON generation failed" || true
        export JSON_FILE="$output_file"
        return 1
    fi

    if ! jq empty "$output_file" 2>/dev/null; then
        log_error "Generated JSON is invalid: $output_file"
        write_minimal_failed_json "$output_file" "Generated JSON was invalid" || true
        export JSON_FILE="$output_file"
        return 1
    fi

    log_success "JSON generated successfully: $output_file"

    export JSON_FILE="$output_file"

    log_info "Environment variables exported: JSON_FILE"
}
