#!/bin/bash

# Calculate Test Pass Rate from Allure Results
#
# This script analyzes test results from allure-results directory
# and calculates the overall pass rate, then exports it as environment variable
#
# Dependencies:
# - jq (for JSON parsing)
# - bc (for floating point calculations)

set -eo pipefail

# Logging functions
log_info() {
    echo "INFO: $1"
}

log_success() {
    echo "SUCCESS: $1"
}

log_warning() {
    echo "WARNING: $1"
}

log_error() {
    echo "ERROR: $1"
}

# Get script directory (exported for potential external use)
# shellcheck disable=SC2034
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default allure-results directory (now in parent directory)
ALLURE_RESULTS_DIR="${1:-/tmp/clone/allure-results}"

# Check if allure-results directory exists
if [ ! -d "$ALLURE_RESULTS_DIR" ]; then
    log_error "Allure results directory not found: $ALLURE_RESULTS_DIR"
    exit 1
fi

# Check if jq is available
if ! command -v jq &>/dev/null; then
    log_error "jq is required but not installed. Please install jq to parse JSON files."
    exit 1
fi

# Check if bc is available, if not we'll use awk for calculations
BC_AVAILABLE=false
if command -v bc &>/dev/null; then
    BC_AVAILABLE=true
fi

log_info "Analyzing test results from: $ALLURE_RESULTS_DIR"

# Initialize counters
total_tests=0
passed_tests=0
failed_tests=0
skipped_tests=0

# Initialize test details arrays
declare -a test_details=()
# Add table header
test_details+=("$(printf "%-12s" "Status") | Test Name")
test_details+=("------------ | ------------------------------------------------------------")

# Process each result file
for result_file in "$ALLURE_RESULTS_DIR"/*-result.json; do
    if [ -f "$result_file" ]; then
        log_info "Processing: $(basename "$result_file")"

        # Extract test status using jq
        status=$(jq -r '.status' "$result_file" 2>/dev/null || echo "unknown")
        test_name=$(jq -r '.name' "$result_file" 2>/dev/null || echo "Unknown Test")

        case "$status" in
        "passed")
            passed_tests=$((passed_tests + 1))
            log_success "PASSED: $test_name"
            test_details+=("PASSED       | $test_name")
            ;;
        "failed")
            failed_tests=$((failed_tests + 1))
            log_error "FAILED: $test_name"
            test_details+=("FAILED       | $test_name")
            ;;
        "skipped")
            skipped_tests=$((skipped_tests + 1))
            log_warning "SKIPPED: $test_name"
            test_details+=("SKIPPED      | $test_name")
            ;;
        *)
            log_warning "? $test_name (status: $status)"
            test_details+=("UNKNOWN      | $test_name")
            ;;
        esac

        total_tests=$((total_tests + 1))
    fi
done

# Calculate pass rate
if [ $total_tests -eq 0 ]; then
    log_error "No test results found in $ALLURE_RESULTS_DIR"
    exit 1
fi

# Calculate pass rate as percentage (passed / total * 100)
if [ "$BC_AVAILABLE" = true ]; then
    pass_rate=$(echo "scale=2; $passed_tests * 100 / $total_tests" | bc)
    pass_rate_rounded=$(echo "scale=0; $passed_tests * 100 / $total_tests" | bc)
else
    # Use awk for calculations if bc is not available
    pass_rate=$(awk "BEGIN {printf \"%.2f\", $passed_tests * 100 / $total_tests}")
    pass_rate_rounded=$(awk "BEGIN {printf \"%.0f\", $passed_tests * 100 / $total_tests}")
fi

# Determine overall status
if [ "$pass_rate_rounded" -eq 100 ]; then
    overall_status="PASSED"
elif [ "$pass_rate_rounded" -ge 80 ]; then
    overall_status="PARTIAL"
else
    overall_status="FAILED"
fi

# Export results as environment variables
export TEST_PASS_RATE="$pass_rate"
export TEST_PASS_RATE_ROUNDED="$pass_rate_rounded"
export TEST_TOTAL_COUNT="$total_tests"
export TEST_PASSED_COUNT="$passed_tests"
export TEST_FAILED_COUNT="$failed_tests"
export TEST_SKIPPED_COUNT="$skipped_tests"
export TEST_OVERALL_STATUS="$overall_status"

# Create test details string
TEST_DETAILS_STRING=""
for test_detail in "${test_details[@]}"; do
    if [ -n "$TEST_DETAILS_STRING" ]; then
        TEST_DETAILS_STRING="$TEST_DETAILS_STRING\n$test_detail"
    else
        TEST_DETAILS_STRING="$test_detail"
    fi
done
export TEST_DETAILS_STRING="$TEST_DETAILS_STRING"

# Display summary
echo ""
log_info "=== Test Results Summary ==="
echo "Overall Status: $overall_status"
echo "Pass Rate: ${pass_rate}%"
echo "Total Tests: $total_tests"
echo "Passed: $passed_tests"
echo "Failed: $failed_tests"
echo "Skipped: $skipped_tests"
echo ""

# Export variables for use in other scripts
log_info "Environment variables exported:"
echo "TEST_PASS_RATE=$pass_rate"
echo "TEST_PASS_RATE_ROUNDED=$pass_rate_rounded"
echo "TEST_TOTAL_COUNT=$total_tests"
echo "TEST_PASSED_COUNT=$passed_tests"
echo "TEST_FAILED_COUNT=$failed_tests"
echo "TEST_SKIPPED_COUNT=$skipped_tests"
echo "TEST_OVERALL_STATUS=$overall_status"
echo "TEST_DETAILS_STRING=<multiline string with test details>"

log_success "Pass rate calculation completed successfully"
