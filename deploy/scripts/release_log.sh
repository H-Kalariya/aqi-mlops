#!/usr/bin/env bash
# Owner: M2 — Deployment: Release logging utility
# Records releases to deploy/releases.log
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${ROOT_DIR}/deploy/releases.log"

show_help() {
    cat <<EOF
Usage: release_log.sh [OPTIONS] <command> [args...]

Commands:
  record <new_tag> [prev_tag] [status]   Record a new release entry
  last                                    Get the latest recorded release tag
  previous                                Get the previous release tag for rollback
  list                                    Display release history
  help, --help                            Show this help message

Examples:
  ./release_log.sh record v1.1.0 v1.0.0 SUCCESS
  ./release_log.sh previous
EOF
}

record_release() {
    local new_tag="${1:-}"
    local prev_tag="${2:-unknown}"
    local status="${3:-SUCCESS}"
    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    local git_sha
    git_sha="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
    local user
    user="${USER:-${USERNAME:-operator}}"

    if [[ -z "${new_tag}" ]]; then
        echo "Error: new_tag is required" >&2
        return 1
    fi

    mkdir -p "$(dirname "${LOG_FILE}")"
    echo "${timestamp}|${new_tag}|${prev_tag}|${git_sha}|${user}|${status}" >> "${LOG_FILE}"
    echo "[release_log] Recorded release: tag=${new_tag}, prev=${prev_tag}, git=${git_sha}, status=${status}"
}

get_last() {
    if [[ ! -f "${LOG_FILE}" ]] || [[ ! -s "${LOG_FILE}" ]]; then
        echo ""
        return 0
    fi
    tail -n 1 "${LOG_FILE}" | cut -d'|' -f2
}

get_previous() {
    if [[ ! -f "${LOG_FILE}" ]] || [[ ! -s "${LOG_FILE}" ]]; then
        echo ""
        return 0
    fi
    tail -n 1 "${LOG_FILE}" | cut -d'|' -f3
}

list_history() {
    if [[ ! -f "${LOG_FILE}" ]] || [[ ! -s "${LOG_FILE}" ]]; then
        echo "No releases recorded yet."
        return 0
    fi
    echo "==================== RELEASE HISTORY ===================="
    printf "%-22s %-12s %-12s %-10s %-12s %-10s\n" "TIMESTAMP" "TAG" "PREV_TAG" "GIT_SHA" "USER" "STATUS"
    echo "---------------------------------------------------------"
    while IFS='|' read -r ts tag prev sha usr stat; do
        printf "%-22s %-12s %-12s %-10s %-12s %-10s\n" "$ts" "$tag" "$prev" "$sha" "$usr" "$stat"
    done < "${LOG_FILE}"
}

case "${1:-help}" in
    record)
        record_release "${2:-}" "${3:-}" "${4:-SUCCESS}"
        ;;
    last)
        get_last
        ;;
    previous)
        get_previous
        ;;
    list)
        list_history
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: ${1}" >&2
        show_help
        exit 1
        ;;
esac
