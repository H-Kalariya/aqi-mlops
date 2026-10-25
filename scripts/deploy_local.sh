#!/usr/bin/env bash
# Owner: M3 — CI/CD: Local deployment helper
# Builds container image locally and runs zero-downtime rolling update
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_help() {
    cat <<EOF
Usage: ./deploy_local.sh [tag] [options]

Builds the AQI API container image locally and triggers a rolling update
using deploy/scripts/rolling_update.sh.

Arguments:
  tag               Image tag/version to assign (default: git short SHA or local-latest)

Options:
  --scale N         Number of API replicas (default: 3)
  --help, -h        Show this help message

Example:
  ./scripts/deploy_local.sh v1.1.0
  ./scripts/deploy_local.sh --scale 2
EOF
}

TARGET_TAG=""
SCALE=3

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scale)
            SCALE="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "${TARGET_TAG}" ]]; then
                TARGET_TAG="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "${TARGET_TAG}" ]]; then
    TARGET_TAG=$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "v$(date +%Y%m%d%H%M)")
fi

echo "=========================================================="
echo " AQI MLOps: Local Build & Rolling Deployment"
echo " Target Tag: ${TARGET_TAG}"
echo " Replicas:   ${SCALE}"
echo "=========================================================="

cd "${ROOT_DIR}"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "[1/2] Building local Docker image aqi-api:${TARGET_TAG}..."
    docker build -t "aqi-api:${TARGET_TAG}" -t "aqi-api:latest" -f Dockerfile .
else
    echo "[NOTE] Docker daemon not active in shell. Proceeding with deployment script in offline mode."
fi

echo "[2/2] Invoking rolling update script..."
chmod +x deploy/scripts/*.sh 2>/dev/null || true
"${ROOT_DIR}/deploy/scripts/rolling_update.sh" "${TARGET_TAG}" --scale "${SCALE}"

echo "=========================================================="
echo " Local deployment successful! Version ${TARGET_TAG} is active."
echo "=========================================================="
