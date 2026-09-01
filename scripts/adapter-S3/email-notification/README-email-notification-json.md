# JSON Test Results Generator

This set of scripts is designed to analyze test results from the `allure-results` folder and generate JSON files with test results in a predefined format.

## Files

### Main Scripts

1. **`calculate-email-notification-variables.sh`** - Main script for calculating test pass rate (shared with text version)
2. **`generate-email-notification-json.sh`** - Script for generating JSON file with test results

## Requirements

- Git Bash (for Windows) or Linux/macOS with Bash
- `jq` (for JSON parsing)
- `awk` (for calculations and placeholder replacement)

## Usage

### 1. Generating JSON Results

```bash
# Using Git Bash on Windows
& "C:\Program Files\Git\bin\bash.exe" email-notification/generate-email-notification-json.sh

# On Linux/macOS
./email-notification/generate-email-notification-json.sh
```

### 2. Combined Usage

```bash
# First, calculate pass rate
& "C:\Program Files\Git\bin\bash.exe" email-notification/calculate-email-notification-variables.sh

# Then generate JSON
& "C:\Program Files\Git\bin\bash.exe" email-notification/generate-email-notification-json.sh
```

## Exported Variables

After executing `generate-email-notification-json.sh`, the following environment variables are available:

- `JSON_FILE` - Path to the JSON results file (read content with `jq`/`cat`; not exported as env to avoid ARG_MAX limits)

Full JSON content is **not** exported as an environment variable; use `$JSON_FILE`.

## Environment Variables

The script uses the following environment variables for JSON generation:

- `TEST_OVERALL_STATUS` - Overall status
- `TEST_PASS_RATE` - Pass rate as percentage (number)
- `TEST_PASS_RATE_ROUNDED` - Rounded pass rate (number)
- `TEST_TOTAL_COUNT` - Total number of tests
- `TEST_PASSED_COUNT` - Number of passed tests
- `TEST_FAILED_COUNT` - Number of failed tests
- `TEST_SKIPPED_COUNT` - Number of skipped tests
- `TEST_FAILURE_RATE` - Failure rate percentage
- `TEST_COVERAGE` - Test coverage
- `EXECUTION_DATE` - Execution date
- `ENV_NAME` - Environment name
- `REPORT_VIEW_HOST_URL` - Host for viewing reports
- `ALLURE_REPORT_URL` - Path to reports folder
- `TIMESTAMP` - Timestamp
- `TEST_DETAILS_FILE` - Path to text file with test details (for email templates; avoids ARG_MAX on large runs)
- `TEST_DETAILS_STRING` - **Deprecated.** Legacy fallback only; do not use on large runs

## Generated JSON Structure

```json
{
  "test_results": {
    "overall_status": "PARTIAL",
    "pass_rate": 85.50,
    "pass_rate_rounded": 86,
    "total_count": 20,
    "passed_count": 17,
    "failed_count": 2,
    "skipped_count": 1,
    "failure_rate": 10.00,
    "coverage": 100.00
  },
  "execution_info": {
    "execution_date": "2024-01-15 14:30:25",
    "timestamp": "2024-01-15 14:30:25 UTC",
    "env_name": "staging",
    "report_view_host_url": "https://reports.example.com",
    "allure_report_url": "https://reports.example.com/Report/staging/2024-01-15/14-30-25/allure-report/index.html"
  },
  "test_details": [
    {
      "status": "PASSED",
      "test_name": "User Login Test",
      "emoji": "✅"
    }
  ],
  "environment_variables": {},
  "environment_variables_description": {},
  "status_logic": {}
}
```

## Integration with Other Scripts

Scripts can be integrated into other Bash scripts:

### Option 1: Using Function (Recommended)

```bash
#!/bin/bash

# Load script with function
source ./email-notification/generate-email-notification-json.sh

# Call the function
json_content=$(generate_email_notification_json)

# Use the result
echo "$json_content"

# Or use exported path and read file
echo "JSON file: $JSON_FILE"
jq . "$JSON_FILE"

# File will be saved to: ../email-notification-generated/email-notification-results-generated.json
```

### Function Parameters

The `generate_email_notification_json` function does not accept parameters.

**Note:**
- Allure results folder is always used by default: `./allure-results`
- Output file is always named `email-notification-results-generated.json` and saved in the `email-notification-generated` directory one level above the `email-notification` folder.

### Return Values

The function writes JSON to disk and exports:
- **Environment variable `JSON_FILE`** - path to JSON file (consumers read file; JSON is not stored in env)

The full payload is built with `jq` (`--arg` / `--argjson`), so special characters in test names, URLs, and environment names are JSON-escaped. After writing, the file is validated with `jq empty`; on failure the generator logs an error, best-effort writes a minimal valid `FAILED` payload, and returns non-zero (callers inside the EXIT trap must not call `fail`).

Optional path overrides for local/regression runs:
- `ALLURE_RESULTS_DIR`
- `EMAIL_NOTIFICATION_OUTPUT_DIR`

Regression check (quoted test names):

```bash
./email-notification/verify-json-escaping.sh
```

## Differences from Text Version

1. **Output Format**: JSON instead of text
2. **Structured Data**: All data is organized into logical blocks
3. **Test Array**: Test details are represented as a JSON array of objects
4. **Data Types**: Numeric values are passed as numbers, not strings
5. **Metadata**: Variable descriptions and status logic are included
6. **No Templates**: JSON is generated directly without using template files
