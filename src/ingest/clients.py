# Owner: M1 — Data ingestion: live API clients
"""Clients for data.gov.in and OpenAQ APIs with retry/backoff and rate limiting."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.common.config import get_config

logger = logging.getLogger(__name__)

# ── City mapping for APIs ─────────────────────────────────────────────────────
DATA_GOV_CITY_MAP: dict[str, str] = {
    "ahmedabad": "Ahmedabad",
    "delhi": "Delhi",
    "mumbai": "Mumbai",
}

OPENAQ_CITY_MAP: dict[str, str] = {
    "ahmedabad": "Ahmedabad",
    "delhi": "Delhi",
    "mumbai": "Mumbai",
}


def _get_session(max_retries: int = 3, backoff_factor: float = 2.0) -> requests.Session:
    """Create a requests session with retry and backoff.

    Args:
        max_retries: Maximum number of retries.
        backoff_factor: Backoff multiplier between retries.

    Returns:
        Configured requests.Session.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 30) -> None:
        self.interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0

    def wait(self) -> None:
        """Block until the next request is allowed."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request_time = time.time()


def fetch_data_gov_in(city: str) -> pd.DataFrame:
    """Fetch AQI data from data.gov.in API.

    Args:
        city: One of the configured city names.

    Returns:
        DataFrame with raw AQI readings.
    """
    config = get_config()
    api_key = os.environ.get("DATA_GOV_IN_API_KEY", "")
    if not api_key:
        raise ValueError("DATA_GOV_IN_API_KEY environment variable not set")

    ingest_cfg = config["ingest"]
    session = _get_session(
        max_retries=ingest_cfg["max_retries"],
        backoff_factor=ingest_cfg["retry_backoff"],
    )
    rate_limiter = RateLimiter(ingest_cfg["rate_limit"])

    city_name = DATA_GOV_CITY_MAP.get(city, city)
    url = "https://api.data.gov.in/resource/real-time-air-quality-index"
    params: dict[str, Any] = {
        "api-key": api_key,
        "format": "json",
        "filters[city]": city_name,
        "limit": 1000,
    }

    rate_limiter.wait()
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    records = data.get("records", [])
    if not records:
        logger.warning("No records returned from data.gov.in for %s", city)
        return pd.DataFrame()

    df = pd.DataFrame(records)
    logger.info("Fetched %d records from data.gov.in for %s", len(df), city)
    return df


def fetch_openaq(city: str) -> pd.DataFrame:
    """Fetch AQI data from OpenAQ API.

    Args:
        city: One of the configured city names.

    Returns:
        DataFrame with raw AQI readings.
    """
    config = get_config()
    api_key = os.environ.get("OPENAQ_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAQ_API_KEY environment variable not set")

    ingest_cfg = config["ingest"]
    session = _get_session(
        max_retries=ingest_cfg["max_retries"],
        backoff_factor=ingest_cfg["retry_backoff"],
    )
    rate_limiter = RateLimiter(ingest_cfg["rate_limit"])

    city_name = OPENAQ_CITY_MAP.get(city, city)
    url = "https://api.openaq.org/v2/measurements"
    params: dict[str, Any] = {
        "city": city_name,
        "country": "IN",
        "limit": 5000,
        "order_by": "datetime",
        "sort": "desc",
    }
    headers = {"X-API-Key": api_key}

    rate_limiter.wait()
    response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])
    if not results:
        logger.warning("No results from OpenAQ for %s", city)
        return pd.DataFrame()

    df = pd.DataFrame(results)
    logger.info("Fetched %d records from OpenAQ for %s", len(df), city)
    return df


# ── Open-Meteo Real-Data Fetcher (No API Key Required) ───────────────────────
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "ahmedabad": (23.0225, 72.5714),
    "mumbai": (19.0760, 72.8777),
}


def calculate_cpcb_aqi(pm25: float, pm10: float) -> float:
    """Compute AQI using official Indian Central Pollution Control Board breakpoints.

    Args:
        pm25: Fine particulate matter in µg/m³.
        pm10: Respirable particulate matter in µg/m³.

    Returns:
        CPCB composite Air Quality Index [0, 500].
    """
    if pd.isna(pm25) or pm25 is None:
        pm25 = 50.0
    if pd.isna(pm10) or pm10 is None:
        pm10 = 100.0

    # PM2.5 sub-index calculation
    if pm25 <= 30:
        s25 = pm25 * 50 / 30
    elif pm25 <= 60:
        s25 = 50 + (pm25 - 30) * 50 / 30
    elif pm25 <= 90:
        s25 = 100 + (pm25 - 60) * 100 / 30
    elif pm25 <= 120:
        s25 = 200 + (pm25 - 90) * 100 / 30
    elif pm25 <= 250:
        s25 = 300 + (pm25 - 120) * 100 / 130
    else:
        s25 = 400 + (pm25 - 250) * 100 / 130

    # PM10 sub-index calculation
    if pm10 <= 50:
        s10 = pm10 * 50 / 50
    elif pm10 <= 100:
        s10 = 50 + (pm10 - 50) * 50 / 50
    elif pm10 <= 250:
        s10 = 100 + (pm10 - 100) * 100 / 150
    elif pm10 <= 350:
        s10 = 200 + (pm10 - 250) * 100 / 100
    elif pm10 <= 430:
        s10 = 300 + (pm10 - 350) * 100 / 80
    else:
        s10 = 400 + (pm10 - 430) * 100 / 80

    return float(max(5.0, min(500.0, max(s25, s10))))


def fetch_real_open_meteo(city: str, days: int = 30) -> pd.DataFrame:
    """Fetch real hourly air quality and weather telemetry from Open-Meteo.

    Args:
        city: City name ('delhi', 'ahmedabad', or 'mumbai').
        days: Number of past days of real historical data to fetch (max 92).

    Returns:
        DataFrame conforming to canonical RAW_COLUMNS.
    """
    city_key = city.lower().strip()
    if city_key not in CITY_COORDINATES:
        raise ValueError(
            f"Unsupported city '{city}'. Choose from: {list(CITY_COORDINATES.keys())}"
        )

    lat, lon = CITY_COORDINATES[city_key]
    past_days = max(1, min(int(days), 92))

    logger.info(
        "Fetching %d days of real data from Open-Meteo for %s (%f, %f)...",
        past_days,
        city_key.capitalize(),
        lat,
        lon,
    )

    session = _get_session()

    # 1. Fetch Air Quality
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "pm2_5",
            "pm10",
            "nitrogen_dioxide",
            "sulphur_dioxide",
            "carbon_monoxide",
            "ozone",
        ],
        "past_days": past_days,
    }
    aq_res = session.get(aq_url, params=aq_params, timeout=20)
    aq_res.raise_for_status()
    aq_data = aq_res.json().get("hourly", {})

    # 2. Fetch Surface Weather
    wx_url = "https://api.open-meteo.com/v1/forecast"
    wx_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "past_days": past_days,
    }
    wx_res = session.get(wx_url, params=wx_params, timeout=20)
    wx_res.raise_for_status()
    wx_data = wx_res.json().get("hourly", {})

    df_aq = pd.DataFrame(aq_data)
    df_wx = pd.DataFrame(wx_data)
    df = pd.merge(df_aq, df_wx, on="time")

    # Rename to canonical column names
    df = df.rename(
        columns={
            "time": "timestamp",
            "pm2_5": "pm25",
            "nitrogen_dioxide": "no2",
            "sulphur_dioxide": "so2",
            "carbon_monoxide": "co",
            "ozone": "o3",
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "wind_speed_10m": "wind_speed",
        }
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    # Filter to real recorded historical timestamps (drop future forecast placeholder NaNs)
    now_utc = pd.Timestamp.now(tz="UTC")
    df = df[df["timestamp"] <= now_utc].copy()
    df = df.dropna(subset=["pm25"]).copy()

    df["city"] = city_key
    # Open-Meteo CO is µg/m³; convert to standard mg/m³
    df["co"] = (df["co"] / 1000.0).round(2)
    df["humidity"] = df["humidity"].astype(float)
    df["aqi"] = [
        round(calculate_cpcb_aqi(row["pm25"], row["pm10"]), 1)
        for _, row in df.iterrows()
    ]

    # Clip physical boundaries to conform with Pandera RAW_SCHEMA bounds
    df["pm25"] = df["pm25"].clip(lower=0.0, upper=1000.0)
    df["pm10"] = df["pm10"].clip(lower=0.0, upper=1000.0)
    df["no2"] = df["no2"].clip(lower=0.0, upper=500.0)
    df["so2"] = df["so2"].clip(lower=0.0, upper=500.0)
    df["co"] = df["co"].clip(lower=0.0, upper=50.0)
    df["o3"] = df["o3"].clip(lower=0.0, upper=500.0)
    df["temperature"] = df["temperature"].clip(lower=-20.0, upper=60.0)
    df["humidity"] = df["humidity"].clip(lower=0.0, upper=100.0)
    df["wind_speed"] = df["wind_speed"].clip(lower=0.0, upper=50.0)
    df["aqi"] = df["aqi"].clip(lower=0.0, upper=500.0)

    # Fill any minor remaining nulls with ffill/bfill
    cols_to_fill = [
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
    df[cols_to_fill] = df[cols_to_fill].ffill().bfill()

    raw_cols = [
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
    df = df[raw_cols].reset_index(drop=True)
    logger.info("Successfully fetched %d real hourly records for %s", len(df), city_key)
    return df


def fetch_real_all(
    cities: list[str] | None = None,
    days: int = 30,
) -> pd.DataFrame:
    """Fetch real data for all configured cities and concatenate.

    Args:
        cities: Optional list of cities. Defaults to ['delhi', 'ahmedabad', 'mumbai'].
        days: Number of past days of real data per city.

    Returns:
        Concatenated DataFrame with real observations across cities.
    """
    cities = cities or ["delhi", "ahmedabad", "mumbai"]
    dfs = []
    for c in cities:
        try:
            dfs.append(fetch_real_open_meteo(c, days=days))
        except Exception:
            logger.exception("Failed to fetch real data for %s", c)

    if not dfs:
        raise RuntimeError("Failed to fetch real data for any city")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values(["city", "timestamp"]).reset_index(drop=True)
    logger.info("Total real records fetched across all cities: %d", len(combined))
    return combined
