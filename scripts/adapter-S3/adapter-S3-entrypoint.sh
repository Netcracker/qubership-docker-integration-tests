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
echo " S3 bucket: ${ATP_STORAGE_BUCKET:-<not set>}"
echo " S3 provider: ${ATP_STORAGE_PROVIDER:-<not set>}"
echo " S3 API host: ${ATP_STORAGE_SERVER_URL:-<not set>}"
echo " S3 UI URL: ${ATP_STORAGE_SERVER_UI_URL:-<not set>}"
echo " Environment name: $ENVIRONMENT_NAME"

# Import modular components
source "${ROBOT_HOME}/scripts/adapter-S3/init.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/test-runner.sh"
source "${ROBOT_HOME}/scripts/adapter-S3/upload-monitor.sh"

# Execute main workflow
echo " Starting test execution workflow..."

# Store all arguments passed to this script
echo " Robot arguments: $*"

# Initialize environment
init_environment

# Start upload monitoring only if S3 is enabled
if [[ -n "${ATP_STORAGE_BUCKET}" ]]; then
    start_upload_monitoring
else
    echo "️ Skipping upload monitoring (S3 integration disabled)"
fi

# Run tests
run_tests "$@"

# Finalize upload only if S3 is enabled
if [[ -n "${ATP_STORAGE_BUCKET}" ]]; then
    finalize_upload
else
    echo "️ Skipping upload finalization (S3 integration disabled)"
    echo " Test results are available locally at: $TMP_DIR"
fi

echo " Test job finished successfully!"
