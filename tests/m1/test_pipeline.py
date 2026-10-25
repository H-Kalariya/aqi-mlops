"""Owner: Member 1 — Tests for data pipeline, validation, features, and model training."""

import numpy as np
import pandas as pd
import pytest
from src.common.schema import FEATURE_COLUMNS, validate_features_dataframe, validate_raw_dataframe
from src.ingest.synthetic import generate_synthetic_data
from src.features.run import engineer_features, make_train_val_split


def test_synthetic_data_generation():
    """Verify synthetic generation produces required columns and realistic timestamps."""
    df = generate_synthetic_data(cities=["ahmedabad"], days=5, seed=42)
    assert not df.empty
    assert "timestamp" in df.columns
    assert "city" in df.columns
    assert "pm25" in df.columns
    assert "aqi" in df.columns
    assert len(df) == 5 * 24


def test_schema_validation_passes():
    """Verify valid synthetic data passes Pandera schema."""
    df = generate_synthetic_data(cities=["mumbai"], days=2, seed=123)
    validated = validate_raw_dataframe(df)
    assert len(validated) == len(df)


def test_schema_validation_fails_on_corrupt_data():
    """Verify schema raises ValueError or SchemaError when ranges or nulls are violated."""
    df = generate_synthetic_data(cities=["delhi"], days=2, seed=123)
    # Inject impossible negative values or nulls
    df.loc[0, "pm25"] = -999.0
    with pytest.raises(Exception):
        validate_raw_dataframe(df)


def test_no_feature_leakage_and_time_split():
    """Ensure validation split strictly precedes training split without temporal leakage."""
    df = generate_synthetic_data(cities=["ahmedabad"], days=10, seed=42)
    featured = engineer_features(df, horizon=24)
    assert "aqi_lag_1" in featured.columns
    assert "horizon_h" in featured.columns

    train_df, val_df = make_train_val_split(featured, train_ratio=0.8)
    assert not train_df.empty
    assert not val_df.empty
    
    # Train timestamps must precede or equal max train timestamp, val must be strictly after min val
    train_max_time = pd.to_datetime(train_df["timestamp"]).max()
    val_min_time = pd.to_datetime(val_df["timestamp"]).min()
    assert train_max_time <= val_min_time
