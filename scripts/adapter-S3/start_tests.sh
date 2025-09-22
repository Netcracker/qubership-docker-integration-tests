#!/bin/bash

# Store robot arguments passed to this script
ROBOT_ARGS="$@"
echo "📋 Using robot arguments: $ROBOT_ARGS"

# Execute the script, generate robot and allure results with passed arguments
robot --output $ADAPTER_S3_OUT_DIR/output.xml \
      --log $ADAPTER_S3_OUT_DIR/log.html \
      --report $ADAPTER_S3_OUT_DIR/report.html \
      --listener "allure_robotframework;$ADAPTER_S3_OUT_DIR/adapter-S3/allure-results" \
      $ROBOT_ARGS

# Capture the exit code from the script
exit_code=$?

# Exit the shell script with the same exit code
exit $exit_code