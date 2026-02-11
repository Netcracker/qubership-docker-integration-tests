#!/bin/bash

# Store robot arguments passed to this script
echo "Using robot arguments: $*"

# Use absolute path for output directory
OUTPUT_DIR="${ROBOT_HOME}/output"

# Create output directory for analyze_result.py compatibility
echo "Creating output directory: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Execute the script, generate robot and allure results with passed arguments
# Note: output.xml goes to ${OUTPUT_DIR}/ for analyze_result.py
#       allure-results go to $TMP_DIR for S3 upload
robot --output "${OUTPUT_DIR}/output.xml" \
    --log "${TMP_DIR}/log.html" \
    --report "${TMP_DIR}/report.html" \
    --listener "allure_robotframework;${TMP_DIR}/allure-results" \
    "$@"

# Capture the exit code from the script
exit_code=$?

# Copy output.xml to TMP_DIR for S3 upload
cp "${OUTPUT_DIR}/output.xml" "${TMP_DIR}/output.xml" 2>/dev/null || true

# Exit the shell script with the same exit code
exit $exit_code
