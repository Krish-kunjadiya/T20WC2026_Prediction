"""
Load all raw CSV files from data/raw/ into the Bronze layer tables.
Handles: kaggle CSVs (matches, batting, bowling, squads, venues, scorecards)
         + a sampled subset of cricsheet ball-by-ball CSVs.
Every load is idempotent when run after a schema TRUNCATE.
"""
import glob
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

_u = os.getenv("POSTGRES_USER")
_p = os.getenv("POSTGRES_PASSWORD")
_h = os.getenv("POSTGRES_HOST")
_port = os.getenv("POSTGRES_PORT")
_db = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{_u}:{_p}@{_h}:{_port}/{_db}"
engine = create_engine(DATABASE_URL)

# ── helpers ───────────────────────────────────────────────────────────────────

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, and replace spaces with underscores in column names."""
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df


def load_csv(
    filepath: str,
    table: str,
    schema: str = "bronze",
    rename: Optional[dict] = None,
    keep_cols: Optional[list] = None,
) -> int:
    """
    Read a CSV file and append its rows to a bronze table.

    Args:
        filepath: Absolute or relative path to the CSV.
        table:    Target table name (without schema prefix).
        schema:   Target PostgreSQL schema (default: bronze).
        rename:   Optional column rename mapping applied after normalisation.
        keep_cols: If set, only these columns are written to the DB.

    Returns:
        Number of rows inserted, or -1 on failure.
    """
    try:
        df = pd.read_csv(filepath, dtype=str, encoding="utf-8", on_bad_lines="skip")
        df = _normalise_columns(df)
        if rename:
            df = df.rename(columns=rename)
        if keep_cols:
            df = df[[c for c in keep_cols if c in df.columns]]
        # Drop fully-empty rows
        df = df.dropna(how="all")
        df.to_sql(table, engine, schema=schema, if_exists="append", index=False)
        print(f"  ✅ {len(df):>5} rows → {schema}.{table}  ({Path(filepath).name})")
        return len(df)
    except Exception as exc:
        print(f"  ❌ FAILED {schema}.{table}: {exc}")
        return -1


# ── main loader ───────────────────────────────────────────────────────────────

def load_all() -> None:
    """Orchestrate loading of all sources into the bronze schema."""
    base = Path(__file__).resolve().parents[2] / "data" / "raw"
    kaggle = base / "kaggle"
    cricket = base / "cricsheet"

    print("\n🔄  BRONZE LAYER — Ingestion starting …\n")

    # ── kaggle / curated CSVs ─────────────────────────────────────────────
    print("── Kaggle / organiser CSVs ──")

    load_csv(
        str(kaggle / "matches.csv"),
        "raw_matches",
        rename={"match_no": "match_no"},   # already correct; keep for clarity
    )

    load_csv(str(kaggle / "batting_stats.csv"), "raw_batting_stats")
    load_csv(str(kaggle / "bowling_stats.csv"), "raw_bowling_stats")
    load_csv(str(kaggle / "squads.csv"), "raw_squads")
    load_csv(str(kaggle / "venues.csv"), "raw_venues")
    load_csv(str(kaggle / "key_scorecards.csv"), "raw_key_scorecards")

    # ── cricsheet ball-by-ball (first 200 match files as representative sample)
    print("\n── Cricsheet ball-by-ball (sample: first 200 matches) ──")
    delivery_files = sorted(
        [f for f in cricket.glob("*.csv") if "_info" not in f.name]
    )[:200]

    total_deliveries = 0
    for fpath in delivery_files:
        match_id = fpath.stem
        try:
            df = pd.read_csv(fpath, dtype=str, encoding="utf-8", on_bad_lines="skip")
            df = _normalise_columns(df)
            df["match_id"] = match_id
            # Ensure _ingested_at is handled by DB default; don't set here
            df.to_sql("raw_deliveries", engine, schema="bronze",
                      if_exists="append", index=False)
            total_deliveries += len(df)
        except Exception as exc:
            print(f"  ❌ {fpath.name}: {exc}")

    print(f"  ✅ {total_deliveries:>6} delivery rows → bronze.raw_deliveries "
          f"(from {len(delivery_files)} match files)")

    print("\n✅  Bronze ingestion complete.\n")


if __name__ == "__main__":
    load_all()
