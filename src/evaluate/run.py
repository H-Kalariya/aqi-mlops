# Owner: M1 — Model evaluation: run module
"""Evaluate the latest trained model and write metrics.json.

Loads the latest model from MLflow, evaluates on validation data,
and writes metrics for the promotion step.

Usage:
    python -m src.evaluate.run [--val-path data/processed/val.csv]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.common.config import PROJECT_ROOT, get_config
from src.common.constants import REGISTERED_MODEL_NAME
from src.common.schema import FEATURE_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def evaluate_model(
    val_path: Path | None = None,
) -> dict:
    """Evaluate the latest model version on validation data.

    Args:
        val_path: Path to validation CSV.

    Returns:
        Dictionary with mae, rmse, model_version.
    """
    config = get_config()
    if val_path is None:
        val_path = PROJECT_ROOT / config["paths"]["processed"] / "val.csv"

    if not val_path.exists():
        raise FileNotFoundError(f"Validation data not found: {val_path}")

    # Load validation data
    logger.info("Loading validation data from %s", val_path)
    val_df = pd.read_csv(val_path)

    feature_cols = [c for c in FEATURE_COLUMNS if c in val_df.columns]
    target_col = "aqi_target"

    if "city" in val_df.columns:
        val_df["city"] = val_df["city"].astype("category")

    X_val = val_df[feature_cols]
    y_val = val_df[target_col]

    # Try loading from MLflow registry
    tracking_uri = config["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(tracking_uri)
    client = mlflow.MlflowClient()

    model = None
    model_version = "unknown"

    try:
        # Load the latest registered version
        versions = client.search_model_versions(
            f"name='{REGISTERED_MODEL_NAME}'",
            order_by=["version_number DESC"],
            max_results=1,
        )
        if versions:
            mv = versions[0]
            model_version = mv.version
            model_uri = f"models:/{REGISTERED_MODEL_NAME}/{model_version}"
            model = mlflow.lightgbm.load_model(model_uri)
            logger.info("Loaded model version %s from registry", model_version)
    except Exception:
        logger.warning("Could not load model from MLflow registry, trying local file")

    # Fallback to local model
    if model is None:
        model_path = PROJECT_ROOT / config["paths"]["models"] / "model.lgb"
        if model_path.exists():
            model = lgb.Booster(model_file=str(model_path))
            logger.info("Loaded model from local file: %s", model_path)
        else:
            raise FileNotFoundError("No model found in registry or locally")

    # Predict and evaluate
    y_pred = model.predict(X_val)
    mae = float(mean_absolute_error(y_val, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))

    # Per-horizon metrics
    horizon_metrics = {}
    if "horizon_h" in val_df.columns:
        for h in sorted(val_df["horizon_h"].unique()):
            mask = val_df["horizon_h"] == h
            if mask.sum() > 0:
                h_mae = float(mean_absolute_error(y_val[mask], y_pred[mask]))
                horizon_metrics[f"horizon_{h}_mae"] = h_mae

    result = {
        "mae": mae,
        "rmse": rmse,
        "model_version": str(model_version),
        "n_val_rows": len(val_df),
        "horizon_metrics": horizon_metrics,
    }

    logger.info("Evaluation — MAE: %.4f, RMSE: %.4f", mae, rmse)
    return result


def run_evaluate(val_path: Path | None = None) -> dict:
    """Run evaluation and save metrics.json.

    Args:
        val_path: Optional override for validation data path.

    Returns:
        Metrics dictionary.
    """
    result = evaluate_model(val_path=val_path)

    # Save metrics.json
    metrics_path = PROJECT_ROOT / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Saved metrics to %s", metrics_path)

    # Also save to reports directory
    config = get_config()
    reports_dir = PROJECT_ROOT / config["paths"]["reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="AQI Model Evaluation")
    parser.add_argument("--val-path", default=None, help="Path to validation CSV")
    args = parser.parse_args()

    val_path = Path(args.val_path) if args.val_path else None
    try:
        result = run_evaluate(val_path=val_path)
        print(json.dumps(result, indent=2))
    except Exception:
        logger.exception("Evaluation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
