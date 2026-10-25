# Owner: M2 — FastAPI serving: Prometheus metrics
"""Fixed Prometheus metrics for the AQI Forecaster API.

Metric names match the contract in §3 of the spec.
"""

from __future__ import annotations

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from src.common.constants import PREDICTION_BUCKETS

# ── Counters ──────────────────────────────────────────────────────────────────
REQUESTS_COUNTER = Counter(
    "aqi_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

ERRORS_COUNTER = Counter(
    "aqi_errors_total",
    "Total errors",
    ["endpoint"],
)

# ── Histograms ────────────────────────────────────────────────────────────────
LATENCY_HISTOGRAM = Histogram(
    "aqi_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
)

PREDICTION_HISTOGRAM = Histogram(
    "aqi_prediction_value",
    "Predicted AQI values",
    buckets=PREDICTION_BUCKETS,
)

# ── Gauges ────────────────────────────────────────────────────────────────────
MODEL_INFO_GAUGE = Gauge(
    "aqi_model_info",
    "Currently loaded model info",
    ["version", "alias"],
)


def generate_metrics_text() -> str:
    """Generate Prometheus-compatible text format metrics.

    Returns:
        Metrics in Prometheus text exposition format.
    """
    return generate_latest().decode("utf-8")
