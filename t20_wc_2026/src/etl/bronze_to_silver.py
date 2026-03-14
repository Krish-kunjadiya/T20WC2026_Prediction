"""ETL: Bronze to Silver layer.

This pipeline performs:
- type casting and conversion
- missing value handling
- duplicate removal
- outlier flag reporting (IQR based, non-destructive)
- normalized output into silver tables
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def safe_float(val: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        return float(str(val).replace("%", "").strip())
    except Exception:
        return default


def safe_int(val: Any, default: int = 0) -> int:
    """Convert value to int safely."""
    try:
        return int(float(str(val).strip()))
    except Exception:
        return default


def remove_outliers_iqr(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Report outlier count using IQR method without dropping rows."""
    if col not in df.columns or df.empty:
        return df
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    flagged = int(((df[col] < lower) | (df[col] > upper)).sum())
    print(f"    Outliers in '{col}': {flagged} rows flagged (kept)")
    return df


def transform_matches() -> None:
    """Transform bronze.raw_matches into silver.clean_matches."""
    print("\nTransforming: bronze.raw_matches -> silver.clean_matches")
    df = pd.read_sql("SELECT * FROM bronze.raw_matches", engine)
    print(f"  Loaded {len(df)} rows")

    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed: {before - len(df)}")

    if "date" in df.columns:
        df["match_date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["match_date"] = pd.NaT

    # Margin in this dataset is text like "3 wkts (3b rem)".
    margin_series = df.get("margin", pd.Series(["0"] * len(df), index=df.index)).fillna("0")
    df["win_by_runs"] = margin_series.apply(
        lambda x: safe_int(str(x).split()[0]) if "run" in str(x).lower() else 0
    )
    df["win_by_wickets"] = margin_series.apply(
        lambda x: safe_int(str(x).split()[0]) if "wkt" in str(x).lower() else 0
    )

    df["winner"] = df.get("winner", pd.Series(index=df.index)).fillna("No Result")
    df["player_of_match"] = "Unknown"
    df["toss_decision"] = df.get("toss_decision", pd.Series(index=df.index)).fillna("bat")

    # Map stage/group to a normalized tournament phase.
    stage_raw = df.get("stage", pd.Series([""] * len(df), index=df.index)).astype(str)
    group_raw = df.get("group", pd.Series([""] * len(df), index=df.index)).astype(str)

    def phase(row: pd.Series) -> str:
        s = str(row["_stage"]).lower()
        g = str(row["_group"]).lower()
        if "final" in s and "semi" not in s:
            return "Final"
        if "semi" in s:
            return "Semi Final"
        if "super" in s:
            return "Super 8"
        if "group" in s or g:
            return "Group Stage"
        return "Group Stage"

    phase_df = pd.DataFrame({"_stage": stage_raw, "_group": group_raw})
    df["tournament_phase"] = phase_df.apply(phase, axis=1)

    df["is_day_night"] = False
    df["match_id"] = ["M" + str(i + 1).zfill(4) for i in range(len(df))]

    keep = [
        "match_id",
        "match_date",
        "venue",
        "city",
        "team1",
        "team2",
        "toss_winner",
        "toss_decision",
        "winner",
        "win_by_runs",
        "win_by_wickets",
        "player_of_match",
        "is_day_night",
        "tournament_phase",
    ]
    df_clean = df[[c for c in keep if c in df.columns]].copy()

    null_pct = (df_clean.isnull().sum() / max(len(df_clean), 1) * 100).round(2)
    non_zero_nulls = null_pct[null_pct > 0]
    print("  Null % after cleaning:")
    print(non_zero_nulls.to_string() if not non_zero_nulls.empty else "    None")

    df_clean.to_sql("clean_matches", engine, schema="silver", if_exists="replace", index=False)
    print(f"  Written {len(df_clean)} rows -> silver.clean_matches")


def transform_deliveries() -> None:
    """Transform bronze.raw_deliveries into silver.clean_deliveries."""
    print("\nTransforming: bronze.raw_deliveries -> silver.clean_deliveries")
    df = pd.read_sql("SELECT * FROM bronze.raw_deliveries", engine)
    print(f"  Loaded {len(df)} rows")

    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed: {before - len(df)}")

    # Parse over/ball from decimal notation in cricsheet ball column (e.g. 12.4).
    ball_as_float = pd.to_numeric(df.get("ball", pd.Series(index=df.index)), errors="coerce")
    df["over_num"] = ball_as_float.fillna(0).astype(int)
    df["ball_num"] = ((ball_as_float.fillna(0) * 10).round().astype(int) % 10).astype(int)

    df["inning"] = df.get("innings", 0).apply(safe_int)
    df["batsman"] = df.get("striker", pd.Series(index=df.index)).fillna("Unknown")
    df["bowler"] = df.get("bowler", pd.Series(index=df.index)).fillna("Unknown")
    df["batsman_runs"] = df.get("runs_off_bat", 0).apply(safe_int)
    df["extra_runs"] = df.get("extras", 0).apply(safe_int)
    df["total_runs"] = df["batsman_runs"] + df["extra_runs"]
    df["dismissal_kind"] = df.get("wicket_type", pd.Series(index=df.index)).fillna("not_out")

    wicket_flag = (
        df.get("player_dismissed", pd.Series(index=df.index)).fillna("").astype(str).str.strip() != ""
    ) | (
        df["dismissal_kind"].astype(str).str.lower() != "not_out"
    )
    df["is_wicket"] = wicket_flag.astype(bool)

    remove_outliers_iqr(df, "total_runs")

    keep = [
        "match_id",
        "inning",
        "over_num",
        "ball_num",
        "batting_team",
        "bowling_team",
        "batsman",
        "bowler",
        "batsman_runs",
        "extra_runs",
        "total_runs",
        "is_wicket",
        "dismissal_kind",
    ]
    df_clean = df[[c for c in keep if c in df.columns]].copy()

    df_clean.to_sql("clean_deliveries", engine, schema="silver", if_exists="replace", index=False)
    print(f"  Written {len(df_clean)} rows -> silver.clean_deliveries")


def transform_players() -> None:
    """Transform squads + batting + bowling stats into silver.clean_players."""
    print("\nTransforming: bronze squads/stats -> silver.clean_players")

    squads = pd.read_sql("SELECT * FROM bronze.raw_squads", engine)
    batting = pd.read_sql("SELECT * FROM bronze.raw_batting_stats", engine)
    bowling = pd.read_sql("SELECT * FROM bronze.raw_bowling_stats", engine)

    for frame in (squads, batting, bowling):
        frame.columns = [c.lower().strip().replace(" ", "_") for c in frame.columns]

    squads = squads.rename(columns={"player_name": "player_name"})
    batting = batting.rename(columns={"player": "player_name", "average": "batting_avg"})
    bowling = bowling.rename(columns={"player": "player_name", "average": "bowling_avg"})

    for frame in (squads, batting, bowling):
        frame["player_name"] = frame["player_name"].astype(str).str.strip().str.title()

    df = squads.drop_duplicates(subset=["player_name"]).copy()

    df = df.merge(
        batting[["player_name", "runs", "batting_avg", "strike_rate", "hundreds", "fifties"]]
        .drop_duplicates("player_name"),
        on="player_name",
        how="left",
    )
    df = df.merge(
        bowling[["player_name", "wickets", "bowling_avg", "economy"]].drop_duplicates("player_name"),
        on="player_name",
        how="left",
    )

    for col in ["runs", "hundreds", "fifties", "wickets"]:
        df[col] = df.get(col, 0).fillna(0).apply(safe_int)

    for col in ["batting_avg", "strike_rate", "bowling_avg", "economy"]:
        df[col] = df.get(col, 0).fillna(0).apply(safe_float)

    remove_outliers_iqr(df, "strike_rate")
    remove_outliers_iqr(df, "batting_avg")

    if "role" not in df.columns:
        def infer_role(row: pd.Series) -> str:
            w = safe_float(row.get("wickets", 0))
            r = safe_float(row.get("runs", 0))
            if w > 10 and r > 100:
                return "All-Rounder"
            if w > 5:
                return "Bowler"
            if r > 100:
                return "Batter"
            return "Unknown"

        df["role"] = df.apply(infer_role, axis=1)

    df["country"] = df.get("team", pd.Series(index=df.index)).fillna("Unknown")
    df["player_id"] = ["P" + str(i + 1).zfill(5) for i in range(len(df))]
    df["matches"] = 0

    keep = [
        "player_id",
        "player_name",
        "country",
        "role",
        "matches",
        "runs",
        "batting_avg",
        "strike_rate",
        "hundreds",
        "fifties",
        "wickets",
        "bowling_avg",
        "economy",
    ]
    df_clean = df[[c for c in keep if c in df.columns]].copy()

    null_pct = (df_clean.isnull().sum() / max(len(df_clean), 1) * 100).round(2)
    non_zero_nulls = null_pct[null_pct > 0]
    print("  Null % after cleaning:")
    print(non_zero_nulls.to_string() if not non_zero_nulls.empty else "    None")

    df_clean.to_sql("clean_players", engine, schema="silver", if_exists="replace", index=False)
    print(f"  Written {len(df_clean)} rows -> silver.clean_players")


def transform_venues() -> None:
    """Transform bronze.raw_venues into silver.clean_venues."""
    print("\nTransforming: bronze.raw_venues -> silver.clean_venues")
    df = pd.read_sql("SELECT * FROM bronze.raw_venues", engine)
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    print(f"  Loaded {len(df)} rows")

    df = df.drop_duplicates()
    df = df.rename(columns={"venue_name": "stadium_name"})

    df["stadium_name"] = df.get("stadium_name", pd.Series(index=df.index)).fillna("Unknown Venue")
    df["city"] = df.get("city", pd.Series(index=df.index)).fillna("Unknown")
    df["country"] = df.get("country", pd.Series(index=df.index)).fillna("Unknown")
    df["pitch_type"] = "Balanced"

    keep = ["stadium_name", "city", "country", "pitch_type"]
    df_clean = df[keep].copy()

    df_clean.to_sql("clean_venues", engine, schema="silver", if_exists="replace", index=False)
    print(f"  Written {len(df_clean)} rows -> silver.clean_venues")


if __name__ == "__main__":
    print("=" * 55)
    print("ETL: BRONZE -> SILVER - STARTING")
    print("=" * 55)
    transform_matches()
    transform_deliveries()
    transform_players()
    transform_venues()
    print("\n" + "=" * 55)
    print("BRONZE -> SILVER ETL COMPLETE")
    print("=" * 55)
