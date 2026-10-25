# Owner: M2 — FastAPI serving: main application
"""FastAPI application for AQI forecasting.

Endpoints:
- POST /predict — 24h AQI forecast
- GET  /health  — Health check with model status
- GET  /metrics — Prometheus text format
- POST /admin/reload — Reload champion model
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response

from api.metrics import (
    ERRORS_COUNTER,
    LATENCY_HISTOGRAM,
    MODEL_INFO_GAUGE,
    PREDICTION_HISTOGRAM,
    REQUESTS_COUNTER,
    generate_metrics_text,
)
from api.model_loader import ModelLoader
from api.schemas import (
    AdminReloadResponse,
    ForecastItem,
    HealthResponse,
    PredictRequest,
    PredictResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App version from env ──────────────────────────────────────────────────────
APP_VERSION = os.environ.get("APP_VERSION", "1.1.0")

# ── Global model loader ──────────────────────────────────────────────────────
model_loader = ModelLoader()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    logger.info("Starting AQI Forecaster API v%s", APP_VERSION)
    model_loader.load()
    if model_loader.is_loaded:
        MODEL_INFO_GAUGE.labels(
            version=model_loader.model_version,
            alias=model_loader.model_alias,
        ).set(1)
    yield
    logger.info("Shutting down AQI Forecaster API")


app = FastAPI(
    title="AQI Forecaster API",
    version=APP_VERSION,
    description="24-hour AQI Forecasting for Indian cities",
    lifespan=lifespan,
)


# ── Middleware: metrics + version headers ─────────────────────────────────────
@app.middleware("http")
async def metrics_and_headers_middleware(request: Request, call_next) -> Response:
    """Track request metrics and add version headers."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Record latency
    duration = time.time() - start_time
    endpoint = request.url.path
    LATENCY_HISTOGRAM.labels(endpoint=endpoint).observe(duration)

    # Count request
    REQUESTS_COUNTER.labels(
        method=request.method,
        endpoint=endpoint,
        status=str(response.status_code),
    ).inc()

    # Count errors
    if response.status_code >= 400:
        ERRORS_COUNTER.labels(endpoint=endpoint).inc()

    # Add version headers
    response.headers["X-App-Version"] = APP_VERSION
    response.headers["X-Model-Version"] = model_loader.model_version or "none"

    return response


# ── POST /predict ─────────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    """Generate 24-hour AQI forecast.

    Args:
        request: Prediction request with city, readings, and optional history.

    Returns:
        24-hour forecast with model version info.
    """
    if not model_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service unavailable.",
        )

    try:
        forecasts = model_loader.predict(
            city=request.city,
            readings=request.readings.model_dump(),
            history=(
                [h.model_dump() for h in request.history] if request.history else None
            ),
        )

        # Record prediction values
        for f in forecasts:
            PREDICTION_HISTOGRAM.observe(f["aqi"])

        return PredictResponse(
            city=request.city,
            model_version=model_loader.model_version or "unknown",
            model_alias=model_loader.model_alias or "unknown",
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            forecast=[
                ForecastItem(horizon_h=f["horizon_h"], aqi=round(f["aqi"], 1))
                for f in forecasts
            ],
        )
    except Exception as exc:
        logger.exception("Prediction error")
        ERRORS_COUNTER.labels(endpoint="/predict").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── GET /health ───────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        model_loaded=model_loader.is_loaded,
        model_version=model_loader.model_version,
        app_version=APP_VERSION,
    )


# ── GET /metrics ──────────────────────────────────────────────────────────────
@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── POST /admin/reload ───────────────────────────────────────────────────────
@app.post("/admin/reload", response_model=AdminReloadResponse)
async def admin_reload() -> AdminReloadResponse:
    """Reload the champion model from registry."""
    old_version = model_loader.model_version
    model_loader.load()

    # Update gauge
    if model_loader.is_loaded:
        MODEL_INFO_GAUGE.labels(
            version=model_loader.model_version,
            alias=model_loader.model_alias,
        ).set(1)

    return AdminReloadResponse(
        status="reloaded",
        old_version=old_version,
        new_version=model_loader.model_version,
    )
