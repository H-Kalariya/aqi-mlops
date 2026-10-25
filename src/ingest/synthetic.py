# Owner: M1 — Data ingestion: synthetic data generator
"""Realistic synthetic hourly AQI data generator.

Generates ~12 months of hourly data per city with:
- Winter smog seasonality (Nov-Feb elevated AQI)
- Diwali spike (late October / early November)
- Monsoon dip (Jul-Sep lower AQI)
- Daily cycles (morning/evening rush hour peaks)
- City-specific base levels
- Correlated pollutant and weather features
- Gaussian noise for realism
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.common.config import get_config

logger = logging.getLogger(__name__)

# ── City-specific base profiles ───────────────────────────────────────────────
CITY_PROFILES: dict[str, dict[str, float]] = {
    "ahmedabad": {
        "base_aqi": 120,
        "base_pm25": 55,
        "base_pm10": 100,
        "base_no2": 25,
        "base_so2": 8,
        "base_co": 1.0,
        "base_o3": 35,
        "base_temp": 30,
        "base_humidity": 45,
        "base_wind": 3.5,
    },
    "delhi": {
        "base_aqi": 180,
        "base_pm25": 90,
        "base_pm10": 160,
        "base_no2": 40,
        "base_so2": 12,
        "base_co": 1.5,
        "base_o3": 45,
        "base_temp": 28,
        "base_humidity": 50,
        "base_wind": 2.5,
    },
    "mumbai": {
        "base_aqi": 100,
        "base_pm25": 45,
        "base_pm10": 85,
        "base_no2": 20,
        "base_so2": 6,
        "base_co": 0.8,
        "base_o3": 30,
        "base_temp": 29,
        "base_humidity": 70,
        "base_wind": 4.0,
    },
}


def _seasonal_factor(month: int) -> float:
    """Return a seasonal multiplier for AQI (winter = high, monsoon = low).

    Args:
        month: Calendar month (1-12).

    Returns:
        Multiplier in [0.5, 1.8] range.
    """
    # Winter peak (Nov=11, Dec=12, Jan=1, Feb=2)
    if month in (11, 12, 1, 2):
        return 1.5 + 0.3 * (1 if month in (12, 1) else 0)
    # Monsoon dip (Jul-Sep)
    if month in (7, 8, 9):
        return 0.55
    # Transition months
    if month in (3, 4):
        return 0.9
    if month in (5, 6):
        return 0.75
    # Oct
    return 1.1


def _daily_cycle(hour: int) -> float:
    """Return a daily cycle multiplier (rush hour peaks).

    Args:
        hour: Hour of day (0-23).

    Returns:
        Multiplier in [0.7, 1.3] range.
    """
    if hour in (7, 8, 9):
        return 1.25
    if hour in (17, 18, 19, 20):
        return 1.3
    if hour in (2, 3, 4):
        return 0.7
    return 1.0


def _diwali_spike(timestamp: pd.Timestamp) -> float:
    """Add a Diwali spike in late October / early November.

    Args:
        timestamp: The specific timestamp.

    Returns:
        Additive spike value (0 normally, large during Diwali).
    """
    month, day = timestamp.month, timestamp.day
    # Diwali window: Oct 28 - Nov 3 (approximate)
    if (month == 10 and day >= 28) or (month == 11 and day <= 3):
        # Peak on Nov 1
        peak_day = 1 if month == 11 else day - 28 + 4
        distance = abs(peak_day - 4)
        return max(0, 150 - distance * 30)
    return 0.0


def generate_synthetic_city(
    city: str,
    months: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic synthetic hourly AQI data for a single city.

    Args:
        city: City name (must be in CITY_PROFILES).
        months: Number of months of data to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns matching RAW_COLUMNS from schema.
    """
    rng = np.random.default_rng(seed + hash(city) % 10000)
    profile = CITY_PROFILES.get(city, CITY_PROFILES["delhi"])

    # Generate hourly timestamps
    end = pd.Timestamp("2024-12-31 23:00:00", tz="UTC")
    start = end - pd.DateOffset(months=months)
    timestamps = pd.date_range(start=start, end=end, freq="h")
    n = len(timestamps)

    records: list[dict] = []
    for i, ts in enumerate(timestamps):
        seasonal = _seasonal_factor(ts.month)
        daily = _daily_cycle(ts.hour)
        diwali = _diwali_spike(ts)

        # Temperature: seasonal + daily
        temp_seasonal = 5 * np.sin(2 * np.pi * (ts.month - 6) / 12)
        temp_daily = 4 * np.sin(2 * np.pi * (ts.hour - 14) / 24)
        temperature = np.clip(
            profile["base_temp"] + temp_seasonal + temp_daily + rng.normal(0, 1.5),
            -5,
            50,
        )

        # Humidity: inverse of temperature + monsoon boost
        monsoon_boost = 25 if ts.month in (7, 8, 9) else 0
        humidity = np.clip(
            profile["base_humidity"]
            + monsoon_boost
            - 0.5 * (temperature - profile["base_temp"])
            + rng.normal(0, 5),
            5,
            99,
        )

        # Wind speed
        wind_speed = np.clip(
            profile["base_wind"] + rng.normal(0, 1.0),
            0.1,
            25,
        )

        # AQI with all factors
        aqi = np.clip(
            profile["base_aqi"] * seasonal * daily
            + diwali
            + rng.normal(0, 15),
            5,
            500,
        )

        # Pollutants correlated with AQI
        aqi_ratio = aqi / profile["base_aqi"]
        pm25 = np.clip(profile["base_pm25"] * aqi_ratio + rng.normal(0, 8), 1, 999)
        pm10 = np.clip(profile["base_pm10"] * aqi_ratio + rng.normal(0, 12), 1, 999)
        no2 = np.clip(profile["base_no2"] * aqi_ratio + rng.normal(0, 5), 0.1, 400)
        so2 = np.clip(profile["base_so2"] * aqi_ratio + rng.normal(0, 2), 0.1, 150)
        co = np.clip(profile["base_co"] * aqi_ratio + rng.normal(0, 0.3), 0.05, 40)
        o3 = np.clip(
            profile["base_o3"] * (1.5 - 0.5 * aqi_ratio) + rng.normal(0, 5),
            0.1,
            400,
        )

        records.append(
            {
                "timestamp": ts,
                "city": city,
                "pm25": round(float(pm25), 1),
                "pm10": round(float(pm10), 1),
                "no2": round(float(no2), 1),
                "so2": round(float(so2), 1),
                "co": round(float(co), 2),
                "o3": round(float(o3), 1),
                "temperature": round(float(temperature), 1),
                "humidity": round(float(humidity), 1),
                "wind_speed": round(float(wind_speed), 1),
                "aqi": round(float(aqi), 1),
            }
        )

    df = pd.DataFrame(records)
    logger.info("Generated %d synthetic hourly records for %s", len(df), city)
    return df


