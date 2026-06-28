"""Load generated CSV files into PostgreSQL raw tables."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "synthetic" / "sample_data"


def database_url() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL before loading data.")
    return url


def load_csvs(data_dir: Path) -> None:
    engine = create_engine(database_url())
    table_files = {
        "facilities": data_dir / "facilities.csv",
        "services": data_dir / "services.csv",
        "units": data_dir / "units.csv",
        "diagnoses": data_dir / "diagnoses.csv",
        "population_growth": data_dir / "population_growth.csv",
        "capacity": data_dir / "capacity.csv",
        "visits": data_dir / "visits.csv",
        "unit_changes": data_dir / "unit_changes.csv",
    }

    with engine.begin() as connection:
        connection.execute(text("create schema if not exists raw"))
        for table_name, path in table_files.items():
            if not path.exists():
                raise FileNotFoundError(f"Missing generated input: {path}")
            frame = pd.read_csv(path)
            frame.to_sql(
                table_name,
                connection,
                schema="raw",
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=1_000,
            )
            print(f"Loaded raw.{table_name}: {len(frame):,} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    load_csvs(args.data_dir)


if __name__ == "__main__":
    main()
