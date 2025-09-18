#!/bin/bash

# Event-based upload monitoring module
start_upload_monitoring() {
    echo "📡 Starting event-based upload monitoring..."
    
    # Prepare common S3 paths
    RESULTS_S3_PATH="s3://${S3_BUCKET}/Result/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/"
    REPORTS_S3_PATH="s3://${S3_BUCKET}/Report/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/"
    ATTACHMENTS_S3_PATH="${REPORTS_S3_PATH}attachments/"

    # Create attachments directory
    mkdir -p $ADAPTER_S3_DIR/results/allure-results
    mkdir -p $ADAPTER_S3_DIR/results/attachments
    
    # Store credentials for background processes (local variables, not exported)
    _BACKGROUND_S3_KEY="$_LOCAL_S3_KEY"
    _BACKGROUND_S3_SECRET="$_LOCAL_S3_SECRET"
    
    # Choose upload method based on environment variable
    if [[ "${UPLOAD_METHOD:-cp}" == "sync" ]]; then
        echo "🔄 Using sync-based upload monitoring (inotifywait + sync)"
        start_sync_uploader "$ADAPTER_S3_DIR/results/allure-results" "${RESULTS_S3_PATH}allure-results/" "*result.json" &
        start_sync_uploader "$ADAPTER_S3_DIR/results/attachments" "$ATTACHMENTS_S3_PATH" &
    else
        echo "📁 Using file-based upload monitoring (inotifywait + cp)"
        start_inotify_uploader "$ADAPTER_S3_DIR/results/allure-results" "${RESULTS_S3_PATH}allure-results/" "*result.json" &
        start_inotify_uploader "$ADAPTER_S3_DIR/results/attachments" "$ATTACHMENTS_S3_PATH" &
    fi
    
    echo "✅ Upload monitoring started"
}

# Inotify uploader function
start_inotify_uploader() {
    WATCH_DIR="$1"
    DEST_PATH="$2"
    FILE_PATTERN="${3:-*}"  # Optional filename filter (e.g. *result.json)

    echo "📡 Starting inotify uploader for $WATCH_DIR => $DEST_PATH (filter: $FILE_PATTERN)"

    # Pass credentials as environment variables only for this process
    inotifywait -m -e close_write,create --format '%w%f' "$WATCH_DIR" | while read NEW_FILE; do
        FILE_NAME=$(basename "$NEW_FILE")
        if [[ "$FILE_NAME" == $FILE_PATTERN ]]; then
            echo "🆕 Matching file: $FILE_NAME"
            upload_file_to_s3 "$NEW_FILE" "$DEST_PATH"
        else
            echo "⚠️ Ignored file: $FILE_NAME"
        fi
    done &
    
    # Store the background process PID
    INOTIFY_PID=$!
    echo "📡 Inotify process started with PID: $INOTIFY_PID"
}

# Upload file to S3/MinIO
upload_file_to_s3() {
    local FILE_PATH="$1"
    local DEST_PATH="$2"
    
    # Use background credentials for upload
    if [[ "$S3_TYPE" == "aws" ]]; then
        AWS_ACCESS_KEY_ID="$_BACKGROUND_S3_KEY" AWS_SECRET_ACCESS_KEY="$_BACKGROUND_S3_SECRET" s5cmd --no-verify-ssl cp "$FILE_PATH" "$DEST_PATH" > /dev/null 2>&1
    elif [[ "$S3_TYPE" == "minio" ]]; then
        AWS_ACCESS_KEY_ID="$_BACKGROUND_S3_KEY" AWS_SECRET_ACCESS_KEY="$_BACKGROUND_S3_SECRET" s5cmd --no-verify-ssl --endpoint-url "$S3_API_HOST" cp "$FILE_PATH" "$DEST_PATH" > /dev/null 2>&1
    fi
}

# Sync-based uploader function (triggered by inotifywait)
start_sync_uploader() {
    WATCH_DIR="$1"
    DEST_PATH="$2"
    FILE_PATTERN="${3:-*}"  # Optional filename filter

    echo "🔄 Starting sync uploader for $WATCH_DIR => $DEST_PATH (filter: $FILE_PATTERN)"

    # Pass credentials as environment variables only for this process
    inotifywait -m -e close_write,create --format '%w%f' "$WATCH_DIR" | while read NEW_FILE; do
        FILE_NAME=$(basename "$NEW_FILE")
        if [[ "$FILE_NAME" == $FILE_PATTERN ]]; then
            echo "🆕 Matching file: $FILE_NAME - triggering sync"
            sync_directory_to_s3 "$WATCH_DIR" "$DEST_PATH"
        #else
        #    echo "⚠️ Ignored file: $FILE_NAME"
        fi
    done &
    
    # Store the background process PID
    SYNC_PID=$!
    echo "🔄 Sync process started with PID: $SYNC_PID"
}

