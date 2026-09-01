# Test Pass Rate Calculator

This set of scripts is designed to analyze test results from the `allure-results` folder and generate reports with pass rate.

## Files

### Main Scripts

1. **`calculate-email-notification-variables.sh`** - Main script for calculating test pass rate
2. **`generate-email-notification-file.sh`** - Script for generating message from template
3. **`email-notification-body-template.txt`** - Email notification template

### Auxiliary Files

- **`message-template.msg`** - Extended template with conditional blocks (not used in final version)
- **`generate-message.sh`** - Script for generating message from template

## Requirements

- Git Bash (for Windows) or Linux/macOS with Bash
- `jq` (for JSON parsing)
- `awk` (for calculations and placeholder replacement)

## Usage

### 1. Calculating Pass Rate

```bash
# Using Git Bash on Windows
& "C:\Program Files\Git\bin\bash.exe" email-notification/calculate-email-notification-variables.sh

# On Linux/macOS
./email-notification/calculate-email-notification-variables.sh
```

The script analyzes all `*-result.json` files in the `allure-results` folder and outputs:
- Overall status (PASSED/PARTIAL/FAILED)
- Pass rate as percentage
- Number of tests by status
- Exports environment variables

### 2. Generating Message

```bash
# Using Git Bash on Windows
& "C:\Program Files\Git\bin\bash.exe" email-notification/generate-email-notification-file.sh

# With template specified
& "C:\Program Files\Git\bin\bash.exe" email-notification/generate-email-notification-file.sh "./email-notification/email-notification-body-template.txt"

# On Linux/macOS
./email-notification/generate-email-notification-file.sh
```

### 3. Combined Usage

```bash
# First, calculate pass rate
& "C:\Program Files\Git\bin\bash.exe" email-notification/calculate-email-notification-variables.sh

# Then generate message
& "C:\Program Files\Git\bin\bash.exe" email-notification/generate-email-notification-file.sh
```

## Exported Variables

After executing `calculate-email-notification-variables.sh`, the following environment variables are available:

- `TEST_PASS_RATE` - Pass rate with two decimal places (e.g., "50.00")
- `TEST_PASS_RATE_ROUNDED` - Rounded pass rate (e.g., "50")
- `TEST_TOTAL_COUNT` - Total number of unique test cases (retries deduplicated by `historyId`)
- `TEST_PASSED_COUNT` - Number of passed tests
- `TEST_FAILED_COUNT` - Number of failed tests
- `TEST_SKIPPED_COUNT` - Number of skipped tests
- `TEST_OVERALL_STATUS` - Overall status (PASSED/PARTIAL/FAILED)

After executing `generate-email-notification-file.sh`, the following are additionally available:

- `GENERATED_MESSAGE` - Content of the generated message
- `MESSAGE_FILE` - Path to the message file

## Template Placeholders

The following placeholders are used in the `email-notification-body-template.txt` file:

- `{{TEST_OVERALL_STATUS}}` - Overall status
- `{{TEST_PASS_RATE}}` - Pass rate as percentage
- `{{TEST_TOTAL_COUNT}}` - Total number of tests
- `{{TEST_PASSED_COUNT}}` - Number of passed tests
- `{{TEST_FAILED_COUNT}}` - Number of failed tests
- `{{TEST_SKIPPED_COUNT}}` - Number of skipped tests
- `{{TEST_FAILURE_RATE}}` - Failure rate percentage
- `{{TEST_COVERAGE}}` - Test coverage
- `{{EXECUTION_DATE}}` - Execution date
- `{{ENVIRONMENT_NAME}}` - Environment name
- `{{ATP_REPORT_VIEW_UI_URL}}` - Host for viewing reports
- `{{ALLURE_REPORT_URL}}` - Path to reports folder
- `{{TIMESTAMP}}` - Timestamp
- `{{TEST_DETAILS}}` - List of all tests with their statuses

## Status Determination Logic

- **PASSED** - 100% of tests passed successfully
- **PARTIAL** - 80-99% of tests passed successfully
- **FAILED** - Less than 80% of tests passed successfully

## Retry Deduplication

Playwright retries write one `*-result.json` file per attempt. Scripts group results by `historyId` (falling back to `fullName`, then `uuid`) and keep the latest attempt (`max_by(stop)`). `TEST_TOTAL_COUNT` reflects unique test cases, not raw result files.

Detail lines show retry count when applicable, e.g. `✅ PASSED (1 retry) | Test name`.

## Example Output

```log
ℹ️ Analyzing test results from: /tmp/clone/allure-results
ℹ️ Processing: Comprehensive Jira integration test @pipeline_job
✅ ✓ Comprehensive Jira integration test @pipeline_job

ℹ️ === Test Results Summary ===
Overall Status: PASSED
Pass Rate: 100.00%
Total Tests: 1
Passed: 1
Failed: 0
Skipped: 0
```

(One test that failed on first attempt and passed on retry produces two result files but counts as one test at 100% pass rate, with `(1 retry)` in the detail line.)

## Integration with Other Scripts

Scripts can be integrated into other Bash scripts:

### Option 1: Using Function (Recommended)

```bash
#!/bin/bash

# Load script with function
source ./email-notification/generate-email-notification-file.sh

# Call the function with parameters
message_content=$(generate_email_notification_file \
    "./email-notification/email-notification-body-template.txt")

# Use the result
echo "$message_content"

# Or use exported variables
echo "Message file: $MESSAGE_FILE"
echo "Content: $GENERATED_MESSAGE"

# File will be saved to: ../email-notification-generated/email-notification-body-template-generated.txt
```

### Option 2: Using source (Deprecated Method)

```bash
#!/bin/bash

# Load pass rate calculation results
source ./email-notification/calculate-email-notification-variables.sh

# Use variables
echo "Pass rate: $TEST_PASS_RATE%"
echo "Status: $TEST_OVERALL_STATUS"

# Generate message
source ./email-notification/generate-email-notification-body-message.sh

# Use generated message
echo "$GENERATED_MESSAGE"
```

### Function Parameters

The `generate_email_notification_file` function accepts the following parameters:

1. **template_file** (optional) - path to template file
   - Default: `./email-notification/email-notification-body-template.txt`

**Note:**
- Allure results folder is always used by default: `./allure-results`
- Output filename is automatically generated based on the template name. The file is saved in the `email-notification-generated` directory one level above the `email-notification` folder. For example, if the template is named `my-template.txt`, the output file will be `../email-notification-generated/my-template-generated.txt`.

### Return Values

The function returns:
- **Generated message content** (output to stdout)
- **Environment variable `GENERATED_MESSAGE`** - message content
- **Environment variable `MESSAGE_FILE`** - path to message file
