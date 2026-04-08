#!/bin/bash

# atpReport.enabled (Helm) -> ATP_REPORT_ENABLED: only "true" or "false"
: "${ATP_REPORT_ENABLED:=false}"

atp_report_upload_enabled() {
    [[ "${ATP_REPORT_ENABLED}" == "true" ]]
}

# Environment initialization module
init_environment() {
    echo "Initializing environment..."

    # Compute current date and time
    if [[ -z "${CURRENT_DATE}" ]]; then
        CURRENT_DATE=$(date +%F) # e.g., 2025-04-07
    fi
    if [[ -z "${CURRENT_TIME}" ]]; then
        CURRENT_TIME=$(date +%H-%M-%S) # e.g., 11-48-00
    fi

    # ATP report upload to S3: requires ATP_REPORT_ENABLED=true and ATP_STORAGE_BUCKET
    if atp_report_upload_enabled; then
        if [[ -z "${ATP_STORAGE_BUCKET}" ]]; then
            echo "ERROR: ATP_REPORT_ENABLED is true but ATP_STORAGE_BUCKET is not set"
            exit 1
        fi
        echo "ATP report upload to S3 enabled (bucket: ${ATP_STORAGE_BUCKET})"

        # Configure AWS S3 parameters (required when upload is enabled) - using local variables for security
        if [[ -z "${ATP_STORAGE_USERNAME}" ]]; then
            echo "ERROR: ATP_STORAGE_USERNAME is required but not set"
            exit 1
        fi
        if [[ -z "${ATP_STORAGE_PASSWORD}" ]]; then
            echo "ERROR: ATP_STORAGE_PASSWORD is required but not set"
            exit 1
        fi

        # Store credentials in local variables (not exported to environment)
        _LOCAL_S3_KEY="$ATP_STORAGE_USERNAME"
        _LOCAL_S3_SECRET="$ATP_STORAGE_PASSWORD"
        export AWS_ACCESS_KEY_ID="$_LOCAL_S3_KEY"
        export AWS_SECRET_ACCESS_KEY="$_LOCAL_S3_SECRET"

        # Configure additional s5cmd settings for MinIO only
        if [[ "${ATP_STORAGE_PROVIDER}" == "minio" || "${ATP_STORAGE_PROVIDER}" == "s3" ]]; then
            export AWS_ENDPOINT_URL="${ATP_STORAGE_SERVER_URL}"
            export AWS_REGION="${ATP_STORAGE_REGION}" # Required by s5cmd even for MinIO
            export AWS_NO_VERIFY_SSL="true"           # Optional: disable SSL verification
        fi
    else
        echo "WARNING: ATP report upload to S3 disabled (set ATP_REPORT_ENABLED=true to enable)"
        if [[ -n "${ATP_STORAGE_BUCKET}" ]]; then
            echo "INFO: ATP_STORAGE_BUCKET is set (${ATP_STORAGE_BUCKET}) but uploads remain disabled until ATP_REPORT_ENABLED=true"
        fi
    fi

    # Define temp clone path
    export TMP_DIR="/tmp/clone"
    mkdir -p "$TMP_DIR"

    # Remove previous contents if any
    rm -rf "${TMP_DIR:?}/"*

    export ALLURE_RESULTS_DIR="${ROBOT_HOME}/output/allure-results"
    mkdir -p "${ALLURE_RESULTS_DIR}"

    echo "SUCCESS: Environment initialized successfully"
}