# Sync directory to S3/MinIO
sync_directory_to_s3() {
    local SOURCE_DIR="$1"
    local DEST_PATH="$2"
    
    # Use background credentials for sync
    if [[ "$S3_TYPE" == "aws" ]]; then
        AWS_ACCESS_KEY_ID="$_BACKGROUND_S3_KEY" AWS_SECRET_ACCESS_KEY="$_BACKGROUND_S3_SECRET" s5cmd --no-verify-ssl sync "$SOURCE_DIR/" "$DEST_PATH" > /dev/null 2>&1
    elif [[ "$S3_TYPE" == "minio" ]]; then
        AWS_ACCESS_KEY_ID="$_BACKGROUND_S3_KEY" AWS_SECRET_ACCESS_KEY="$_BACKGROUND_S3_SECRET" s5cmd --no-verify-ssl --endpoint-url "$S3_API_HOST" sync "$SOURCE_DIR/" "$DEST_PATH" > /dev/null 2>&1
    fi
}

# Finalize upload after tests
finalize_upload() {
    echo "🔄 Finalizing upload operations..."
    
    # Prepare common S3 paths
    RESULTS_S3_PATH="s3://${S3_BUCKET}/Result/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/"
    REPORTS_S3_PATH="s3://${S3_BUCKET}/Report/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/"
    ATTACHMENTS_S3_PATH="${REPORTS_S3_PATH}attachments/"

    # Restore credentials for final operations
    restore_aws_credentials

    # Final sync to ensure all files are captured
    if [[ "$S3_TYPE" == "aws" ]]; then
        s5cmd --no-verify-ssl sync "$ADAPTER_S3_DIR/results/allure-results/" "${RESULTS_S3_PATH}allure-results/"
        s5cmd --no-verify-ssl sync "$ADAPTER_S3_DIR/results/attachments/" "$ATTACHMENTS_S3_PATH"
    elif [[ "$S3_TYPE" == "minio" ]]; then
        s5cmd --no-verify-ssl --endpoint-url "$S3_API_HOST" sync "$ADAPTER_S3_DIR/results/allure-results/" "${RESULTS_S3_PATH}allure-results/"
        s5cmd --no-verify-ssl --endpoint-url "$S3_API_HOST" sync "$ADAPTER_S3_DIR/results/attachments/" "$ATTACHMENTS_S3_PATH"
    fi

    # Upload marker file
    echo -n "false" > $ADAPTER_S3_DIR/results/allure-results.uploaded
    if [[ "$S3_TYPE" == "aws" ]]; then
        s5cmd --no-verify-ssl cp "$ADAPTER_S3_DIR/results/allure-results.uploaded" "${RESULTS_S3_PATH}allure-results.uploaded"
    elif [[ "$S3_TYPE" == "minio" ]]; then
        s5cmd --no-verify-ssl --endpoint-url "$S3_API_HOST" cp "$ADAPTER_S3_DIR/results/allure-results.uploaded" "${RESULTS_S3_PATH}allure-results.uploaded"
    fi

    # Generate result URLs
    generate_result_urls

    # Final cleanup
    final_cleanup

    echo ""
    echo "Results are available at: ${RESULTS_URL}"
    echo "Reports are available at: ${REPORTS_URL}"
    echo "Report view is available at: ${REPORT_VIEW_HOST_URL}/${REPORTS_FOLDER_PATH}index.html"
    
    echo "✅ Upload finalization completed"
}

# Generate URLs for results
generate_result_urls() {
    if [[ "$S3_TYPE" == "aws" ]]; then
        RESULT_URL="${S3_BUCKET}.${S3_UI_URL}/Result/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/allure-results/"
    elif [[ "$S3_TYPE" == "minio" ]]; then
        # Generate base64-encoded URLs for MinIO UI
        RESULTS_FOLDER_PATH="Result/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/allure-results/"
        RESULTS_ENCODED_PATH=$(echo -n "${RESULTS_FOLDER_PATH}" | base64)
        RESULTS_URL="${S3_UI_URL}/browser/${S3_BUCKET}/${RESULTS_ENCODED_PATH}"

        REPORTS_FOLDER_PATH="Report/${ENV_NAME}/${CURRENT_DATE}/${CURRENT_TIME}/allure-report/"
        REPORTS_ENCODED_PATH=$(echo -n "${REPORTS_FOLDER_PATH}" | base64)
        REPORTS_URL="${S3_UI_URL}/browser/${S3_BUCKET}/${REPORTS_ENCODED_PATH}"
    fi
}

# Clear sensitive environment variables
clear_sensitive_vars() {
    echo "🔐 Clearing sensitive environment variables..."
    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    unset S3_ACCESS_KEY
    unset S3_SECRET_KEY
}

# Restore AWS credentials for final operations
restore_aws_credentials() {
    echo "🔑 Restoring AWS credentials for final operations..."
    export AWS_ACCESS_KEY_ID="$_LOCAL_S3_KEY"
    export AWS_SECRET_ACCESS_KEY="$_LOCAL_S3_SECRET"
}

# Final cleanup of all credentials
final_cleanup() {
    echo "🧹 Final cleanup of all credentials..."
    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    unset _LOCAL_S3_KEY
    unset _LOCAL_S3_SECRET
    unset _BACKGROUND_S3_KEY
    unset _BACKGROUND_S3_SECRET
} 