#!/bin/bash
# Prints "run=true" when a pull request touches anything that can affect the images, and "run=false"
# when it touches only documentation and repository metadata. Compares <head-sha> with its merge base.
#
# Usage: detect-image-changes.sh <base-sha> <head-sha>
set -euo pipefail

base_sha="${1:?Usage: detect-image-changes.sh <base-sha> <head-sha>}"
head_sha="${2:?Usage: detect-image-changes.sh <base-sha> <head-sha>}"

# Write the list to a file first: a failing git diff inside a process substitution would go unnoticed
# and report "run=false", which lets the gate pass without running the builds.
changed_files="$(mktemp)"
trap 'rm -f "${changed_files}"' EXIT
git diff --name-only -z "${base_sha}...${head_sha}" >"${changed_files}"

while IFS= read -r -d '' path; do
    case "${path}" in
    .github/ISSUE_TEMPLATE/* | .github/PULL_REQUEST_TEMPLATE.md | .github/auto-labeler-config.yaml | \
        .github/release-drafter-config.yml | .github/super-linter.env | .github/linters/* | docs/* | \
        CODE-OF-CONDUCT.md | CONTRIBUTING.md | LICENSE | README.md | SECURITY.md) ;;
    *)
        echo "run=true"
        exit 0
        ;;
    esac
done <"${changed_files}"

echo "run=false"
