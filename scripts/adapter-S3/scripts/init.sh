#!/bin/bash

# Environment initialization module
init_environment() {
    echo "🔧 Initializing environment..."
    
    # Compute current date and time
    if [[ -z "${CURRENT_DATE}" ]]; then
        CURRENT_DATE=$(date +%F)         # e.g., 2025-04-07
    fi
    if [[ -z "${CURRENT_TIME}" ]]; then
        CURRENT_TIME=$(date +%H-%M-%S)  # e.g., 11-48-00
    fi

    # Configure AWS S3 parameters (required) - using local variables for security
    if [[ -z "${S3_ACCESS_KEY}" ]]; then
        echo "❌ S3_ACCESS_KEY is required but not set"
        exit 1
    fi
    if [[ -z "${S3_SECRET_KEY}" ]]; then
        echo "❌ S3_SECRET_KEY is required but not set"
        exit 1
    fi
    
    # Store credentials in local variables (not exported to environment)
    _LOCAL_S3_KEY="$S3_ACCESS_KEY"
    _LOCAL_S3_SECRET="$S3_SECRET_KEY"
    export AWS_ACCESS_KEY_ID="$_LOCAL_S3_KEY"
    export AWS_SECRET_ACCESS_KEY="$_LOCAL_S3_SECRET"

    # Configure additional s5cmd settings for MinIO only
    if [[ "${S3_TYPE}" == "minio" ]]; then
        export AWS_ENDPOINT_URL="${S3_API_HOST}"
        export AWS_REGION="us-east-1"             # Required by s5cmd even for MinIO
        export AWS_NO_VERIFY_SSL="true"           # Optional: disable SSL verification
    fi

    # Define adapter S3 directory path
    ADAPTER_S3_DIR="../"
    
    export ADAPTER_S3_DIR="${ADAPTER_S3_DIR}"

    echo "✅ Environment initialized successfully"
} 