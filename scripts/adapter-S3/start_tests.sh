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
ALLURE_OUTPUT_DIR="${OUTPUT_DIR}/allure-results"
mkdir -p "${ALLURE_OUTPUT_DIR}"

robot --output "${OUTPUT_DIR}/output.xml" \
    --log "${OUTPUT_DIR}/log.html" \
    --report "${OUTPUT_DIR}/report.html" \
    --listener "allure_robotframework;${ALLURE_OUTPUT_DIR}" \
    "$@"

# Capture the exit code from the script
exit_code=$?

# Copy output.xml to TMP_DIR for S3 upload
cp "${OUTPUT_DIR}/output.xml" "${TMP_DIR}/output.xml" 2>/dev/null || true

if [[ -n "${TMP_DIR:-}" ]] && [[ -d "${ALLURE_OUTPUT_DIR}" ]]; then
    mkdir -p "${TMP_DIR}/allure-results"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete "${ALLURE_OUTPUT_DIR}/" "${TMP_DIR}/allure-results/"
    else
        rm -rf "${TMP_DIR:?}/allure-results"
        mkdir -p "${TMP_DIR}/allure-results"
        cp -a "${ALLURE_OUTPUT_DIR}/." "${TMP_DIR}/allure-results/"
    fi
fi

# Exit the shell script with the same exit code
exit $exit_code
