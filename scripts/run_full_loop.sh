#!/usr/bin/env bash
# Owner: M3 — Continuous Training: Full end-to-end feedback loop demo
# Runs: inject drift -> drift check -> retrain -> evaluate -> compare/promote -> API reload
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_help() {
    cat <<EOF
Usage: ./scripts/run_full_loop.sh [options]

Demonstrates the complete closed-loop continuous training cycle:
  1. Injects severe distribution shift (drift) into recent AQI data
  2. Runs Evidently / statistical drift detection
  3. Triggers retraining of a challenger model
  4. Evaluates challenger performance
  5. Compares challenger MAE against champion MAE
  6. Promotes challenger if superior and calls API reload

Options:
  --factor F        Drift perturbation factor (default: 2.5)
  --days N          Number of days of data to perturb (default: 7)
  --fast            Fast training mode with reduced trees
  --help, -h        Show this help message

Example:
  ./scripts/run_full_loop.sh --factor 2.5 --fast
EOF
}

FACTOR="2.5"
DAYS="7"
FAST_FLAG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --factor)
            FACTOR="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --fast)
            FAST_FLAG="--fast"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

cd "${ROOT_DIR}"

echo "======================================================================"
echo " AQI MLOps: Continuous Training Closed-Loop Demonstration"
echo " Workflow: Detect Drift -> Retrain -> Compare -> Promote -> API Reload"
echo "======================================================================"

echo ""
echo "[Step 1/6] Injecting synthetic data drift into recent data..."
python -m src.drift.inject_drift --factor "${FACTOR}" --days "${DAYS}"

echo ""
echo "[Step 2/6] Running data drift analysis..."
python -m src.drift.drift_check --current "data/processed/drifted_data.csv"

echo ""
echo "[Step 3/6] Ingesting updated data and regenerating feature matrix..."
python -m src.validate.run --input-path "data/processed/drifted_data.csv" || true
python -m src.features.run --input-path "data/processed/drifted_data.csv"

echo ""
echo "[Step 4/6] Retraining LightGBM challenger model..."
if [[ -n "${FAST_FLAG}" ]]; then
    python -m src.train.run --fast
else
    python -m src.train.run
fi

echo ""
echo "[Step 5/6] Evaluating challenger model on holdout set..."
python -m src.evaluate.run

echo ""
echo "[Step 6/6] Executing champion vs. challenger promotion decision..."
python -m src.drift.promote

echo ""
echo "======================================================================"
echo " Closed-Loop Demonstration Complete!"
echo " Reports generated:"
echo "   - Drift Metrics:     reports/drift_metrics.json"
echo "   - Drift HTML Report: reports/drift_report.html"
echo "   - Evaluation:        metrics.json"
echo "   - Promotion Decision: reports/promotion_decision.json"
echo "======================================================================"
