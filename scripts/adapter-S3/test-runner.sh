#!/bin/bash

# Test execution module
run_tests() {
    echo "▶ Starting test execution..."
    
    # Store robot arguments passed to this function
    ROBOT_ARGS="$@"
    echo "📋 Passing robot arguments to start_tests.sh: $ROBOT_ARGS"
    
    # Import upload monitoring module for security functions
    source ./upload-monitor.sh
    
    # Create Allure results directory
    echo "📁 Creating Allure results directory..."
    mkdir -p $ADAPTER_S3_OUT_DIR/results/allure-results

    # Clear sensitive variables before tests
    echo "🔐 Clearing sensitive environment variables before tests..."
    clear_sensitive_vars

    # Execute test suite with robot arguments
    echo "🚀 Running test suite..."
    chmod +x start_tests.sh
    ./start_tests.sh $ROBOT_ARGS || TEST_EXIT_CODE=$?

    TEST_EXIT_CODE=${TEST_EXIT_CODE:-0}
    echo "ℹ️ Test script exited with code: $TEST_EXIT_CODE (but continuing...)"
    
    echo "✅ Test execution completed"
} 