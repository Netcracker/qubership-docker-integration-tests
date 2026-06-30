#!/bin/bash

# Adapter-S3 is only sourced when the ATP report path is active (see docker-entrypoint.sh).

# True when a bucket is set — actually publish reports to S3. Empty bucket: run tests, no S3 publish.
atp_report_upload() {
    [[ -n "${ATP_STORAGE_BUCKET:-}" ]]
}

read_atp_storage_credential() {
    local var_name="$1"
    local file_name="$2"
    local file_path="${INTEGRATION_TESTS_SECRETS_DIR}/${file_name}"

    if [[ -f "$file_path" && -r "$file_path" ]]; then
        local val
        val="$(tr -d '\n\r' <"$file_path")"
        if [[ -n "$val" ]]; then
            export "$var_name"="$val"
        fi
    fi
}

load_atp_storage_credentials() {
    if [[ -z "${INTEGRATION_TESTS_SECRETS_DIR:-}" ]]; then
        return 0
    fi

    echo "Loading ATP credentials from ${INTEGRATION_TESTS_SECRETS_DIR} (files override env when non-empty)"
    ls -la "${INTEGRATION_TESTS_SECRETS_DIR}" 2>&1 || echo "WARN: cannot list ${INTEGRATION_TESTS_SECRETS_DIR}"

    read_atp_storage_credential ATP_STORAGE_USERNAME ATP_STORAGE_USERNAME
    read_atp_storage_credential ATP_STORAGE_PASSWORD ATP_STORAGE_PASSWORD
}

# Environment initialization module
init_environment() {
    echo "Initializing environment..."

    load_atp_storage_credentials

    # Compute current date and time
    if [[ -z "${CURRENT_DATE}" ]]; then
        CURRENT_DATE=$(date +%F) # e.g., 2025-04-07
    fi
    if [[ -z "${CURRENT_TIME}" ]]; then
        CURRENT_TIME=$(date +%H-%M-%S) # e.g., 11-48-00
    fi

    # Bucket set: full S3 publish path — fail fast if creds/settings are incomplete (exit 1 → pod Error, not stuck Running+ttyd).
    if atp_report_upload; then
        local _missing=()
        [[ -z "${ATP_STORAGE_PROVIDER:-}" ]] && _missing+=(ATP_STORAGE_PROVIDER)
        [[ -z "${ATP_STORAGE_USERNAME:-}" ]] && _missing+=(ATP_STORAGE_USERNAME)
        [[ -z "${ATP_STORAGE_PASSWORD:-}" ]] && _missing+=(ATP_STORAGE_PASSWORD)
        [[ -z "${ENVIRONMENT_NAME:-}" ]] && _missing+=(ENVIRONMENT_NAME)

        local _prov_lc="${ATP_STORAGE_PROVIDER,,}"
        case "${_prov_lc}" in
        aws)
            [[ -z "${ATP_STORAGE_REGION:-}" ]] && _missing+=(ATP_STORAGE_REGION)
            ;;
        minio | s3)
            [[ -z "${ATP_STORAGE_SERVER_URL:-}" ]] && _missing+=(ATP_STORAGE_SERVER_URL)
            [[ -z "${ATP_STORAGE_REGION:-}" ]] && _missing+=(ATP_STORAGE_REGION)
            ;;
        *)
            echo "ERROR: ATP_STORAGE_PROVIDER must be aws, minio, or s3 (got: '${ATP_STORAGE_PROVIDER:-}')"
            exit 1
            ;;
        esac

        if [[ ${#_missing[@]} -gt 0 ]]; then
            echo "ERROR: S3 upload is configured (ATP_STORAGE_BUCKET is set) but required variables are missing or empty: ${_missing[*]}"
            exit 1
        fi

        echo "ATP report upload to S3 enabled (provider: ${ATP_STORAGE_PROVIDER}, bucket: ${ATP_STORAGE_BUCKET})"

        _LOCAL_S3_KEY="$ATP_STORAGE_USERNAME"
        _LOCAL_S3_SECRET="$ATP_STORAGE_PASSWORD"
        export AWS_ACCESS_KEY_ID="$_LOCAL_S3_KEY"
        export AWS_SECRET_ACCESS_KEY="$_LOCAL_S3_SECRET"
        export AWS_REGION="${ATP_STORAGE_REGION}"

        if [[ "${_prov_lc}" == "minio" || "${_prov_lc}" == "s3" ]]; then
            export AWS_ENDPOINT_URL="${ATP_STORAGE_SERVER_URL}"
            export AWS_NO_VERIFY_SSL="true"
        fi
    else
        echo "INFO: ATP_STORAGE_BUCKET is empty — running tests without S3 upload."
    fi

    # Define temp clone path
    export TMP_DIR="/tmp/clone"
    mkdir -p "$TMP_DIR"

    # Remove previous contents if any
    rm -rf "${TMP_DIR:?}/"*

    export ALLURE_RESULTS_DIR="${ROBOT_HOME}/output/allure-results"
    mkdir -p "${ALLURE_RESULTS_DIR}"

    echo "SUCCESS: Environment initialized successfully"
}
