# Owner: M1 — Feature engineering: run module
"""Feature engineering pipeline.

Creates:
- Lag features (aqi_lag_1/3/6/12/24, pm25_lag_1/24)
- Rolling features (aqi_roll_mean_6/24, aqi_roll_std_24)
- Calendar features (hour, day_of_week, month)
- Multi-horizon stacked training frame with horizon_h and aqi_target
- Time-based train/validation split (no shuffling, no leakage)

Usage:
    python -m src.features.run [--input data/raw/aqi_validated.csv]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import PROJECT_ROOT, get_config, get_params

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag features per city (no leakage across cities).

    Args:
        df: DataFrame sorted by timestamp within each city.

    Returns:
        DataFrame with lag columns added.
    """
    config = get_config()
    aqi_lags = config["features"]["aqi_lags"]
    pm25_lags = config["features"]["pm25_lags"]

    for lag in aqi_lags:
        df[f"aqi_lag_{lag}"] = df.groupby("city")["aqi"].shift(lag)

    for lag in pm25_lags:
        df[f"pm25_lag_{lag}"] = df.groupby("city")["pm25"].shift(lag)

    logger.info("Added lag features: aqi_lags=%s, pm25_lags=%s", aqi_lags, pm25_lags)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling mean/std features per city.

    Args:
        df: DataFrame sorted by timestamp within each city.

    Returns:
        DataFrame with rolling columns added.
    """
    config = get_config()
    mean_windows = config["features"]["aqi_roll_mean_windows"]
    std_windows = config["features"]["aqi_roll_std_windows"]

    for window in mean_windows:
        df[f"aqi_roll_mean_{window}"] = df.groupby("city")["aqi"].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )

    for window in std_windows:
        df[f"aqi_roll_std_{window}"] = df.groupby("city")["aqi"].transform(
            lambda x: x.rolling(window=window, min_periods=1).std().fillna(0)
        )

    logger.info(
        "Added rolling features: mean_windows=%s, std_windows=%s",
        mean_windows,
        std_windows,
    )
    return df


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features from the timestamp.

    Args:
        df: DataFrame with a timestamp column.

    Returns:
        DataFrame with hour, day_of_week, month columns.
    """
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    logger.info("Added calendar features: hour, day_of_week, month")
    return df


def create_multi_horizon_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Stack the data across horizons 1..24 with horizon_h as a feature.

    For each row at time t and each horizon h in 1..24:
    - Features are from time t
    - Target (aqi_target) = AQI at time t+h

    Args:
        df: Feature-engineered DataFrame sorted by timestamp per city.

    Returns:
        Stacked DataFrame with horizon_h and aqi_target columns.
    """
    params = get_params()
    horizons = params["train"]["horizons"]

    frames: list[pd.DataFrame] = []
    for city_name, city_df in df.groupby("city"):
        city_df = city_df.sort_values("timestamp").reset_index(drop=True)
        for h in horizons:
            horizon_df = city_df.copy()
            horizon_df["horizon_h"] = h
            # Target = AQI at t+h (shift backwards by h to get future value)
            horizon_df["aqi_target"] = city_df["aqi"].shift(-h)
            frames.append(horizon_df)

    stacked = pd.concat(frames, ignore_index=True)
    # Drop rows where target is NaN (last h rows per city per horizon)
    stacked.dropna(subset=["aqi_target"], inplace=True)
    stacked.reset_index(drop=True, inplace=True)
    logger.info(
        "Created multi-horizon frame: %d rows across %d horizons",
        len(stacked),
        len(horizons),
    )
    return stacked


def time_based_split(
    df: pd.DataFrame, split_ratio: float = 0.8
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split data by time — no shuffling, no leakage.

    Args:
        df: Multi-horizon stacked DataFrame.
        split_ratio: Fraction of data for training.

    Returns:
        Tuple of (train_df, val_df).
    """
    # Get unique timestamps and sort
    unique_ts = df["timestamp"].sort_values().unique()
    split_idx = int(len(unique_ts) * split_ratio)
    split_time = unique_ts[split_idx]

    train_df = df[df["timestamp"] < split_time].reset_index(drop=True)
    val_df = df[df["timestamp"] >= split_time].reset_index(drop=True)

    logger.info(
        "Time-based split at %s: train=%d rows, val=%d rows",
        split_time,
        len(train_df),
        len(val_df),
    )
    return train_df, val_df


def engineer_features(df: pd.DataFrame, horizon: int = 24) -> pd.DataFrame:
    """Helper to run end-to-end feature engineering on a DataFrame."""
    df = df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["city", "timestamp"]).reset_index(drop=True)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_calendar_features(df)
    df = df.dropna(subset=[c for c in df.columns if "lag" in c or "roll" in c]).reset_index(drop=True)
    return create_multi_horizon_frame(df)



def make_train_val_split(
    df: pd.DataFrame, train_ratio: float = 0.8
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Helper alias for time_based_split."""
    return time_based_split(df, split_ratio=train_ratio)



def run_features(input_path: Path | None = None) -> None:
    """Run the full feature engineering pipeline.

    Args:
        input_path: Path to validated CSV. Defaults to data/raw/aqi_validated.csv.
    """
    config = get_config()
    if input_path is None:
        input_path = PROJECT_ROOT / config["paths"]["raw"] / "aqi_validated.csv"

    if not input_path.exists():
        raise FileNotFoundError(f"Validated data not found: {input_path}")

    logger.info("Loading validated data from %s", input_path)
    df = pd.read_csv(input_path, parse_dates=["timestamp"])

    # Sort by city and timestamp
    df.sort_values(["city", "timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Feature engineering
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_calendar_features(df)

    # Drop rows with NaN from lag computation
    max_lag = max(config["features"]["aqi_lags"] + config["features"]["pm25_lags"])
    initial_len = len(df)
    df.dropna(
        subset=[
            col for col in df.columns if "lag" in col or "roll" in col
        ],
        inplace=True,
    )
    df.reset_index(drop=True, inplace=True)
    logger.info(
        "Dropped %d rows with NaN lags (max_lag=%d)",
        initial_len - len(df),
        max_lag,
    )

    # Create multi-horizon stacked frame
    stacked = create_multi_horizon_frame(df)

    # Time-based split
    split_ratio = config["features"]["train_split_ratio"]
    train_df, val_df = time_based_split(stacked, split_ratio)

    # Save outputs
    processed_dir = PROJECT_ROOT / config["paths"]["processed"]
    processed_dir.mkdir(parents=True, exist_ok=True)

    stacked.to_csv(processed_dir / "features.csv", index=False)
    train_df.to_csv(processed_dir / "train.csv", index=False)
    val_df.to_csv(processed_dir / "val.csv", index=False)

    logger.info("Saved feature files to %s", processed_dir)
    logger.info("  features.csv: %d rows", len(stacked))
    logger.info("  train.csv:    %d rows", len(train_df))
    logger.info("  val.csv:      %d rows", len(val_df))


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="AQI Feature Engineering")
    parser.add_argument("--input", default=None, help="Path to validated CSV file")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    try:
        run_features(input_path=input_path)
    except Exception:
        logger.exception("Feature engineering failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
