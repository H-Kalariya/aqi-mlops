#!/usr/bin/env bash
# Owner: M3 — Git Scenario 3: Production Hotfix Cherry-Pick & Semantic Release Tagging
# Runs safely in a temporary sandbox repository to protect active repository history.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SANDBOX_DIR="${ROOT_DIR}/git_scenarios/sandbox/m3_sandbox"
EVIDENCE_DIR="${ROOT_DIR}/git_scenarios/evidence"

mkdir -p "${EVIDENCE_DIR}"
LOG_FILE="${EVIDENCE_DIR}/m3_git_scenario.log"

echo "=========================================================="
echo " M3 Git Scenario: Hotfix Cherry-Pick & Release Tags Demo"
echo " Log file: ${LOG_FILE}"
echo "=========================================================="

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "==> [1/7] Setting up sandbox repository at ${SANDBOX_DIR}..."
rm -rf "${SANDBOX_DIR}"
mkdir -p "${SANDBOX_DIR}"
cd "${SANDBOX_DIR}"

git init -b main
cat << 'EOF' > app.py
# Production API entrypoint
def run():
    print("AQI API running on 0.0.0.0:8000")
EOF

git add app.py
git commit -m "feat: initial API implementation"

echo "==> [2/7] Creating initial annotated release tag v1.0..."
git tag -a v1.0 -m "Release v1.0: Initial stable AQI Forecaster deployment"
echo "Active tags:"
git tag -n

echo "==> [3/7] Branching dev and adding ongoing feature commits..."
git checkout -b dev
cat << 'EOF' >> features.py
# Experimental continuous training features
def compute_ewma():
    pass
EOF
git add features.py
git commit -m "feat(m3): add EWMA feature calculation"

echo "==> [4/7] Critical security / bug discovered on production main! Creating hotfix..."
git checkout main
cat << 'EOF' > app.py
# Production API entrypoint with security sanitization hotfix
import html

def sanitize_input(val: str) -> str:
    return html.escape(val)

def run():
    print("AQI API running securely on 0.0.0.0:8000")
EOF
git add app.py
git commit -m "fix(security): sanitize incoming header values on main"
HOTFIX_COMMIT_SHA=$(git rev-parse HEAD)

echo "Hotfix commit created on main: ${HOTFIX_COMMIT_SHA}"

echo "==> [5/7] Cherry-picking hotfix commit into dev branch..."
git checkout dev
git cherry-pick "${HOTFIX_COMMIT_SHA}"

echo "Dev branch commit log showing cherry-picked fix:"
git log --oneline -n 3

echo "==> [6/7] Simulating drift retraining milestone and tagging v1.1..."
git checkout main
# Merge dev features for v1.1 release
git merge dev -m "chore(release): merge dev into main for v1.1"

git tag -a v1.1 -m "Release v1.1: Automated drift retraining and model promotion enabled"

echo "==> [7/7] Verifying all tags and commit graph:"
git tag -l -n2
git log --graph --oneline --decorate -n 6

echo "=========================================================="
echo " M3 Scenario Completed Successfully! Evidence logged."
echo "=========================================================="
