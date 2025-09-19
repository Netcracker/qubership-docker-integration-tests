#!/bin/bash

# Install allure plugin
# pip install robotframework-allure2

# Store robot arguments passed to this script
ROBOT_ARGS="$@"
echo "📋 Using robot arguments: $ROBOT_ARGS"

# Execute the script, generate robot and allure results with passed arguments
robot --output $ADAPTER_S3_OUT_DIR/output.xml \
      --log $ADAPTER_S3_OUT_DIR/log.html \
      --report $ADAPTER_S3_OUT_DIR/report.html \
      --listener "allure_robotframework;$ADAPTER_S3_OUT_DIR/adapter-S3/results/allure-results" \
      $ROBOT_ARGS

# Execute the script for all tests in folder and subfolders, generate robot and allure results
# robot --output $ADAPTER_S3_OUT_DIR/results/robot-results/output.xml \
#       --log $ADAPTER_S3_OUT_DIR/results/robot-results/log.html \
#       --report $ADAPTER_S3_OUT_DIR/results/robot-results/report.html \
#       --listener "allure_robotframework;$ADAPTER_S3_OUT_DIR/results/allure-results" \
#       ../../consul/**/*.robot

# Capture the exit code from the script
exit_code=$?

# Exit the shell script with the same exit code
exit $exit_code