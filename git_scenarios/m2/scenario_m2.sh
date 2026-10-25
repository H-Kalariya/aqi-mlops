#!/usr/bin/env bash
# Owner: M2 — Git Scenario 2: Deliberate Merge Conflict Resolution & Feature Rebase
# Runs safely in a temporary sandbox repository to protect active repository history.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SANDBOX_DIR="${ROOT_DIR}/git_scenarios/sandbox/m2_sandbox"
EVIDENCE_DIR="${ROOT_DIR}/git_scenarios/evidence"

mkdir -p "${EVIDENCE_DIR}"
LOG_FILE="${EVIDENCE_DIR}/m2_git_scenario.log"

echo "=========================================================="
echo " M2 Git Scenario: Merge Conflict Resolution & Rebase Demo"
echo " Log file: ${LOG_FILE}"
echo "=========================================================="

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "==> [1/8] Setting up sandbox git repository at ${SANDBOX_DIR}..."
rm -rf "${SANDBOX_DIR}"
mkdir -p "${SANDBOX_DIR}"
cd "${SANDBOX_DIR}"

git init -b main
cat << 'EOF' > config.yaml
# Shared project configuration
project:
  name: aqi-forecaster
  version: "1.0.0"
horizon: 24
ingest:
  rate_limit: 30
EOF

git add config.yaml
git commit -m "chore: base config.yaml on main"

# Create dev branch
git checkout -b dev
git commit --allow-empty -m "chore: initialize dev branch"

echo "==> [2/8] Creating M1 feature branch modifying rate_limit to 60..."
git checkout -b feat/m1-data-rate dev
cat << 'EOF' > config.yaml
# Shared project configuration
project:
  name: aqi-forecaster
  version: "1.0.0"
horizon: 24
ingest:
  rate_limit: 60  # M1 needs higher rate limit for bulk ingest
EOF
git add config.yaml
git commit -m "feat(m1): increase rate_limit to 60 for batch ingest"

echo "==> [3/8] Creating M2 feature branch modifying rate_limit to 15 on same line..."
git checkout -b feat/m2-rate-limit dev
cat << 'EOF' > config.yaml
# Shared project configuration
project:
  name: aqi-forecaster
  version: "1.0.0"
horizon: 24
ingest:
  rate_limit: 15  # M2 lowers rate limit to prevent upstream 429 errors
EOF
git add config.yaml
git commit -m "feat(m2): throttle rate_limit to 15 for API stability"

echo "==> [4/8] Merging M1 branch into dev..."
git checkout dev
git merge --no-ff feat/m1-data-rate -m "Merge branch 'feat/m1-data-rate' into dev"

echo "==> [5/8] Merging M2 branch into dev (DELIBERATE CONFLICT TRIGGER)..."
set +e
git merge --no-ff feat/m2-rate-limit -m "Merge branch 'feat/m2-rate-limit' into dev"
MERGE_STATUS=$?
set -e

if [[ $MERGE_STATUS -ne 0 ]]; then
    echo "[EXPECTED CONFLICT]: Conflict observed in config.yaml:"
    cat config.yaml
fi

echo "==> [6/8] Resolving conflict collaboratively (compromising on 30 with retry)..."
cat << 'EOF' > config.yaml
# Shared project configuration
project:
  name: aqi-forecaster
  version: "1.0.0"
horizon: 24
ingest:
  rate_limit: 30  # Resolved: Compromise between M1 bulk needs and M2 stability
EOF
git add config.yaml
git commit -m "merge: resolve conflict on ingest.rate_limit between M1 and M2"
echo "[CONFLICT RESOLVED]: Clean merge committed."

echo "==> [7/8] Demonstrating Git Rebase onto dev..."
git checkout -b feat/m2-cache dev~2
git commit --allow-empty -m "feat(m2): add redis cache scaffolding"
git commit --allow-empty -m "feat(m2): implement cache lookup"

echo "Commit tree BEFORE rebase:"
git log --oneline --graph --all -n 8

echo "Executing git rebase dev..."
git rebase dev

echo "Commit tree AFTER rebase (linear history):"
git log --oneline --graph --all -n 8

echo "=========================================================="
echo " M2 Scenario Completed Successfully! Evidence logged."
echo "=========================================================="
