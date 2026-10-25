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


def run_ingest(source: str | None = None, city: str | None = None) -> pd.DataFrame:
    """Run the ingestion pipeline.

    Args:
        source: Override for ingest source (live|snapshot|synthetic).
        city: Optional single city to ingest.

    Returns:
        Ingested DataFrame.
    """
    config = get_config()
    source = source or config["ingest"]["source"]
    raw_dir = PROJECT_ROOT / config["paths"]["raw"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Ingestion source: %s", source)

    if source == "synthetic":
        from src.ingest.synthetic import generate_synthetic_all

        df = generate_synthetic_all()
    elif source == "snapshot":
        from src.ingest.snapshot import load_snapshot

        df = load_snapshot(city=city)
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
            logger.error("No live data fetched. Falling back to synthetic.")
            from src.ingest.synthetic import generate_synthetic_all

            df = generate_synthetic_all()
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
        choices=["live", "snapshot", "synthetic"],
        default=None,
        help="Data source (overrides config.yaml)",
    )
    parser.add_argument("--city", default=None, help="Single city to ingest")
    args = parser.parse_args()

    try:
        run_ingest(source=args.source, city=args.city)
    except Exception:
        logger.exception("Ingestion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
