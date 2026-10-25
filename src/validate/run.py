# Owner: M1 — Data validation: run module
"""Validate raw ingested data using Pandera schemas.

Checks:
- Column presence and types
- Range checks (pm25 0-1000, aqi 0-500, etc.)
- Null checks
- Hourly timestamp monotonicity per city

Usage:
    python -m src.validate.run [--input data/raw/aqi_raw.csv]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd
import pandera as pa

from src.common.config import PROJECT_ROOT, get_config
from src.common.schema import RAW_SCHEMA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def validate_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Validate a DataFrame against the raw schema.

    Args:
        df: Raw ingested data.

    Returns:
        Tuple of (validated DataFrame, report dict).

    Raises:
        pandera.errors.SchemaErrors: If validation fails with lazy=True.
    """
    report: dict = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "null_counts": df.isnull().sum().to_dict(),
        "issues": [],
    }

    # Ensure timestamp is datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Check for duplicate timestamps per city
    if "timestamp" in df.columns and "city" in df.columns:
        dupes = df.groupby("city")["timestamp"].apply(lambda x: x.duplicated().sum())
        for city_name, dupe_count in dupes.items():
            if dupe_count > 0:
                report["issues"].append(
                    f"City {city_name}: {dupe_count} duplicate timestamps"
                )
                logger.warning(
                    "City %s has %d duplicate timestamps", city_name, dupe_count
                )

    # Check hourly monotonicity per city
    if "timestamp" in df.columns and "city" in df.columns:
        for city_name, group in df.groupby("city"):
            sorted_ts = group["timestamp"].sort_values()
            diffs = sorted_ts.diff().dropna()
            non_hourly = diffs[diffs != pd.Timedelta(hours=1)]
            if len(non_hourly) > 0:
                report["issues"].append(
                    f"City {city_name}: {len(non_hourly)} non-hourly gaps"
                )

    # Drop rows with all-null pollutant values
    pollutant_cols = ["pm25", "pm10", "no2", "so2", "co", "o3", "aqi"]
    existing_cols = [c for c in pollutant_cols if c in df.columns]
    if existing_cols:
        all_null_mask = df[existing_cols].isnull().all(axis=1)
        n_dropped = all_null_mask.sum()
        if n_dropped > 0:
            df = df[~all_null_mask].reset_index(drop=True)
            report["issues"].append(
                f"Dropped {n_dropped} rows with all-null pollutants"
            )
            logger.warning("Dropped %d rows with all-null pollutant values", n_dropped)

    # Fill remaining nulls with forward fill then backward fill per city
    if "city" in df.columns:
        fill_cols = [c for c in df.columns if c not in ["timestamp", "city"]]
        if fill_cols:
            df[fill_cols] = df.groupby("city")[fill_cols].transform(
                lambda g: g.ffill().bfill()
            )

    # Run Pandera validation
    try:
        validated = RAW_SCHEMA.validate(df, lazy=True)
        report["validation"] = "PASSED"
        logger.info("✅ Pandera validation PASSED")
    except pa.errors.SchemaErrors as exc:
        report["validation"] = "FAILED"
        report["schema_errors"] = str(exc)
        logger.error("❌ Pandera validation FAILED: %s", exc)
        raise

    report["validated_rows"] = len(validated)
    return validated, report


def run_validate(input_path: Path | None = None) -> pd.DataFrame:
    """Run validation on the raw data file.

    Args:
        input_path: Path to raw CSV. Defaults to data/raw/aqi_raw.csv.

    Returns:
        Validated DataFrame.
    """
    config = get_config()
    if input_path is None:
        input_path = PROJECT_ROOT / config["paths"]["raw"] / "aqi_raw.csv"

    if not input_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {input_path}")

    logger.info("Loading raw data from %s", input_path)
    df = pd.read_csv(input_path, parse_dates=["timestamp"])

    validated_df, report = validate_data(df)

    # Save validated data
    processed_dir = PROJECT_ROOT / config["paths"]["raw"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / "aqi_validated.csv"
    validated_df.to_csv(output_path, index=False)
    logger.info("Saved validated data to %s", output_path)

    # Save validation report
    reports_dir = PROJECT_ROOT / config["paths"]["reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Saved validation report to %s", report_path)

    return validated_df


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="AQI Data Validation")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to raw CSV file",
    )
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    try:
        run_validate(input_path=input_path)
    except Exception:
        logger.exception("Validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
