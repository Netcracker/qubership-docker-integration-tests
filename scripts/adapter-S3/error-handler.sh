#!/bin/bash

# Centralized error handler and exit-trap for graceful pod termination.
#
# fail()         — logs the error, stores its message, and exits 1.
# finalize_once() — the single EXIT trap: writes error-state JSON when rc≠0,
#                   runs all cleanup, then always exits 0 so Argo does not hang.
#
# Register the trap in entrypoint.sh AFTER all scripts are sourced:
#   trap 'finalize_once' EXIT

# Stores the fatal error message so finalize_once can embed it in the error JSON.
FAIL_MESSAGE=""
FINALIZE_DONE=false

fail() {
    local error_message="${1:-Unknown error}"
    echo "❌ FATAL: $error_message"
    echo "⚠️  Delegating cleanup to EXIT trap (finalize_once)."
    FAIL_MESSAGE="$error_message"
    # Caught by EXIT trap and goes to finalize_once()
    exit 1
}

#shellcheck disable=SC2329
finalize_once() {
    local rc=$?

    if [ "$FINALIZE_DONE" != "true" ]; then
        FINALIZE_DONE=true
        echo "🔄 EXIT trap triggered with rc=$rc"

        set +e

        # When fail() triggered the exit, write a minimal error-state JSON so
        # downstream pipeline stages (e.g. "get ATP report file") receive a valid
        # FAILED payload instead of finding no file at all.
        if [ "$rc" -ne 0 ]; then
            echo "⚠️  Non-zero exit detected — pre-seeding error-state variables for generate_email_notification_json."
            # Pre-export the variables that generate_email_notification_json reads.
            # calculate-email-notification-variables.sh will bail early (no allure results),
            # leaving these values intact so the downstream JSON reflects the fatal error.
            export TEST_OVERALL_STATUS="FAILED"
            export TEST_PASS_RATE=0
            export TEST_PASS_RATE_ROUNDED=0
            export TEST_TOTAL_COUNT=0
            export TEST_PASSED_COUNT=0
            export TEST_FAILED_COUNT=0
            export TEST_SKIPPED_COUNT=0
            export TEST_COVERAGE=0
            unset TEST_DETAILS_STRING
            export TEST_DETAILS_FILE=""
            export EXECUTION_DATE
            EXECUTION_DATE="$(date '+%Y-%m-%d %H:%M:%S')"
            export TIMESTAMP
            TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S UTC')"
            if compgen -G "$TMP_DIR/allure-results/*-result.json" > /dev/null 2>&1; then
                echo "ℹ️  Allure results detected — skipping 'Test not started' URL override."
            else
                export ALLURE_REPORT_URL="Test not started. Please check the logs for more details. $FAIL_MESSAGE. "
                export ATP_REPORT_VIEW_UI_URL="Test not started. Please check the logs for more details. $FAIL_MESSAGE. "
            fi
        fi

        generate_email_notification_json || true

        # Source runner-specific missed-test detector if provided.
        if [ -f "/app/detect-missed-tests.sh" ]; then
            # shellcheck disable=SC1091
            source "/app/detect-missed-tests.sh" || true
        fi

        # Finalize upload only when publishing to S3 (bucket set)
        if atp_report_upload; then
            finalize_upload || true
        else
            echo " Skipping upload finalization (no bucket — results stay local)"
            echo " Test results are available locally at: $TMP_DIR"
        fi
        sleep 15

        set -e
    fi

    exit "$rc"
}
