"""Load Cricsheet data into Bronze layer tables.

This loader is Cricsheet-only and reads:
- ball-by-ball files: <match_id>.csv
- metadata files: <match_id>_info.csv
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

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


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, and replace spaces with underscores in column names."""
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df


def _safe_str(value: str | None) -> str:
    """Return a trimmed non-null string."""
    if value is None:
        return ""
    return str(value).strip()


def _normalize_gender(value: str | None) -> str:
    """Normalize gender labels to male/female/unknown."""
    raw = _safe_str(value).lower()
    if raw in {"male", "men", "man", "m", "boys"}:
        return "male"
    if raw in {"female", "women", "woman", "f", "girls"}:
        return "female"
    return "unknown"


def _parse_info_file(info_path: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Parse Cricsheet info CSV into match metadata and player tuples."""
    meta: dict[str, str] = {}
    teams: list[str] = []
    players: list[tuple[str, str]] = []

    with info_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 3 or row[0] != "info":
                continue

            key = _safe_str(row[1]).lower()
            if key == "team":
                teams.append(_safe_str(row[2]))
            elif key == "player" and len(row) >= 4:
                players.append((_safe_str(row[2]), _safe_str(row[3])))
            elif key in {
                "date",
                "event",
                "gender",
                "venue",
                "city",
                "toss_winner",
                "toss_decision",
                "winner",
                "winner_runs",
                "winner_wickets",
            }:
                meta[key] = _safe_str(row[2])

    meta["team1"] = teams[0] if len(teams) > 0 else ""
    meta["team2"] = teams[1] if len(teams) > 1 else ""
    return meta, players


def _build_match_row(match_id: str, meta: dict[str, str]) -> dict[str, str]:
    """Build one bronze.raw_matches-compatible row from parsed Cricsheet metadata."""
    margin = ""
    if _safe_str(meta.get("winner_runs")):
        margin = f"{meta['winner_runs']} runs"
    elif _safe_str(meta.get("winner_wickets")):
        margin = f"{meta['winner_wickets']} wkts"

    winner = _safe_str(meta.get("winner"))
    return {
        "match_no": match_id[:20],
        "stage": _safe_str(meta.get("event"))[:30],
        "group": "",
        "date": _safe_str(meta.get("date"))[:20],
        "venue": _safe_str(meta.get("venue"))[:120],
        "city": _safe_str(meta.get("city"))[:60],
        "team1": _safe_str(meta.get("team1"))[:60],
        "team2": _safe_str(meta.get("team2"))[:60],
        "gender": _normalize_gender(meta.get("gender"))[:10],
        "toss_winner": _safe_str(meta.get("toss_winner"))[:60],
        "toss_decision": _safe_str(meta.get("toss_decision"))[:10],
        "winner": winner[:60],
        "result": "completed" if winner else "no result",
        "margin": margin[:30],
    }


def _build_venue_row(meta: dict[str, str]) -> dict[str, str]:
    """Build one bronze.raw_venues-compatible row from parsed Cricsheet metadata."""
    return {
        "venue_name": (_safe_str(meta.get("venue")) or "Unknown Venue")[:120],
        "city": (_safe_str(meta.get("city")) or "Unknown")[:60],
        "country": "Unknown",
        "capacity": "",
        "stages_hosted": _safe_str(meta.get("event"))[:200],
    }


def load_all() -> None:
    """Orchestrate Cricsheet-only loading into bronze schema."""
    base = Path(__file__).resolve().parents[2] / "data" / "raw"
    cricsheet = base / "cricsheet"

    print("\n🔄  BRONZE LAYER — Cricsheet ingestion starting …\n")

    if not cricsheet.exists():
        raise FileNotFoundError(f"Cricsheet folder not found: {cricsheet}")

    delivery_files = sorted(
        [f for f in cricsheet.glob("*.csv") if not f.name.endswith("_info.csv")]
    )

    max_matches = int(os.getenv("CRICSHEET_MAX_MATCHES", "0") or "0")
    if max_matches > 0:
        delivery_files = delivery_files[:max_matches]
        print(f"Using first {max_matches} matches due to CRICSHEET_MAX_MATCHES")

    print(f"Found {len(delivery_files)} match files")

    total_deliveries = 0
    match_rows: list[dict[str, str]] = []
    venue_rows: list[dict[str, str]] = []
    squad_rows: list[dict[str, str]] = []

    for fpath in delivery_files:
        match_id = fpath.stem
        info_path = cricsheet / f"{match_id}_info.csv"
        meta: dict[str, str] = {}
        players: list[tuple[str, str]] = []

        if info_path.exists():
            try:
                meta, players = _parse_info_file(info_path)
                match_rows.append(_build_match_row(match_id, meta))
                venue_rows.append(_build_venue_row(meta))
            except Exception as exc:
                print(f"  ❌ info failed for {info_path.name}: {exc}")

        match_gender = _normalize_gender(meta.get("gender"))

        try:
            deliveries = pd.read_csv(fpath, dtype=str, encoding="utf-8", on_bad_lines="skip")
            deliveries = _normalise_columns(deliveries)
            deliveries["match_id"] = match_id
            deliveries["match_gender"] = match_gender
            deliveries.to_sql(
                "raw_deliveries",
                engine,
                schema="bronze",
                if_exists="append",
                index=False,
            )
            total_deliveries += len(deliveries)
        except Exception as exc:
            print(f"  ❌ deliveries failed for {fpath.name}: {exc}")
            continue

        for team, player_name in players:
            squad_rows.append(
                {
                    "team": team,
                    "player_name": player_name,
                    "gender": match_gender,
                    "role": "Unknown",
                    "designation": "XI",
                }
            )

    if match_rows:
        matches_df = pd.DataFrame(match_rows).drop_duplicates(subset=["match_no"])
        matches_df.to_sql("raw_matches", engine, schema="bronze", if_exists="append", index=False)

    if venue_rows:
        venues_df = pd.DataFrame(venue_rows).drop_duplicates(subset=["venue_name", "city"])
        venues_df.to_sql("raw_venues", engine, schema="bronze", if_exists="append", index=False)

    if squad_rows:
        squads_df = pd.DataFrame(squad_rows).drop_duplicates(subset=["team", "player_name", "gender"])
        squads_df.to_sql("raw_squads", engine, schema="bronze", if_exists="append", index=False)

    print(f"\n  ✅ {total_deliveries:>8} delivery rows -> bronze.raw_deliveries")
    print(f"  ✅ {len(match_rows):>8} match rows -> bronze.raw_matches")
    print(f"  ✅ {len(venue_rows):>8} venue rows -> bronze.raw_venues")
    print(f"  ✅ {len(squad_rows):>8} squad rows -> bronze.raw_squads")
    print("\n✅  Bronze ingestion complete (Cricsheet-only).\n")


if __name__ == "__main__":
    load_all()