def generate_synthetic_all(
    cities: list[str] | None = None,
    months: int | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic data for all configured cities.

    Args:
        cities: List of city names. Defaults to config.
        months: Number of months. Defaults to config.
        seed: Random seed.

    Returns:
        Combined DataFrame for all cities.
    """
    config = get_config()
    if cities is None:
        cities = config["cities"]
    if months is None:
        months = config["ingest"]["synthetic_months"]

    dfs = [generate_synthetic_city(city, months=months, seed=seed) for city in cities]
    combined = pd.concat(dfs, ignore_index=True)
    combined.sort_values(["timestamp", "city"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    logger.info("Total synthetic records: %d", len(combined))
    return combined


def generate_synthetic_data(
    cities: list[str] | None = None,
    days: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Convenience generator that produces exactly `days` worth of hourly data.

    Args:
        cities: Optional list of cities. Defaults to all configured cities.
        days: Number of days of hourly data to generate.
        seed: Random seed.

    Returns:
        DataFrame containing synthetic data.
    """
    months = max(1, int(np.ceil(days / 30.0)))
    df = generate_synthetic_all(cities=cities, months=months, seed=seed)
    # Truncate to the specified number of days
    min_ts = df["timestamp"].min()
    max_ts = min_ts + pd.Timedelta(days=days)
    truncated = df[df["timestamp"] < max_ts].copy()
    truncated.reset_index(drop=True, inplace=True)
    return truncated

