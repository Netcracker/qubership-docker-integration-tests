#!/bin/bash

# Calculate Test Pass Rate from Allure Results
#
# This script analyzes test results from allure-results directory
# and calculates the overall pass rate, then exports it as environment variable
#
# Dependencies:
# - jq (for JSON parsing)
# - bc (for floating point calculations)

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

# shellcheck disable=SC2034
# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default allure-results directory (now in parent directory)
ALLURE_RESULTS_DIR="${1:-/tmp/clone/allure-results}"

# Check if allure-results directory exists
if [ ! -d "$ALLURE_RESULTS_DIR" ]; then
    log_error "Allure results directory not found: $ALLURE_RESULTS_DIR"
    return 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed. Please install jq to parse JSON files."
    return 1
fi

# Check if bc is available, if not we'll use awk for calculations
BC_AVAILABLE=false
if command -v bc &> /dev/null; then
    BC_AVAILABLE=true
fi

log_info "Analyzing test results from: $ALLURE_RESULTS_DIR"

# Initialize counters
total_tests=0
passed_tests=0
failed_tests=0
skipped_tests=0

# Stream test details to file (avoids ARG_MAX from giant in-memory strings)
TEST_DETAILS_DIR="/tmp/clone/scripts/email-notification-generated"
mkdir -p "$TEST_DETAILS_DIR"
TEST_DETAILS_FILE="$TEST_DETAILS_DIR/test-details.txt"
{
    printf '%s | Test Name\n' "$(printf '%-12s' "Status")"
    printf '%s\n' "------------ | ------------------------------------------------------------"
} > "$TEST_DETAILS_FILE"

# ponytail: one jq pass instead of N shell forks; duplicate filter also in generate script
shopt -s nullglob
result_files=("$ALLURE_RESULTS_DIR"/*-result.json)
shopt -u nullglob

aggregated="[]"
if [ ${#result_files[@]} -gt 0 ]; then
    aggregated=$(jq -s '
        group_by(
            if (.historyId // "") != "" then .historyId
            elif (.fullName // "") != "" then .fullName
            else .uuid end
        )
        | map(
            (max_by(.stop // .start // 0)) as $w |
            { name: $w.name, status: $w.status, retries: (length - 1) }
        )
    ' "${result_files[@]}")
fi

while IFS= read -r row; do
    status=$(jq -r '.status' <<< "$row")
    test_name=$(jq -r '.name' <<< "$row")
    retries=$(jq -r '.retries' <<< "$row")
    test_name=$(printf '%s' "$test_name" | jq -R .)
    test_name=${test_name:1:-1}

    retry_hint=""
    if [ "$retries" -gt 0 ]; then
        if [ "$retries" -eq 1 ]; then
            retry_hint=" (1 retry)"
        else
            retry_hint=" ($retries retries)"
        fi
    fi

    log_info "Processing: $test_name"
    case "$status" in
        "passed")
            passed_tests=$((passed_tests + 1))
            log_success "✓ $test_name"
            printf '%s\n' "✅ PASSED${retry_hint} | $test_name" >> "$TEST_DETAILS_FILE"
            ;;
        "failed")
            failed_tests=$((failed_tests + 1))
            log_error "✗ $test_name"
            printf '%s\n' "❌ FAILED${retry_hint} | $test_name" >> "$TEST_DETAILS_FILE"
            ;;
        "skipped")
            skipped_tests=$((skipped_tests + 1))
            log_warning "⚠ $test_name"
            printf '%s\n' "⚠️ SKIPPED${retry_hint} | $test_name" >> "$TEST_DETAILS_FILE"
            ;;
        *)
            log_warning "? $test_name (status: $status)"
            printf '%s\n' "❓ UNKNOWN${retry_hint} | $test_name" >> "$TEST_DETAILS_FILE"
            ;;
    esac

    total_tests=$((total_tests + 1))
done < <(jq -c '.[]' <<< "$aggregated")

# Calculate pass rate
if [ $total_tests -eq 0 ]; then
    log_error "No test results found in $ALLURE_RESULTS_DIR"
    return 1
fi

# Calculate pass rate as percentage (passed / (total - skipped) * 100)
effective_total=$(( total_tests - skipped_tests ))
if [ "$BC_AVAILABLE" = true ]; then
    pass_rate=$(echo "scale=2; $passed_tests * 100 / $effective_total" | bc)
    pass_rate_rounded=$(echo "scale=0; $passed_tests * 100 / $effective_total" | bc)
else
    # Use awk for calculations if bc is not available
    pass_rate=$(awk -v p="$passed_tests" -v t="$effective_total" \
    'BEGIN { if (t > 0) printf "%.2f", p * 100 / t; else print "0.00" }')
    pass_rate_rounded=$(awk -v p="$passed_tests" -v t="$effective_total" \
    'BEGIN { if (t > 0) printf "%.0f", p * 100 / t; else print "0" }')
fi

expected_pass_rate=${EXPECTED_PASS_RATE:-80}

if (( pass_rate_rounded == 100 )); then
    overall_status="PASSED"
elif (( pass_rate_rounded >= expected_pass_rate )); then
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

export TEST_DETAILS_FILE
unset TEST_DETAILS_STRING

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
echo "TEST_DETAILS_FILE=$TEST_DETAILS_FILE"

log_success "Pass rate calculation completed successfully"
