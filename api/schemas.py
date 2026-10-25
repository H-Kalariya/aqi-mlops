# Owner: M2 — FastAPI serving: Pydantic schemas
"""Request/response models for the AQI Forecaster API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Readings(BaseModel):
    """Current pollutant and weather readings."""

    pm25: float = Field(..., ge=0, le=1000, description="PM2.5 concentration")
    pm10: float = Field(..., ge=0, le=1000, description="PM10 concentration")
    no2: float = Field(..., ge=0, le=500, description="NO2 concentration")
    so2: float = Field(..., ge=0, le=200, description="SO2 concentration")
    co: float = Field(..., ge=0, le=50, description="CO concentration")
    o3: float = Field(..., ge=0, le=500, description="O3 concentration")
    temperature: float = Field(..., ge=-10, le=55, description="Temperature (°C)")
    humidity: float = Field(..., ge=0, le=100, description="Humidity (%)")
    wind_speed: float = Field(..., ge=0, le=50, description="Wind speed (m/s)")


class HistoryRecord(BaseModel):
    """One hourly historical record for lag computation."""

    pm25: float = 0.0
    pm10: float = 0.0
    no2: float = 0.0
    so2: float = 0.0
    co: float = 0.0
    o3: float = 0.0
    temperature: float = 0.0
    humidity: float = 0.0
    wind_speed: float = 0.0
    aqi: float = 0.0


class PredictRequest(BaseModel):
    """Prediction request body."""

    city: str = Field(
        ...,
        description="City name (ahmedabad, delhi, mumbai)",
        examples=["ahmedabad"],
    )
    readings: Readings
    history: list[HistoryRecord] | None = Field(
        default=None,
        description="Optional last 24 hourly records for lag features",
    )


class ForecastItem(BaseModel):
    """Single horizon forecast."""

    horizon_h: int = Field(..., ge=1, le=24, description="Hours ahead")
    aqi: float = Field(..., description="Predicted AQI")


class PredictResponse(BaseModel):
    """Prediction response body."""

    city: str
    model_version: str
    model_alias: str
    generated_at: str
    forecast: list[ForecastItem]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    model_version: str | None
    app_version: str


class AdminReloadResponse(BaseModel):
    """Admin reload response."""

    status: str
    old_version: str | None
    new_version: str | None
