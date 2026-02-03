#!/bin/bash

# Test execution module
run_tests() {
    echo "▶ Starting test execution..."
    
    # Import upload monitoring module for security functions
    if [ -f "${ROBOT_HOME}/scripts/adapter-S3/upload-monitor.sh" ]; then
        source "${ROBOT_HOME}/scripts/adapter-S3/upload-monitor.sh"
    elif [ -f "/app/scripts/upload-monitor.sh" ]; then
        source "/app/scripts/upload-monitor.sh"
    elif [ -f "/scripts/upload-monitor.sh" ]; then
        source "/scripts/upload-monitor.sh"
    else
        echo "❌ upload-monitor.sh not found!"
        echo "Searched in: ${ROBOT_HOME}/scripts/adapter-S3/, /app/scripts/, /scripts/"
        exit 1
    fi
    
    # Create Allure results directory
    echo "📁 Creating Allure results directory..."
    mkdir -p $TMP_DIR/allure-results

    # Clear sensitive variables before tests (only if S3 is enabled)
    if [[ -n "${ATP_STORAGE_BUCKET}" ]]; then
        echo "🔐 Clearing sensitive environment variables before tests..."
        clear_sensitive_vars
    fi

    # Execute test suite
    echo "🚀 Running test suite..."
    # Note: permissions are already set in Dockerfile during build
    ${ROBOT_HOME}/scripts/adapter-S3/start_tests.sh "$@" || TEST_EXIT_CODE=$?

    TEST_EXIT_CODE=${TEST_EXIT_CODE:-0}
    echo "ℹ️ Test script exited with code: $TEST_EXIT_CODE (but continuing...)"
    
    echo "✅ Test execution completed"
}
