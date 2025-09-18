#!/bin/bash
set -e

# Main test job entrypoint script - coordinates all modules
echo "🔧 Starting test job entrypoint script..."
echo "📁 Working directory: $(pwd)"
echo "📅 Timestamp: $(date)"

# Set default upload method
export UPLOAD_METHOD="${UPLOAD_METHOD:-sync}"
echo "📤 Upload method: $UPLOAD_METHOD"

# export REPORT_VIEW_HOST_URL="${REPORT_VIEW_HOST_URL:-https://atp3-results-test.kube23mdc.test}"
# export S3_BUCKET="${S3_BUCKET:-atp3-test}"
# export S3_TYPE="${S3_TYPE:-minio}"
# export S3_API_HOST="${S3_API_HOST:-https://atp3-mdc.s3.test}"
# export S3_UI_URL="${S3_UI_URL:-https://console.atp3-mdc.s3.test}"
# export ENV_NAME="${ENV_NAME:-CRQA1}"

export REPORT_VIEW_HOST_URL="https://atp3-results-test.kube23mdc.test"
export S3_BUCKET="qstp-consul"
export S3_TYPE="minio"
export S3_API_HOST="https://s3.amazonaws.com"
export S3_UI_URL="https://console.atp3-mdc.s3.test"
export ENV_NAME="consul"

echo "📦 S3 bucket: $S3_BUCKET"
echo "📦 S3 access key: $S3_ACCESS_KEY"
echo "📦 S3 secret key: $S3_SECRET_KEY"
echo "📦 S3 type: $S3_TYPE"
echo "📦 S3 API host: $S3_API_HOST"
echo "📦 S3 UI URL: $S3_UI_URL"
echo "📦 Environment name: $ENV_NAME"


# Import modular components
source ./init.sh
source ./test-runner.sh
source ./upload-monitor.sh

# Execute main workflow
echo "🚀 Starting test execution workflow..."

init_environment
start_upload_monitoring
run_tests
finalize_upload

echo "✅ Test job finished successfully!"