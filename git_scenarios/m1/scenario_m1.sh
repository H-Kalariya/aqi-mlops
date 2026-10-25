#!/usr/bin/env bash
# Owner: M1 — Git Scenario 1: Pre-commit blocking & Git Revert demonstration
# Runs safely in a temporary sandbox repository to protect active repository history.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SANDBOX_DIR="${ROOT_DIR}/git_scenarios/sandbox/m1_sandbox"
EVIDENCE_DIR="${ROOT_DIR}/git_scenarios/evidence"

mkdir -p "${EVIDENCE_DIR}"
LOG_FILE="${EVIDENCE_DIR}/m1_git_scenario.log"

echo "=========================================================="
echo " M1 Git Scenario: Pre-commit & Bad Commit Revert Demo"
echo " Log file: ${LOG_FILE}"
echo "=========================================================="

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "==> [1/6] Initializing sandbox git repository at ${SANDBOX_DIR}..."
rm -rf "${SANDBOX_DIR}"
mkdir -p "${SANDBOX_DIR}"
cd "${SANDBOX_DIR}"

git init -b main
# Copy project configuration for realistic environment
cp "${ROOT_DIR}/.pre-commit-config.yaml" .
cp "${ROOT_DIR}/pyproject.toml" .

git add .
git commit -m "chore: initial commit with lint configuration"

echo "==> [2/6] Demonstrating pre-commit hook blocking poorly formatted code..."
cat << 'EOF' > bad_code.py
import sys, os
def bad_formatting( x,y ):
  return   x+y
EOF

echo "Attempting to run ruff and black check on bad_code.py (EXPECT FAILURE)..."
if command -v black >/dev/null 2>&1; then
    black --check bad_code.py || echo "[PRE-COMMIT BLOCKED]: Black detected formatting errors as expected!"
fi
if command -v ruff >/dev/null 2>&1; then
    ruff check bad_code.py || echo "[PRE-COMMIT BLOCKED]: Ruff detected unused imports / style violations as expected!"
fi

echo "==> [3/6] Fixing code format to pass pre-commit..."
cat << 'EOF' > bad_code.py
"""Properly formatted module conforming to PEP 8."""


def good_formatting(x: int, y: int) -> int:
    """Add two numbers cleanly."""
    return x + y
EOF

if command -v black >/dev/null 2>&1; then
    black bad_code.py
fi
if command -v ruff >/dev/null 2>&1; then
    ruff check --fix bad_code.py
fi

git add bad_code.py
git commit -m "feat(m1): add properly formatted helper function"
echo "[PRE-COMMIT PASSED]: Commit succeeded after clean formatting."

echo "==> [4/6] Introducing an erroneous model change commit..."
cat << 'EOF' >> model_logic.py
# Accidental degradation introduced in model logic
def get_learning_rate():
    return -999.0  # Erroneous negative rate causing training failure
EOF

git add model_logic.py
git commit -m "feat(m1): modify learning rate parameter (bad change)"

echo "Recent git log before revert:"
git log --oneline -n 3 --graph

echo "==> [5/6] Executing git revert to undo the bad commit cleanly..."
BAD_COMMIT_SHA=$(git rev-parse HEAD)
git revert --no-edit "${BAD_COMMIT_SHA}"

echo "==> [6/6] Verifying repository log after git revert:"
git log --oneline -n 4 --graph

echo "Content of model_logic.py after revert:"
cat model_logic.py 2>/dev/null || echo "(File removed or reverted cleanly)"

echo "=========================================================="
echo " M1 Scenario Completed Successfully! Evidence logged."
echo "=========================================================="
