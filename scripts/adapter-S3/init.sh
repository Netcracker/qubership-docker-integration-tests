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

    # Check if S3 integration is enabled (based on ATP_STORAGE_BUCKET)
    if [[ -n "${ATP_STORAGE_BUCKET}" ]]; then
        echo "📦 S3 integration enabled (bucket: ${ATP_STORAGE_BUCKET})"
        
        # Configure AWS S3 parameters (required when S3 is enabled) - using local variables for security
        if [[ -z "${ATP_STORAGE_USERNAME}" ]]; then
            echo "❌ ATP_STORAGE_USERNAME is required but not set"
            exit 1
        fi
        if [[ -z "${ATP_STORAGE_PASSWORD}" ]]; then
            echo "❌ ATP_STORAGE_PASSWORD is required but not set"
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
            export AWS_REGION="${ATP_STORAGE_REGION}"             # Required by s5cmd even for MinIO
            export AWS_NO_VERIFY_SSL="true"           # Optional: disable SSL verification
        fi
    else
        echo "⚠️ S3 integration disabled (ATP_STORAGE_BUCKET is not set)"
    fi

    # Define temp clone path
    export TMP_DIR="/tmp/clone"
    mkdir -p "$TMP_DIR"

    # Remove previous contents if any
    rm -rf "${TMP_DIR:?}/"*
    
    echo "✅ Environment initialized successfully"
}
