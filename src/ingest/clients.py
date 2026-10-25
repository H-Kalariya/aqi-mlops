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
