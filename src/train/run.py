# Owner: M1 — Model training: run module
"""Train a LightGBM regressor and register with MLflow.

- Logs params, MAE, RMSE, feature importance to MLflow
- Registers as 'aqi-forecaster'
- First model gets alias 'champion'; subsequent runs get 'challenger'
- Tags each run with data_version (DVC hash) and git SHA

Usage:
    python -m src.train.run [--train-path data/processed/train.csv]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.common.config import PROJECT_ROOT, get_config, get_params
from src.common.constants import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    REGISTERED_MODEL_NAME,
)
from src.common.schema import FEATURE_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _get_git_sha() -> str:
    """Get the current git commit SHA, or 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=5,
        )
        return result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _get_data_version() -> str:
    """Get a hash of the DVC-tracked data files for traceability."""
    dvc_files = list(PROJECT_ROOT.glob("data/**/*.dvc")) + list(
        PROJECT_ROOT.glob("*.dvc")
    )
    if not dvc_files:
        # Fallback: hash the raw data file
        raw_path = PROJECT_ROOT / "data" / "raw" / "aqi_raw.csv"
        if raw_path.exists():
            content = raw_path.read_bytes()[:4096]
            return hashlib.md5(content).hexdigest()[:8]
        return "no-dvc"

    hashes = []
    for f in sorted(dvc_files):
        hashes.append(hashlib.md5(f.read_bytes()).hexdigest())
    return hashlib.md5("".join(hashes).encode()).hexdigest()[:8]


def _has_champion(client: mlflow.MlflowClient) -> bool:
    """Check if a champion alias already exists in the registry."""
    try:
        mv = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, CHAMPION_ALIAS)
        return mv is not None
    except Exception:
        return False


def run_train(
    train_path: Path | None = None,
    val_path: Path | None = None,
    fast: bool = False,
) -> dict:

    """Train LightGBM model and register with MLflow.

    Args:
        train_path: Path to training CSV.
        val_path: Path to validation CSV.

    Returns:
        Dictionary with model version, MAE, RMSE.
    """
    config = get_config()
    params = get_params()

    if train_path is None:
        train_path = PROJECT_ROOT / config["paths"]["processed"] / "train.csv"
    if val_path is None:
        val_path = PROJECT_ROOT / config["paths"]["processed"] / "val.csv"

    if not train_path.exists():
        raise FileNotFoundError(f"Training data not found: {train_path}")
    if not val_path.exists():
        raise FileNotFoundError(f"Validation data not found: {val_path}")

    # Load data
    logger.info("Loading training data from %s", train_path)
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    # Prepare feature columns (use only those present in the data)
    feature_cols = [c for c in FEATURE_COLUMNS if c in train_df.columns]
    target_col = "aqi_target"

    # Handle categorical city column
    if "city" in train_df.columns:
        train_df["city"] = train_df["city"].astype("category")
        val_df["city"] = val_df["city"].astype("category")

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_val = val_df[feature_cols]
    y_val = val_df[target_col]

    logger.info("Training: %d rows, %d features", len(X_train), len(feature_cols))
    logger.info("Validation: %d rows", len(X_val))

    # LightGBM parameters
    lgbm_params = params["lgbm"].copy()
    seed = params.get("seed", 42)
    lgbm_params["random_state"] = seed
    early_stopping_rounds = params["train"]["early_stopping_rounds"]

    # Set MLflow tracking URI
    tracking_uri = config["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("aqi-forecaster")

    # Train with MLflow tracking
    with mlflow.start_run() as run:
        # Log parameters
        mlflow.log_params(lgbm_params)
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train_rows", len(X_train))
        mlflow.log_param("n_val_rows", len(X_val))
        mlflow.log_param("seed", seed)

        # Tags
        git_sha = _get_git_sha()
        data_version = _get_data_version()
        mlflow.set_tag("git_sha", git_sha)
        mlflow.set_tag("data_version", data_version)

        # Create and train model
        categorical_features = ["city"] if "city" in feature_cols else []
        train_set = lgb.Dataset(
            X_train,
            label=y_train,
            categorical_feature=categorical_features,
        )
        val_set = lgb.Dataset(
            X_val,
            label=y_val,
            categorical_feature=categorical_features,
            reference=train_set,
        )

        boost_rounds = 30 if fast else lgbm_params.pop("n_estimators", 500)
        model = lgb.train(
            lgbm_params,
            train_set,
            num_boost_round=boost_rounds,
            valid_sets=[train_set, val_set],
            valid_names=["train", "val"],

            callbacks=[
                lgb.early_stopping(stopping_rounds=early_stopping_rounds),
                lgb.log_evaluation(period=50),
            ],
        )

        # Evaluate
        y_pred = model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))

        mlflow.log_metric("mae", mae)
        mlflow.log_metric("rmse", rmse)
        logger.info("MAE: %.4f, RMSE: %.4f", mae, rmse)

        # Log feature importance
        importance = dict(
            zip(
                feature_cols,
                model.feature_importance(importance_type="gain").tolist(),
                strict=False,
            )
        )

        mlflow.log_dict(importance, "feature_importance.json")

        # Log model
        mlflow.lightgbm.log_model(
            model,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
        )

        # Also save locally as fallback
        models_dir = PROJECT_ROOT / config["paths"]["models"]
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / "model.lgb"
        model.save_model(str(model_path))
        logger.info("Saved model locally to %s", model_path)

        # Save as joblib too for easier loading
        joblib_path = models_dir / "model.joblib"
        joblib.dump(model, joblib_path)

        # Set alias
        client = mlflow.MlflowClient()
        # Get the latest version
        latest_versions = client.search_model_versions(
            f"name='{REGISTERED_MODEL_NAME}'",
            order_by=["version_number DESC"],
            max_results=1,
        )
        if latest_versions:
            version = latest_versions[0].version
            if _has_champion(client):
                # There's already a champion — new model is challenger
                client.set_registered_model_alias(
                    REGISTERED_MODEL_NAME, CHALLENGER_ALIAS, version
                )
                alias = CHALLENGER_ALIAS
                logger.info("Registered version %s as %s", version, CHALLENGER_ALIAS)
            else:
                # First model — set as champion
                client.set_registered_model_alias(
                    REGISTERED_MODEL_NAME, CHAMPION_ALIAS, version
                )
                alias = CHAMPION_ALIAS
                logger.info("Registered version %s as %s", version, CHAMPION_ALIAS)
        else:
            version = "unknown"
            alias = "unknown"

        result = {
            "model_version": str(version),
            "alias": alias,
            "mae": mae,
            "rmse": rmse,
            "run_id": run.info.run_id,
            "git_sha": git_sha,
            "data_version": data_version,
        }

    return result


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="AQI Model Training")
    parser.add_argument("--train-path", default=None, help="Path to training CSV")
    parser.add_argument("--val-path", default=None, help="Path to validation CSV")
    parser.add_argument(
        "--fast", action="store_true", help="Train with fewer boost rounds"
    )
    args = parser.parse_args()

    train_path = Path(args.train_path) if args.train_path else None
    val_path = Path(args.val_path) if args.val_path else None

    try:
        result = run_train(
            train_path=train_path, val_path=val_path, fast=args.fast
        )

        logger.info("Training result: %s", json.dumps(result, indent=2))

        # Save metrics
        metrics_path = PROJECT_ROOT / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info("Saved metrics to %s", metrics_path)
    except Exception:
        logger.exception("Training failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
