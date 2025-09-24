#!/bin/bash

# Store robot arguments passed to this script
echo "📋 Using robot arguments: $@"

# Execute the script, generate robot and allure results with passed arguments
# robot --output $ADAPTER_S3_OUT_DIR/output.xml \
#       --log $ADAPTER_S3_OUT_DIR/log.html \
#       --report $ADAPTER_S3_OUT_DIR/report.html \
#       --listener "allure_robotframework;$ADAPTER_S3_OUT_DIR/adapter-S3/allure-results" \
#       "$@"

robot --output $ADAPTER_S3_OUT_DIR/output.xml \
      --log $ADAPTER_S3_OUT_DIR/log.html \
      --report $ADAPTER_S3_OUT_DIR/report.html \
      --listener "allure_robotframework;$ADAPTER_S3_OUT_DIR/adapter-S3/allure-results" \
      -i backup,crud,consul_images -e consul_images,alerts,unauthorized_access,s3_storage ./tests

# Capture the exit code from the script
exit_code=$?

# Exit the shell script with the same exit code
exit $exit_code