# Owner: M1 — Data ingestion: snapshot loader
"""Load pre-saved CSV snapshots from data/snapshot/ as offline fallback."""

from __future__ import annotations

import logging

import pandas as pd

from src.common.config import PROJECT_ROOT, get_config

logger = logging.getLogger(__name__)


def load_snapshot(city: str | None = None) -> pd.DataFrame:
    """Load snapshot CSV files from the configured snapshot directory.

    Args:
        city: If specified, load only that city's snapshot. Otherwise load all.

    Returns:
        DataFrame with raw AQI readings.

    Raises:
        FileNotFoundError: If no snapshot files are found.
    """
    config = get_config()
    snapshot_dir = PROJECT_ROOT / config["ingest"]["snapshot_dir"]

    if not snapshot_dir.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

    csv_files = list(snapshot_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files in snapshot directory: {snapshot_dir}")

    dfs: list[pd.DataFrame] = []
    for csv_file in csv_files:
        if city and city not in csv_file.stem.lower():
            continue
        df = pd.read_csv(csv_file, parse_dates=["timestamp"])
        dfs.append(df)
        logger.info("Loaded snapshot %s: %d records", csv_file.name, len(df))

    if not dfs:
        raise FileNotFoundError(
            f"No snapshot files found for city={city} in {snapshot_dir}"
        )

    combined = pd.concat(dfs, ignore_index=True)
    combined.sort_values(["timestamp", "city"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    logger.info("Total snapshot records: %d", len(combined))
    return combined
