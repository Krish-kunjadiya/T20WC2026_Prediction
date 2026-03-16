"""Load CricSheet CSV files from data/raw/cricsheet into Bronze tables."""
import argparse
import csv
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


def load_cricsheet_metadata(
    cricket_dir: Path,
    max_matches: Optional[int] = None,
) -> None:
    """Load CricSheet _info.csv metadata into bronze.raw_matches/raw_squads/raw_venues."""
    info_candidates = sorted(cricket_dir.glob("*_info.csv"))
    if max_matches is not None and max_matches > 0:
        info_files = info_candidates[:max_matches]
    else:
        info_files = info_candidates

    match_rows = []
    squad_rows = []
    venue_rows = []

    for fpath in info_files:
        match_id = fpath.stem.replace("_info", "")
        meta: dict[str, str] = {}
        teams: list[str] = []
        players_seen: set[tuple[str, str]] = set()

        try:
            with fpath.open("r", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if not row:
                        continue
                    if row[0] != "info":
                        continue
                    if len(row) < 3:
                        continue

                    key = row[1]
                    value = row[2]

                    if key == "team":
                        teams.append(value)
                    elif key == "player" and len(row) >= 4:
                        team_name = value
                        player_name = row[3]
                        pair = (team_name, player_name)
                        if pair not in players_seen:
                            players_seen.add(pair)
                            squad_rows.append(
                                {
                                    "team": team_name,
                                    "player_name": player_name,
                                    "role": "Unknown",
                                    "designation": "Playing XI",
                                }
                            )
                    else:
                        # keep first value for duplicate keys like umpire
                        meta.setdefault(key, value)

            team1 = teams[0] if len(teams) > 0 else "Unknown"
            team2 = teams[1] if len(teams) > 1 else "Unknown"

            winner = meta.get("winner", "")
            winner_runs = meta.get("winner_runs", "")
            winner_wickets = meta.get("winner_wickets", "")

            if winner_runs:
                margin = f"{winner_runs} runs"
            elif winner_wickets:
                margin = f"{winner_wickets} wickets"
            else:
                margin = "No Result"

            date_raw = meta.get("date", "")
            match_date = date_raw.replace("/", "-") if date_raw else ""

            match_rows.append(
                {
                    "match_no": match_id,
                    "stage": "Group Stage",
                    "group": "",
                    "date": match_date,
                    "venue": meta.get("venue", "Unknown Venue"),
                    "city": meta.get("city", ""),
                    "team1": team1,
                    "team2": team2,
                    "toss_winner": meta.get("toss_winner", ""),
                    "toss_decision": meta.get("toss_decision", "bat"),
                    "winner": winner,
                    "result": "normal" if winner else "no result",
                    "margin": margin,
                }
            )

            venue_rows.append(
                {
                    "venue_name": meta.get("venue", "Unknown Venue"),
                    "city": meta.get("city", ""),
                    "country": "Unknown",
                    "capacity": "",
                    "stages_hosted": "",
                }
            )
        except Exception as exc:
            print(f"  ❌ {fpath.name}: {exc}")

    if match_rows:
        pd.DataFrame(match_rows).drop_duplicates(subset=["match_no"]).to_sql(
            "raw_matches", engine, schema="bronze", if_exists="append", index=False
        )
    if squad_rows:
        pd.DataFrame(squad_rows).drop_duplicates(subset=["team", "player_name"]).to_sql(
            "raw_squads", engine, schema="bronze", if_exists="append", index=False
        )
    if venue_rows:
        pd.DataFrame(venue_rows).drop_duplicates(subset=["venue_name", "city"]).to_sql(
            "raw_venues", engine, schema="bronze", if_exists="append", index=False
        )

    print(
        f"  ✅ {len(match_rows):>5} match metadata rows -> bronze.raw_matches"
    )
    print(
        f"  ✅ {len(squad_rows):>5} squad metadata rows -> bronze.raw_squads"
    )
    print(
        f"  ✅ {len(venue_rows):>5} venue metadata rows -> bronze.raw_venues"
    )


# ── main loader ───────────────────────────────────────────────────────────────

def load_all(max_matches: Optional[int] = None) -> None:
    """Orchestrate loading of CricSheet data into the bronze schema."""
    base = Path(__file__).resolve().parents[2] / "data" / "raw"
    cricket = base / "cricsheet"

    print("\n🔄  BRONZE LAYER — Ingestion starting …\n")

    # ── cricsheet metadata (_info.csv) ─────────────────────────────────────
    print("── CricSheet metadata (_info.csv) ──")
    load_cricsheet_metadata(cricket, max_matches=max_matches)

    # ── cricsheet ball-by-ball (full set by default; optional sample via CLI)
    delivery_candidates = sorted([f for f in cricket.glob("*.csv") if "_info" not in f.name])
    if max_matches is not None and max_matches > 0:
        delivery_files = delivery_candidates[:max_matches]
        print(f"\n── Cricsheet ball-by-ball (sample: first {len(delivery_files)} matches) ──")
    else:
        delivery_files = delivery_candidates
        print(f"\n── Cricsheet ball-by-ball (full load: {len(delivery_files)} matches) ──")

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
    parser = argparse.ArgumentParser(description="Load raw cricket data into bronze layer tables.")
    parser.add_argument(
        "--max-matches",
        type=int,
        default=0,
        help="Optional cap on CricSheet match files to ingest (0 = all files).",
    )
    args = parser.parse_args()
    load_all(max_matches=args.max_matches if args.max_matches > 0 else None)
