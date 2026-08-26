#!/bin/bash
set -e

# Main test job entrypoint script - coordinates all modules
echo " Starting test job entrypoint script..."
echo " Working directory: $(pwd)"
echo " Timestamp: $(date)"

# Set default upload method
export UPLOAD_METHOD="${UPLOAD_METHOD:-sync}"
echo " Upload method: $UPLOAD_METHOD"
echo " Report view host URL: $ATP_REPORT_VIEW_UI_URL"
echo " ATP report upload enabled (atpReport.enabled -> ATP_REPORT_ENABLED): ${ATP_REPORT_ENABLED:-false}"
echo " S3 bucket: ${ATP_STORAGE_BUCKET:-<not set>}"
echo " S3 provider: ${ATP_STORAGE_PROVIDER:-<not set>}"
echo " S3 API host: ${ATP_STORAGE_SERVER_URL:-<not set>}"
echo " S3 UI URL: ${ATP_STORAGE_SERVER_UI_URL:-<not set>}"
echo " Environment name: $ENVIRONMENT_NAME"

# Import modular components
source "${ROBOT_HOME}/scripts/adapter-S3/error-handler.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/init.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/test-runner.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/upload-monitor.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/email-notification/generate-email-notification-json.sh"

# Execute main workflow
echo " Starting test execution workflow..."

# Store all arguments passed to this script
echo " Robot arguments: $*"

# finalize_once() is defined in error-handler.sh (sourced above).
# Register it here after all scripts are sourced so every function it calls is available.
trap 'finalize_once' EXIT

# Initialize environment
init_environment

# Start upload monitoring only when publishing to S3 (bucket set)
if atp_report_upload; then
    start_upload_monitoring
else
    echo " Skipping upload monitoring (no bucket — results stay local)"
fi

# Run tests
run_tests "$@" || fail "Test runner failed"

echo " Test job finished successfully!"
