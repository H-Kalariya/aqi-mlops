"""Owner: Member 3 — Continuous Training: Synthetic data drift injector.

Injects a controlled distribution shift (e.g., Diwali smog spike or sensor degradation)
into recent AQI data to test the automated drift detection and retraining loop.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import get_config


def inject_drift(
    input_file: Path,
    output_file: Path,
    factor: float = 2.5,
    days: int = 7,
    city: str | None = None,
) -> pd.DataFrame:
    """Inject a multiplicative and additive shift into the most recent N days of data.

    Args:
        input_file: Path to clean processed or raw CSV data.
        output_file: Path to write the drifted CSV data.
        factor: Multiplier for PM2.5 and PM10 to simulate severe smog/drift.
        days: Number of trailing days to perturb.
        city: Optional city filter (e.g. 'delhi'). If None, perturbs all cities.

    Returns:
        pd.DataFrame containing the modified dataset.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    df = pd.read_csv(input_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    max_time = df["timestamp"].max()
    cutoff_time = max_time - pd.Timedelta(days=days)

    mask = df["timestamp"] >= cutoff_time
    if city:
        mask = mask & (df["city"] == city)

    num_shifted = mask.sum()
    print(
        f"[inject_drift] Injecting drift for {num_shifted} records after {cutoff_time.isoformat()} (factor={factor})"
    )

    # Apply severe smog effect: scale PM2.5 and PM10 and calculate higher AQI
    if "pm25" in df.columns:
        df.loc[mask, "pm25"] = df.loc[mask, "pm25"] * factor + np.random.normal(
            15, 5, num_shifted
        )
        df.loc[mask, "pm25"] = df.loc[mask, "pm25"].clip(upper=999.0)

    if "pm10" in df.columns:
        df.loc[mask, "pm10"] = df.loc[mask, "pm10"] * (factor * 0.9) + 20.0
        df.loc[mask, "pm10"] = df.loc[mask, "pm10"].clip(upper=999.0)

    if "aqi" in df.columns and "pm25" in df.columns:
        # Re-derive AQI approximately based on inflated PM2.5
        df.loc[mask, "aqi"] = (df.loc[mask, "pm25"] * 1.6 + 10.0).clip(
            lower=10.0, upper=500.0
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"[inject_drift] Drifted dataset saved to: {output_file}")
    return df


def parse_args() -> argparse.Namespace:
    cfg = get_config()
    default_input = Path(cfg["paths"]["processed"]) / "features.csv"
    if not default_input.exists():
        default_input = Path(cfg["paths"]["raw"]) / "aqi_raw.csv"

    default_output = Path(cfg["paths"]["processed"]) / "drifted_data.csv"

    parser = argparse.ArgumentParser(
        description="Inject distribution drift into AQI dataset"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="Path to source CSV file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path to save drifted CSV file",
    )
    parser.add_argument(
        "--factor",
        type=float,
        default=2.5,
        help="Multiplication factor for PM pollutants (default: 2.5)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=cfg["drift"]["current_window_days"],
        help=f"Number of recent days to perturb (default: {cfg['drift']['current_window_days']})",
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Target city to perturb (default: all cities)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inject_drift(
            input_file=args.input,
            output_file=args.output,
            factor=args.factor,
            days=args.days,
            city=args.city,
        )
        return 0
    except Exception as e:
        print(f"[inject_drift] Error injecting drift: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
