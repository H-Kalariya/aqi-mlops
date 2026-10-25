#!/usr/bin/env bash
# Owner: M2 — Deployment: Automated rollback script
# Rolls back to the previously recorded active release
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

show_help() {
    cat <<EOF
Usage: ./rollback.sh [target_tag] [options]

Rolls back API deployment to the previous version recorded in deploy/releases.log,
or to a specific target_tag if provided.

Arguments:
  target_tag        (Optional) Specific image/app tag to roll back to.
                    If omitted, the previous tag from releases.log is used.

Options:
  --help, -h        Show this help message

Examples:
  ./rollback.sh
  ./rollback.sh v1.0.0
EOF
}

TARGET_TAG="${1:-}"

if [[ "${TARGET_TAG}" == "--help" ]] || [[ "${TARGET_TAG}" == "-h" ]]; then
    show_help
    exit 0
fi

if [[ -z "${TARGET_TAG}" ]]; then
    echo "[rollback] Searching release log for previous release tag..."
    TARGET_TAG="$("${SCRIPT_DIR}/release_log.sh" previous 2>/dev/null || echo "")"
    if [[ -z "${TARGET_TAG}" ]] || [[ "${TARGET_TAG}" == "unknown" ]]; then
        echo "Error: No previous release found in deploy/releases.log to rollback to." >&2
        echo "Please specify a target tag manually: ./rollback.sh <tag>" >&2
        exit 1
    fi
fi

echo "=========================================================="
echo " Initiating Automated Rollback to Version: ${TARGET_TAG}"
echo "=========================================================="

# Run the rolling update script with target tag
"${SCRIPT_DIR}/rolling_update.sh" "${TARGET_TAG}"

echo "[rollback] Verifying active version header..."
ENDPOINT="http://localhost:8080/health"
if command -v curl >/dev/null 2>&1; then
    ACTIVE_VER=$(curl -s -I "${ENDPOINT}" 2>/dev/null | grep -i "X-App-Version" | tr -d '\r\n' | awk '{print $2}' || true)
    if [[ -n "${ACTIVE_VER}" ]]; then
        echo "[rollback] Active API X-App-Version: ${ACTIVE_VER}"
    fi
fi

echo "=========================================================="
echo " Rollback to ${TARGET_TAG} completed successfully."
echo "=========================================================="
