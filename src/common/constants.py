# Owner: Shared (M1 as repo/release manager) — Project constants
"""Project-wide constants. Import from here, never hardcode."""

from __future__ import annotations

from typing import Final

# ── Cities ────────────────────────────────────────────────────────────────────
CITIES: Final[list[str]] = ["ahmedabad", "delhi", "mumbai"]

# ── Model ─────────────────────────────────────────────────────────────────────
REGISTERED_MODEL_NAME: Final[str] = "aqi-forecaster"
CHAMPION_ALIAS: Final[str] = "champion"
CHALLENGER_ALIAS: Final[str] = "challenger"

# ── Horizons ──────────────────────────────────────────────────────────────────
FORECAST_HORIZONS: Final[list[int]] = list(range(1, 25))  # 1..24

# ── Prometheus metric names (fixed contract) ─────────────────────────────────
METRIC_REQUESTS_TOTAL: Final[str] = "aqi_http_requests_total"
METRIC_LATENCY_SECONDS: Final[str] = "aqi_request_latency_seconds"
METRIC_ERRORS_TOTAL: Final[str] = "aqi_errors_total"
METRIC_PREDICTION_VALUE: Final[str] = "aqi_prediction_value"
METRIC_MODEL_INFO: Final[str] = "aqi_model_info"

# ── Prediction buckets ───────────────────────────────────────────────────────
PREDICTION_BUCKETS: Final[tuple[float, ...]] = (0, 50, 100, 150, 200, 300, 400, 500)

# ── API defaults ─────────────────────────────────────────────────────────────
DEFAULT_API_HOST: Final[str] = "0.0.0.0"
DEFAULT_API_PORT: Final[int] = 8000

# ── Paths (relative to project root) ─────────────────────────────────────────
DATA_RAW_DIR: Final[str] = "data/raw"
DATA_PROCESSED_DIR: Final[str] = "data/processed"
DATA_SNAPSHOT_DIR: Final[str] = "data/snapshot"
REPORTS_DIR: Final[str] = "reports"
MODELS_DIR: Final[str] = "models"
METRICS_FILE: Final[str] = "metrics.json"

# Re-export feature columns from schema
from src.common.schema import FEATURE_COLUMNS
