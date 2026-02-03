#!/bin/bash

# Generate Message from Template (Final Simplified Version)
# 
# This script generates a message file from a template by replacing placeholders
# with actual values from environment variables
#
# Usage: ./generate-email-notification-file.sh [template_file]
# 
# Dependencies:
# - calculate-email-notification-variables.sh (for test statistics)

set -eo pipefail

# Function to generate email notification body message
generate_email_notification_file() {
    local template_file="${1:-}"
    
    # Logging functions
    log_info() {
        echo "ℹ️ $1"
    }

    log_success() {
        echo "✅ $1"
    }

    log_warning() {
        echo "⚠️ $1"
    }

    log_error() {
        echo "❌ $1"
    }

    # Get script directory
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Set default values if not provided
    if [ -z "$template_file" ]; then
        template_file="$SCRIPT_DIR/email-notification-body-template.txt"
    fi
    
    # Set allure results directory to default location
    local allure_results_dir="/tmp/clone/allure-results"
    
    # Generate output file name based on template name
    local template_basename=$(basename "$template_file" .txt)
    
    # Create email-notification-generated directory one level up
    local output_dir="/tmp/clone/scripts/email-notification-generated"
    mkdir -p "$output_dir"
    
    local output_file="$output_dir/${template_basename}-generated.txt"

    # Check if template file exists
    if [ ! -f "$template_file" ]; then
        log_error "Template file not found: $template_file"
        log_warning "Skipping message generation - no output file will be created"
        return 0
    fi

    log_info "Generating message from template: $template_file"

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

    # Read template content
    local template_content=$(cat "$template_file")

    log_info "Replacing placeholders with actual values..."

    # Replace placeholders and handle conditional blocks using awk
    local message_content=$(echo "$template_content" | awk -v overall_status="$TEST_OVERALL_STATUS" \
        -v pass_rate="$TEST_PASS_RATE" \
        -v total_count="$TEST_TOTAL_COUNT" \
        -v passed_count="$TEST_PASSED_COUNT" \
        -v failed_count="$TEST_FAILED_COUNT" \
        -v skipped_count="$TEST_SKIPPED_COUNT" \
        -v failure_rate="$TEST_FAILURE_RATE" \
        -v coverage="$TEST_COVERAGE" \
        -v exec_date="$EXECUTION_DATE" \
        -v environment_name="${ENVIRONMENT_NAME:-Unknown}" \
        -v report_host_url="$ATP_REPORT_VIEW_UI_URL" \
        -v allure_report_url="$ALLURE_REPORT_URL" \
        -v timestamp="$TIMESTAMP" '
        BEGIN {
            in_conditional = 0
            conditional_type = ""
            skip_until_else = 0
            skip_until_end = 0
        }
        {
            # Handle conditional blocks
            if ($0 ~ /{{#if TEST_FAILED_COUNT}}/) {
                in_conditional = 1
                conditional_type = "failed"
                if (failed_count == 0) {
                    skip_until_else = 1
                }
                next
            }
            if ($0 ~ /{{#if TEST_PASSED_COUNT}}/) {
                in_conditional = 1
                conditional_type = "passed"
                if (passed_count == 0) {
                    skip_until_else = 1
                }
                next
            }
            if ($0 ~ /{{#if TEST_SKIPPED_COUNT}}/) {
                in_conditional = 1
                conditional_type = "skipped"
                if (skipped_count == 0) {
                    skip_until_else = 1
                }
                next
            }
            if ($0 ~ /{{else}}/) {
                if (in_conditional) {
                    if (skip_until_else) {
                        skip_until_else = 0
                        skip_until_end = 0
                    } else {
                        skip_until_end = 1
                    }
                }
                next
            }
            if ($0 ~ /{{\/if}}/) {
                in_conditional = 0
                conditional_type = ""
                skip_until_else = 0
                skip_until_end = 0
                next
            }
            
            # Skip lines if we are in a conditional block that should be skipped
            if (in_conditional && (skip_until_else || skip_until_end)) {
                next
            }
            
            # Replace placeholders
            gsub(/{{TEST_OVERALL_STATUS}}/, overall_status)
            gsub(/{{TEST_PASS_RATE}}/, pass_rate)
            gsub(/{{TEST_TOTAL_COUNT}}/, total_count)
            gsub(/{{TEST_PASSED_COUNT}}/, passed_count)
            gsub(/{{TEST_FAILED_COUNT}}/, failed_count)
            gsub(/{{TEST_SKIPPED_COUNT}}/, skipped_count)
            gsub(/{{TEST_FAILURE_RATE}}/, failure_rate)
            gsub(/{{TEST_COVERAGE}}/, coverage)
                    gsub(/{{EXECUTION_DATE}}/, exec_date)
        gsub(/{{ENVIRONMENT_NAME}}/, environment_name)
                gsub(/{{ATP_REPORT_VIEW_UI_URL}}/, report_host_url)
        gsub(/{{ALLURE_REPORT_URL}}/, allure_report_url)
        gsub(/{{TIMESTAMP}}/, timestamp)
            
        print
    }')

    # Replace TEST_DETAILS placeholder separately
    if [ -n "${TEST_DETAILS_STRING:-}" ]; then
        # Create temporary file with test details
        temp_details_file=$(mktemp)
        echo -e "$TEST_DETAILS_STRING" > "$temp_details_file"
        
        # Use sed with file input to replace placeholder
        message_content=$(echo "$message_content" | sed "/{{TEST_DETAILS}}/r $temp_details_file" | sed "/{{TEST_DETAILS}}/d")
        
        # Clean up temporary file
        rm -f "$temp_details_file"
    else
        message_content=$(echo "$message_content" | sed "s|{{TEST_DETAILS}}|No test details available|g")
    fi

    # Write the generated message to output file
    printf "%s" "$message_content" > "$output_file"

    log_success "Message generated successfully: $output_file"

    # Display the generated message
    echo ""
    #log_info "=== Generated Message Preview ==="
    #echo "$message_content"
    #echo ""

    # Export the message content as environment variable for use in other scripts
    export GENERATED_MESSAGE="$message_content"
    export MESSAGE_FILE="$output_file"

    log_info "Message content exported as GENERATED_MESSAGE environment variable"
    log_info "Message file path exported as MESSAGE_FILE environment variable"
    
    # Return the message content
    # echo "$message_content"
}

