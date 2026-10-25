#!/usr/bin/env bash
# Owner: Shared (M1 as repo/release manager) — Handoff packager
# Packages each team member's owned files and guides into individual zip bundles
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
HANDOFF_DIR="${ROOT_DIR}/handoff"

echo "=========================================================="
echo " AQI Forecaster MLOps: Team Member Handoff Packager"
echo " Export root: ${HANDOFF_DIR}"
echo "=========================================================="

# Common shared files needed by all members
SHARED_FILES=(
    "config.yaml"
    "README.md"
    "OWNERSHIP.md"
    "pyproject.toml"
    "requirements.txt"
    ".gitignore"
    ".env.example"
    "docs/DECISIONS.md"
    "docs/demo_script.md"
)

# Function to package a specific member
export_member() {
    local num="$1"
    local m_name="member${num}"
    local target_dir="${HANDOFF_DIR}/${m_name}/aqi-mlops-m${num}"
    local zip_file="${HANDOFF_DIR}/${m_name}.zip"

    echo ""
    echo "===> Exporting Member ${num} Bundle..."
    rm -rf "${HANDOFF_DIR}/${m_name}" "${zip_file}"
    mkdir -p "${target_dir}"

    # 1. Copy shared files
    for file in "${SHARED_FILES[@]}"; do
        if [[ -f "${ROOT_DIR}/${file}" ]]; then
            mkdir -p "$(dirname "${target_dir}/${file}")"
            cp "${ROOT_DIR}/${file}" "${target_dir}/${file}"
        fi
    done

    # 2. Copy shared common code
    if [[ -d "${ROOT_DIR}/src/common" ]]; then
        mkdir -p "${target_dir}/src/common"
        cp -r "${ROOT_DIR}/src/common/." "${target_dir}/src/common/"
    fi

    # 3. Copy Member-specific files
    case "${num}" in
        1)
            # M1: Data, DVC, Pipeline, Train, Eval, Git M1
            mkdir -p "${target_dir}/data/snapshot"
            cp -r "${ROOT_DIR}/data/snapshot/." "${target_dir}/data/snapshot/" 2>/dev/null || true
            cp "${ROOT_DIR}/dvc.yaml" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/params.yaml" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/.dvcignore" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/.pre-commit-config.yaml" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/Makefile" "${target_dir}/" 2>/dev/null || true

            for dir in ingest validate features train evaluate; do
                if [[ -d "${ROOT_DIR}/src/${dir}" ]]; then
                    mkdir -p "${target_dir}/src/${dir}"
                    cp -r "${ROOT_DIR}/src/${dir}/." "${target_dir}/src/${dir}/"
                fi
            done

            if [[ -d "${ROOT_DIR}/tests/m1" ]]; then
                mkdir -p "${target_dir}/tests/m1"
                cp -r "${ROOT_DIR}/tests/m1/." "${target_dir}/tests/m1/"
            fi

            if [[ -d "${ROOT_DIR}/git_scenarios/m1" ]]; then
                mkdir -p "${target_dir}/git_scenarios/m1"
                cp -r "${ROOT_DIR}/git_scenarios/m1/." "${target_dir}/git_scenarios/m1/"
            fi
            ;;

        2)
            # M2: Serving, Docker, Deploy strategies, Git M2
            cp "${ROOT_DIR}/Dockerfile" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/docker-compose.yml" "${target_dir}/" 2>/dev/null || true
            cp "${ROOT_DIR}/requirements-api.txt" "${target_dir}/" 2>/dev/null || true

            if [[ -d "${ROOT_DIR}/api" ]]; then
                mkdir -p "${target_dir}/api"
                cp -r "${ROOT_DIR}/api/." "${target_dir}/api/"
            fi

            if [[ -d "${ROOT_DIR}/deploy" ]]; then
                mkdir -p "${target_dir}/deploy"
                cp -r "${ROOT_DIR}/deploy/." "${target_dir}/deploy/"
            fi

            if [[ -d "${ROOT_DIR}/tests/m2" ]]; then
                mkdir -p "${target_dir}/tests/m2"
                cp -r "${ROOT_DIR}/tests/m2/." "${target_dir}/tests/m2/"
            fi

            if [[ -d "${ROOT_DIR}/git_scenarios/m2" ]]; then
                mkdir -p "${target_dir}/git_scenarios/m2"
                cp -r "${ROOT_DIR}/git_scenarios/m2/." "${target_dir}/git_scenarios/m2/"
            fi
            ;;

        3)
            # M3: Monitoring, CI/CD, Drift, Continuous Training, Git M3
            if [[ -d "${ROOT_DIR}/monitoring" ]]; then
                mkdir -p "${target_dir}/monitoring"
                cp -r "${ROOT_DIR}/monitoring/." "${target_dir}/monitoring/"
            fi

            if [[ -d "${ROOT_DIR}/.github" ]]; then
                mkdir -p "${target_dir}/.github"
                cp -r "${ROOT_DIR}/.github/." "${target_dir}/.github/"
            fi

            if [[ -d "${ROOT_DIR}/scripts" ]]; then
                mkdir -p "${target_dir}/scripts"
                cp -r "${ROOT_DIR}/scripts/." "${target_dir}/scripts/"
            fi

            if [[ -d "${ROOT_DIR}/src/drift" ]]; then
                mkdir -p "${target_dir}/src/drift"
                cp -r "${ROOT_DIR}/src/drift/." "${target_dir}/src/drift/"
            fi

            if [[ -d "${ROOT_DIR}/tests/m3" ]]; then
                mkdir -p "${target_dir}/tests/m3"
                cp -r "${ROOT_DIR}/tests/m3/." "${target_dir}/tests/m3/"
            fi

            if [[ -d "${ROOT_DIR}/git_scenarios/m3" ]]; then
                mkdir -p "${target_dir}/git_scenarios/m3"
                cp -r "${ROOT_DIR}/git_scenarios/m3/." "${target_dir}/git_scenarios/m3/"
            fi
            ;;
    esac

    # 4. Copy Member Guide as START_HERE.md
    if [[ -f "${ROOT_DIR}/docs/member${num}_guide.md" ]]; then
        cp "${ROOT_DIR}/docs/member${num}_guide.md" "${target_dir}/START_HERE.md"
        cp "${ROOT_DIR}/docs/member${num}_guide.md" "${target_dir}/docs/member${num}_guide.md"
    fi

    # 5. Compress to memberN.zip
    cd "${HANDOFF_DIR}/${m_name}"
    if command -v zip >/dev/null 2>&1; then
        zip -r -q "${zip_file}" "aqi-mlops-m${num}"
    elif command -v python >/dev/null 2>&1; then
        python -c "import shutil; shutil.make_archive('${HANDOFF_DIR}/${m_name}', 'zip', '${HANDOFF_DIR}/${m_name}')"
    fi

    echo "Finished: created ${target_dir} and ${zip_file}"
}

# Export all 3 members
export_member 1
export_member 2
export_member 3

echo ""
echo "=========================================================="
echo " All Member Handoff Packages Successfully Generated!"
echo " Output files in ${HANDOFF_DIR}:"
ls -lh "${HANDOFF_DIR}"/*.zip 2>/dev/null || dir "${HANDOFF_DIR}"
echo "=========================================================="
