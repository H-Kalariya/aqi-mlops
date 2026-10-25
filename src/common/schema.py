# Owner: Shared (M1 as repo/release manager) — Feature schema (single source of truth)
"""Pandera schema defining the canonical AQI data format.

This is the single source of truth for column names, types and valid ranges
used across ingest → validate → features → train → serve.
"""

from __future__ import annotations

from typing import Final

import pandera as pa
from pandera import Column, DataFrameSchema

# ── Raw columns (from ingestion) ──────────────────────────────────────────────
RAW_COLUMNS: Final[list[str]] = [
    "timestamp",
    "city",
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3",
    "temperature",
    "humidity",
    "wind_speed",
    "aqi",
]

# ── Engineered feature columns ────────────────────────────────────────────────
LAG_COLUMNS: Final[list[str]] = [
    "aqi_lag_1",
    "aqi_lag_3",
    "aqi_lag_6",
    "aqi_lag_12",
    "aqi_lag_24",
    "pm25_lag_1",
    "pm25_lag_24",
]

ROLLING_COLUMNS: Final[list[str]] = [
    "aqi_roll_mean_6",
    "aqi_roll_mean_24",
    "aqi_roll_std_24",
]

CALENDAR_COLUMNS: Final[list[str]] = [
    "hour",
    "day_of_week",
    "month",
]

HORIZON_COLUMN: Final[str] = "horizon_h"
TARGET_COLUMN: Final[str] = "aqi_target"

# All feature columns used by the model (excludes timestamp and target)
FEATURE_COLUMNS: Final[list[str]] = [
    "city",
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3",
    "temperature",
    "humidity",
    "wind_speed",
    "aqi",
    *LAG_COLUMNS,
    *ROLLING_COLUMNS,
    *CALENDAR_COLUMNS,
    HORIZON_COLUMN,
]

# ── Pandera schema for raw ingested data ──────────────────────────────────────
RAW_SCHEMA: DataFrameSchema = DataFrameSchema(
    columns={
        "timestamp": Column(pa.DateTime, nullable=False),
        "city": Column(str, nullable=False),
        "pm25": Column(float, pa.Check.in_range(0, 1000), nullable=True),
        "pm10": Column(float, pa.Check.in_range(0, 1000), nullable=True),
        "no2": Column(float, pa.Check.in_range(0, 500), nullable=True),
        "so2": Column(float, pa.Check.in_range(0, 200), nullable=True),
        "co": Column(float, pa.Check.in_range(0, 50), nullable=True),
        "o3": Column(float, pa.Check.in_range(0, 500), nullable=True),
        "temperature": Column(float, pa.Check.in_range(-10, 55), nullable=True),
        "humidity": Column(float, pa.Check.in_range(0, 100), nullable=True),
        "wind_speed": Column(float, pa.Check.in_range(0, 50), nullable=True),
        "aqi": Column(float, pa.Check.in_range(0, 500), nullable=True),
    },
    coerce=True,
    strict=False,
    ordered=False,
)

# ── Pandera schema for the processed / feature-engineered data ────────────────
FEATURE_SCHEMA: DataFrameSchema = DataFrameSchema(
    columns={
        "timestamp": Column(pa.DateTime, nullable=False),
        "city": Column(str, nullable=False),
        "pm25": Column(float, nullable=False),
        "pm10": Column(float, nullable=False),
        "no2": Column(float, nullable=False),
        "so2": Column(float, nullable=False),
        "co": Column(float, nullable=False),
        "o3": Column(float, nullable=False),
        "temperature": Column(float, nullable=False),
        "humidity": Column(float, nullable=False),
        "wind_speed": Column(float, nullable=False),
        "aqi": Column(float, nullable=False),
        # Lags
        "aqi_lag_1": Column(float, nullable=False),
        "aqi_lag_3": Column(float, nullable=False),
        "aqi_lag_6": Column(float, nullable=False),
        "aqi_lag_12": Column(float, nullable=False),
        "aqi_lag_24": Column(float, nullable=False),
        "pm25_lag_1": Column(float, nullable=False),
        "pm25_lag_24": Column(float, nullable=False),
        # Rolling
        "aqi_roll_mean_6": Column(float, nullable=False),
        "aqi_roll_mean_24": Column(float, nullable=False),
        "aqi_roll_std_24": Column(float, nullable=False),
        # Calendar
        "hour": Column(int, pa.Check.in_range(0, 23), nullable=False),
        "day_of_week": Column(int, pa.Check.in_range(0, 6), nullable=False),
        "month": Column(int, pa.Check.in_range(1, 12), nullable=False),
        # Horizon
        "horizon_h": Column(int, pa.Check.in_range(1, 24), nullable=False),
        # Target
        "aqi_target": Column(float, nullable=False),
    },
    coerce=True,
    strict=False,
    ordered=False,
)


def validate_raw_dataframe(df: "pd.DataFrame") -> "pd.DataFrame":
    """Validate a raw DataFrame against RAW_SCHEMA."""
    import pandas as pd
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return RAW_SCHEMA.validate(df)


def validate_features_dataframe(df: "pd.DataFrame") -> "pd.DataFrame":
    """Validate a features DataFrame against FEATURE_SCHEMA."""
    import pandas as pd
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return FEATURE_SCHEMA.validate(df)

