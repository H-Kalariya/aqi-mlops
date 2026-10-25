# Owner: M1 — Data ingestion: run module
"""Entrypoint for data ingestion. Selects source based on config.yaml.

Usage:
    python -m src.ingest.run [--source synthetic|snapshot|live] [--city delhi]
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from src.common.config import PROJECT_ROOT, get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingest(
    source: str | None = None,
    city: str | None = None,
    days: int | None = None,
) -> pd.DataFrame:
    """Run the ingestion pipeline.

    Args:
        source: Override for ingest source (live|snapshot|synthetic).
        city: Optional single city to ingest.
        days: Optional number of days of synthetic data to generate.

    Returns:
        Ingested DataFrame.
    """
    config = get_config()
    source = source or config["ingest"]["source"]
    raw_dir = PROJECT_ROOT / config["paths"]["raw"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Ingestion source: %s", source)

    if source == "synthetic":
        if days:
            from src.ingest.synthetic import generate_synthetic_data

            df = generate_synthetic_data(days=days)
        else:
            from src.ingest.synthetic import generate_synthetic_all

            df = generate_synthetic_all()

    elif source == "snapshot":
        from src.ingest.snapshot import load_snapshot

        df = load_snapshot(city=city)
    elif source in ("real", "open-meteo"):
        from src.ingest.clients import fetch_real_all, fetch_real_open_meteo

        past_days = days or 30
        if city:
            df = fetch_real_open_meteo(city=city, days=past_days)
        else:
            cities = config.get("cities", ["delhi", "ahmedabad", "mumbai"])
            df = fetch_real_all(cities=cities, days=past_days)

    elif source == "live":
        from src.ingest.clients import fetch_data_gov_in

        cities = [city] if city else config["cities"]
        dfs = []
        for c in cities:
            try:
                dfs.append(fetch_data_gov_in(c))
            except Exception:
                logger.exception("Failed to fetch live data for %s", c)
        if not dfs:
            logger.warning(
                "No data.gov.in data fetched. Falling back to real Open-Meteo stream."
            )
            from src.ingest.clients import fetch_real_all

            df = fetch_real_all(cities=cities, days=days or 30)
        else:
            df = pd.concat(dfs, ignore_index=True)
    else:
        raise ValueError(f"Unknown ingest source: {source}")

    # Save raw data
    output_path = raw_dir / "aqi_raw.csv"
    df.to_csv(output_path, index=False)
    logger.info("Saved raw data to %s (%d rows)", output_path, len(df))
    return df


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="AQI Data Ingestion")
    parser.add_argument(
        "--source",
        choices=["live", "real", "open-meteo", "snapshot", "synthetic"],
        default=None,
        help="Data source (overrides config.yaml)",
    )
    parser.add_argument("--city", default=None, help="Single city to ingest")
    parser.add_argument(
        "--days", type=int, default=None, help="Days of data to fetch/generate"
    )
    args = parser.parse_args()

    try:
        run_ingest(source=args.source, city=args.city, days=args.days)

    except Exception:
        logger.exception("Ingestion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
