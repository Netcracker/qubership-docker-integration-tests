#!/bin/bash

# Generate JSON Results from Test Data (Based on generate-email-notification-file.sh)
#
# This script generates a JSON file with test results in a predefined format
# without using templates
#
# Usage: ./generate-email-notification-json.sh
#
# Dependencies:
# - calculate-email-notification-variables.sh (for test statistics)

set -eo pipefail

# Function to generate email notification JSON results
generate_email_notification_json() {
    # Logging functions
    log_info() {
        echo "INFO: $1"
    }

    # Get script directory
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Set allure results directory to default location
    local allure_results_dir="/tmp/clone/allure-results"

    # Create email-notification-generated directory one level up
    local output_dir="/tmp/clone/scripts/email-notification-generated"
    mkdir -p "$output_dir"

    local output_file="$output_dir/email-notification-results-generated.json"

    log_info "Generating JSON results file"

    # Calculate pass rate and test details
    source "$SCRIPT_DIR/calculate-email-notification-variables.sh" "$allure_results_dir"

    # Calculate additional metrics
    if [ -n "${TEST_TOTAL_COUNT:-}" ] && [ "$TEST_TOTAL_COUNT" -gt 0 ]; then
        TEST_FAILURE_RATE=$(awk "BEGIN {printf \"%.2f\", $TEST_FAILED_COUNT * 100 / $TEST_TOTAL_COUNT}")
    else
        TEST_FAILURE_RATE="0.00"
    fi

    # Set default values for optional variables
    EXECUTION_DATE="${EXECUTION_DATE:-$(date '+%Y-%m-%d %H:%M:%S')}"
    TEST_COVERAGE="${TEST_COVERAGE:-100.00}"
    ATP_REPORT_VIEW_UI_URL="${ATP_REPORT_VIEW_UI_URL:-https://example.com}"
    ALLURE_REPORT_URL="${ATP_REPORT_VIEW_UI_URL}/Report/${ENVIRONMENT_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/allure-report/index.html"
    TIMESTAMP="${TIMESTAMP:-$(date '+%Y-%m-%d %H:%M:%S UTC')}"

    log_info "Building JSON structure..."

    # Build test details JSON array
    local test_details_json="["
    local first_test=true

    if [ -n "${TEST_DETAILS_STRING:-}" ]; then
        # Convert \n to actual newlines and process each test detail line
        # Use process substitution to avoid subshell issues
        while IFS= read -r line; do
            # Skip header lines
            if [[ "$line" =~ ^[[:space:]]*Status[[:space:]]*\| ]] || [[ "$line" =~ ^[[:space:]]*-+[[:space:]]*\| ]]; then
                continue
            fi

            # Extract status and test name from the formatted line
            if [[ "$line" =~ ^[[:space:]]*([^|]+)\|[[:space:]]*(.+)$ ]]; then
                local status_part="${BASH_REMATCH[1]// /}"
                # Keep test name exactly as is (no formatting applied)
                local test_name="${BASH_REMATCH[2]}"

                # Determine status and emoji
                local status="UNKNOWN"
                local emoji="UNKNOWN"

                if [[ "$status_part" =~ PASSED ]]; then
                    status="PASSED"
                    emoji="PASSED"
                elif [[ "$status_part" =~ FAILED ]]; then
                    status="FAILED"
                    emoji="FAILED"
                elif [[ "$status_part" =~ SKIPPED ]]; then
                    status="SKIPPED"
                    emoji="SKIPPED"
                fi

                # Add comma if not first test
                if [ "$first_test" = true ]; then
                    first_test=false
                else
                    test_details_json="$test_details_json,"
                fi

                # Add test object to JSON array
                test_details_json="$test_details_json"$'\n    {'$'\n      "status": "'"$status"'",'$'\n      "test_name": "'"$test_name"'",'$'\n      "emoji": "'"$emoji"'"'$'\n    }'
            fi
        done < <(echo -e "$TEST_DETAILS_STRING")
    else
        # If no test details string, try to get test details from allure results directly
        log_info "Parsing allure results directly..."

        # Process each result file directly
        for result_file in "$allure_results_dir"/*-result.json; do
            if [ -f "$result_file" ]; then
                # Extract test status and name using jq
                local status
                status=$(jq -r '.status' "$result_file" 2>/dev/null || echo "unknown")
                local test_name
                test_name=$(jq -r '.name' "$result_file" 2>/dev/null || echo "Unknown Test")

                # Determine status and emoji
                local emoji="UNKNOWN"
                case "$status" in
                "passed")
                    status="PASSED"
                    emoji="PASSED"
                    ;;
                "failed")
                    status="FAILED"
                    emoji="FAILED"
                    ;;
                "skipped")
                    status="SKIPPED"
                    emoji="SKIPPED"
                    ;;
                *)
                    status="UNKNOWN"
                    emoji="UNKNOWN"
                    ;;
                esac

                # Add comma if not first test
                if [ "$first_test" = true ]; then
                    first_test=false
                else
                    test_details_json="$test_details_json,"
                fi

                # Add test object to JSON array
                test_details_json="$test_details_json"$'\n    {'$'\n      "status": "'"$status"'",'$'\n      "test_name": "'"$test_name"'",'$'\n      "emoji": "'"$emoji"'"'$'\n    }'
            fi
        done
    fi

    test_details_json="$test_details_json"$'\n  ]'

    # Build complete JSON structure
    local json_content
    json_content=$(
        cat <<EOF
{
    "test_results": {
        "overall_status": "$TEST_OVERALL_STATUS",
        "pass_rate": $TEST_PASS_RATE,
        "pass_rate_rounded": $TEST_PASS_RATE_ROUNDED,
        "total_count": $TEST_TOTAL_COUNT,
        "passed_count": $TEST_PASSED_COUNT,
        "failed_count": $TEST_FAILED_COUNT,
        "skipped_count": $TEST_SKIPPED_COUNT,
        "failure_rate": $TEST_FAILURE_RATE,
        "coverage": $TEST_COVERAGE
    },
    "execution_info": {
        "execution_date": "$EXECUTION_DATE",
        "timestamp": "$TIMESTAMP",
        "environment_name": "${ENVIRONMENT_NAME:-Unknown}",
        "atp_report_view_ui_url": "$ATP_REPORT_VIEW_UI_URL",
        "allure_report_url": "$ALLURE_REPORT_URL"
    },
    "test_details": $test_details_json,
    "environment_variables": {
        "TEST_PASS_RATE": "$TEST_PASS_RATE",
        "TEST_PASS_RATE_ROUNDED": "$TEST_PASS_RATE_ROUNDED",
        "TEST_TOTAL_COUNT": "$TEST_TOTAL_COUNT",
        "TEST_PASSED_COUNT": "$TEST_PASSED_COUNT",
        "TEST_FAILED_COUNT": "$TEST_FAILED_COUNT",
        "TEST_SKIPPED_COUNT": "$TEST_SKIPPED_COUNT",
        "TEST_OVERALL_STATUS": "$TEST_OVERALL_STATUS",
        "TEST_FAILURE_RATE": "$TEST_FAILURE_RATE",
        "TEST_COVERAGE": "$TEST_COVERAGE",
        "EXECUTION_DATE": "$EXECUTION_DATE",
        "ENVIRONMENT_NAME": "${ENVIRONMENT_NAME:-Unknown}",
        "ATP_REPORT_VIEW_UI_URL": "$ATP_REPORT_VIEW_UI_URL",
        "ALLURE_REPORT_URL": "$ALLURE_REPORT_URL",
        "TIMESTAMP": "$TIMESTAMP"
    },
    "environment_variables_description": {
        "description": "Variables used in email notification json file",
        "variables": {
            "TEST_OVERALL_STATUS": "Overall test status (PASSED/PARTIAL/FAILED)",
            "TEST_PASS_RATE": "Pass rate percentage with 2 decimal places",
            "TEST_TOTAL_COUNT": "Total number of tests",
            "TEST_PASSED_COUNT": "Number of passed tests",
            "TEST_FAILED_COUNT": "Number of failed tests",
            "TEST_SKIPPED_COUNT": "Number of skipped tests",
            "TEST_FAILURE_RATE": "Failure rate percentage",
            "TEST_COVERAGE": "Test coverage percentage",
            "EXECUTION_DATE": "Test execution date and time",
            "ENVIRONMENT_NAME": "Environment name (dev/staging/prod)",
            "ATP_REPORT_VIEW_UI_URL": "Base URL for viewing reports",
            "ALLURE_REPORT_URL": "Full URL to Allure report",
            "TIMESTAMP": "Current timestamp",
            "TEST_DETAILS": "Details of all tests"
        }
    },
    "status_logic": {
        "description": "Logic for determining overall test status",
        "rules": {
            "PASSED": "100% of tests passed successfully",
            "PARTIAL": "80-99% of tests passed successfully",
            "FAILED": "Less than 80% of tests passed successfully"
        }
    }
}
EOF
    )

    # Write the generated JSON to output file
    printf "%s" "$json_content" >"$output_file"

    log_info "JSON generated successfully: $output_file"

    # Export the JSON content as environment variable for use in other scripts
    export GENERATED_JSON="$json_content"
    export JSON_FILE="$output_file"

    log_info "Environment variables exported: GENERATED_JSON, JSON_FILE"

    # Return the JSON content
    # echo "$json_content"
}
