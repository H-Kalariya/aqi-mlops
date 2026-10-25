# Owner: M2 — FastAPI serving: model loader
"""Model loader with MLflow registry support and local fallback.

Loading priority:
1. Champion alias from MLflow registry
2. Bundled local model file (models/model.lgb)
3. No model → /predict returns 503, /health shows model_loaded=false
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.common.constants import (
    CHAMPION_ALIAS,
    FEATURE_COLUMNS,
    FORECAST_HORIZONS,
    REGISTERED_MODEL_NAME,
)

logger = logging.getLogger(__name__)


class ModelLoader:
    """Loads and serves the AQI forecasting model."""

    def __init__(self) -> None:
        self.model: Any = None
        self.model_version: str | None = None
        self.model_alias: str | None = None
        self.is_loaded: bool = False

    def load(self) -> None:
        """Load model from MLflow registry, falling back to local file."""
        # Try MLflow registry first
        try:
            self._load_from_registry()
            return
        except Exception as exc:
            logger.warning("MLflow registry unavailable: %s", exc)

        # Fallback to local model file
        try:
            self._load_from_file()
            return
        except Exception as exc:
            logger.warning("Local model file unavailable: %s", exc)

        # No model available
        self.model = None
        self.model_version = None
        self.model_alias = None
        self.is_loaded = False
        logger.error("No model available. /predict will return 503.")

    def _load_from_registry(self) -> None:
        """Load champion model from MLflow registry."""
        import mlflow
        import mlflow.lightgbm

        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.MlflowClient()

        mv = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, CHAMPION_ALIAS)
        model_uri = f"models:/{REGISTERED_MODEL_NAME}@{CHAMPION_ALIAS}"
        self.model = mlflow.lightgbm.load_model(model_uri)
        self.model_version = str(mv.version)
        self.model_alias = CHAMPION_ALIAS
        self.is_loaded = True
        logger.info(
            "Loaded champion model v%s from MLflow registry", self.model_version
        )

    def _load_from_file(self) -> None:
        """Load model from local file as fallback."""
        import lightgbm as lgb

        # Try multiple known locations
        search_paths = [
            Path("models/model.lgb"),
            Path("/app/models/model.lgb"),
            Path(os.environ.get("MODEL_PATH", "models/model.lgb")),
        ]

        for model_path in search_paths:
            if model_path.exists():
                self.model = lgb.Booster(model_file=str(model_path))
                self.model_version = "local"
                self.model_alias = "local-fallback"
                self.is_loaded = True
                logger.info("Loaded local model from %s", model_path)
                return

        raise FileNotFoundError("No local model file found")

    def predict(
        self,
        city: str,
        readings: dict[str, float],
        history: list[dict[str, float]] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate 24-hour AQI forecast.

        Args:
            city: City name.
            readings: Current pollutant and weather readings.
            history: Optional 24 hourly historical records for lag computation.

        Returns:
            List of 24 forecast dicts with horizon_h and aqi.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Model not loaded")

        # Build feature vector for each horizon
        forecasts: list[dict[str, Any]] = []

        # Compute lag and rolling features from history
        lag_features = self._compute_lag_features(readings, history)
        calendar_features = self._compute_calendar_features()

        for h in FORECAST_HORIZONS:
            feature_row: dict[str, Any] = {
                "city": city,
                **readings,
                "aqi": readings.get(
                    "aqi",
                    self._estimate_aqi(readings),
                ),
                **lag_features,
                **calendar_features,
                "horizon_h": h,
            }

            # Create DataFrame with proper column order
            feature_cols = [c for c in FEATURE_COLUMNS if c in feature_row]
            df = pd.DataFrame([{c: feature_row.get(c, 0) for c in feature_cols}])

            # Handle categorical
            if "city" in df.columns:
                df["city"] = df["city"].astype("category")

            # Predict
            pred = float(self.model.predict(df)[0])
            pred = max(0, min(500, pred))  # Clip to valid AQI range
            forecasts.append({"horizon_h": h, "aqi": pred})

        return forecasts

    @staticmethod
    def _estimate_aqi(readings: dict[str, float]) -> float:
        """Rough AQI estimate from PM2.5 when actual AQI is not provided.

        Args:
            readings: Current readings dict.

        Returns:
            Estimated AQI value.
        """
        pm25 = readings.get("pm25", 50)
        # Simplified AQI = ~PM2.5 * 1.5 (rough linear approximation)
        return min(500, max(0, pm25 * 1.5))

    @staticmethod
    def _compute_lag_features(
        readings: dict[str, float],
        history: list[dict[str, float]] | None,
    ) -> dict[str, float]:
        """Compute lag features from history or approximate from current readings.

        Args:
            readings: Current readings.
            history: Optional historical records (most recent first).

        Returns:
            Dictionary of lag feature values.
        """
        current_aqi = readings.get("aqi", readings.get("pm25", 50) * 1.5)
        current_pm25 = readings.get("pm25", 50)

        if history and len(history) >= 24:
            aqi_vals = [h.get("aqi", current_aqi) for h in history]
            pm25_vals = [h.get("pm25", current_pm25) for h in history]
            return {
                "aqi_lag_1": aqi_vals[0] if len(aqi_vals) > 0 else current_aqi,
                "aqi_lag_3": aqi_vals[2] if len(aqi_vals) > 2 else current_aqi,
                "aqi_lag_6": aqi_vals[5] if len(aqi_vals) > 5 else current_aqi,
                "aqi_lag_12": aqi_vals[11] if len(aqi_vals) > 11 else current_aqi,
                "aqi_lag_24": aqi_vals[23] if len(aqi_vals) > 23 else current_aqi,
                "pm25_lag_1": pm25_vals[0] if len(pm25_vals) > 0 else current_pm25,
                "pm25_lag_24": pm25_vals[23] if len(pm25_vals) > 23 else current_pm25,
                "aqi_roll_mean_6": float(np.mean(aqi_vals[:6])),
                "aqi_roll_mean_24": float(np.mean(aqi_vals[:24])),
                "aqi_roll_std_24": float(np.std(aqi_vals[:24])),
            }

        # Fallback: approximate from current readings
        return {
            "aqi_lag_1": current_aqi,
            "aqi_lag_3": current_aqi,
            "aqi_lag_6": current_aqi,
            "aqi_lag_12": current_aqi,
            "aqi_lag_24": current_aqi,
            "pm25_lag_1": current_pm25,
            "pm25_lag_24": current_pm25,
            "aqi_roll_mean_6": current_aqi,
            "aqi_roll_mean_24": current_aqi,
            "aqi_roll_std_24": 0.0,
        }

    @staticmethod
    def _compute_calendar_features() -> dict[str, int]:
        """Get current calendar features.

        Returns:
            Dictionary with hour, day_of_week, month.
        """
        import datetime

        now = datetime.datetime.now(datetime.UTC)
        return {
            "hour": now.hour,
            "day_of_week": now.weekday(),
            "month": now.month,
        }
