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


def mode_or_unknown(series: pd.Series) -> str:
    """Return most frequent non-empty string value, else 'Unknown'."""
    clean = series.fillna("").astype(str).str.strip()
    clean = clean[clean != ""]
    if clean.empty:
        return "Unknown"
    mode = clean.mode()
    return str(mode.iloc[0]) if not mode.empty else "Unknown"


def transform_matches() -> None:
    """Transform bronze.raw_matches into silver.clean_matches."""
    print("\nTransforming: bronze.raw_matches -> silver.clean_matches")
    df = pd.read_sql("SELECT * FROM bronze.raw_matches", engine)
    print(f"  Loaded {len(df)} rows")

    if df.empty:
        cols = [
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
        pd.DataFrame(columns=cols).to_sql("clean_matches", engine, schema="silver", if_exists="replace", index=False)
        print("  No rows available in bronze.raw_matches")
        return

    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed: {before - len(df)}")

    if "match_no" in df.columns:
        df["match_id"] = df["match_no"].fillna("").astype(str).str.strip()
    else:
        df["match_id"] = ""

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
    df["toss_winner"] = df.get("toss_winner", pd.Series(index=df.index)).fillna("Unknown")
    df["team1"] = df.get("team1", pd.Series(index=df.index)).fillna("Unknown")
    df["team2"] = df.get("team2", pd.Series(index=df.index)).fillna("Unknown")
    df["venue"] = df.get("venue", pd.Series(index=df.index)).fillna("Unknown Venue")
    df["city"] = df.get("city", pd.Series(index=df.index)).fillna("Unknown")
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
    df = df[df["match_id"] != ""].copy()

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
    """Transform Cricsheet squads + deliveries into silver.clean_players."""
    print("\nTransforming: bronze squads/deliveries -> silver.clean_players")

    squads = pd.read_sql("SELECT * FROM bronze.raw_squads", engine)
    deliveries = pd.read_sql("SELECT * FROM bronze.raw_deliveries", engine)

    if not squads.empty:
        squads.columns = [c.lower().strip().replace(" ", "_") for c in squads.columns]
        squads["player_name"] = squads.get("player_name", pd.Series(index=squads.index)).fillna("").astype(str).str.strip().str.title()
        squads["team"] = squads.get("team", pd.Series(index=squads.index)).fillna("Unknown").astype(str).str.strip()
        squads["role"] = squads.get("role", pd.Series(index=squads.index)).fillna("Unknown").astype(str).str.strip()

    if not deliveries.empty:
        deliveries.columns = [c.lower().strip().replace(" ", "_") for c in deliveries.columns]
        deliveries["striker"] = deliveries.get("striker", pd.Series(index=deliveries.index)).fillna("").astype(str).str.strip().str.title()
        deliveries["bowler"] = deliveries.get("bowler", pd.Series(index=deliveries.index)).fillna("").astype(str).str.strip().str.title()
        deliveries["player_dismissed"] = deliveries.get("player_dismissed", pd.Series(index=deliveries.index)).fillna("").astype(str).str.strip().str.title()
        deliveries["batting_team"] = deliveries.get("batting_team", pd.Series(index=deliveries.index)).fillna("Unknown").astype(str).str.strip()
        deliveries["bowling_team"] = deliveries.get("bowling_team", pd.Series(index=deliveries.index)).fillna("Unknown").astype(str).str.strip()
        deliveries["match_id"] = deliveries.get("match_id", pd.Series(index=deliveries.index)).fillna("").astype(str).str.strip()
        deliveries["runs_off_bat"] = deliveries.get("runs_off_bat", 0).fillna(0).apply(safe_int)
        deliveries["extras"] = deliveries.get("extras", 0).fillna(0).apply(safe_int)
        deliveries["total_runs"] = deliveries["runs_off_bat"] + deliveries["extras"]

    if squads.empty and deliveries.empty:
        cols = [
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
        pd.DataFrame(columns=cols).to_sql("clean_players", engine, schema="silver", if_exists="replace", index=False)
        print("  No rows available in bronze.raw_squads/raw_deliveries")
        return

    batsman_stats = pd.DataFrame(columns=["player_name", "matches_batted", "runs", "balls_faced", "fours", "sixes", "dismissals", "batting_avg", "strike_rate", "hundreds", "fifties"])
    bowler_stats = pd.DataFrame(columns=["player_name", "matches_bowled", "wickets", "bowling_avg", "economy"])
    batsman_team_map = pd.DataFrame(columns=["player_name", "bat_team"])
    bowler_team_map = pd.DataFrame(columns=["player_name", "bowl_team"])

    if not deliveries.empty:
        batsman_stats = (
            deliveries.groupby("striker", dropna=False)
            .agg(
                matches_batted=("match_id", "nunique"),
                runs=("runs_off_bat", "sum"),
                balls_faced=("ball", "count"),
                fours=("runs_off_bat", lambda x: int((x == 4).sum())),
                sixes=("runs_off_bat", lambda x: int((x == 6).sum())),
            )
            .reset_index()
            .rename(columns={"striker": "player_name"})
        )

        dismissals = (
            deliveries[deliveries["player_dismissed"] != ""]
            .groupby("player_dismissed")
            .size()
            .reset_index(name="dismissals")
            .rename(columns={"player_dismissed": "player_name"})
        )
        batsman_stats = batsman_stats.merge(dismissals, on="player_name", how="left")
        batsman_stats["dismissals"] = batsman_stats["dismissals"].fillna(0).apply(safe_int)

        innings_scores = (
            deliveries.groupby(["match_id", "striker"], dropna=False)["runs_off_bat"]
            .sum()
            .reset_index()
            .rename(columns={"striker": "player_name", "runs_off_bat": "innings_runs"})
        )
        fifties = (
            innings_scores[(innings_scores["innings_runs"] >= 50) & (innings_scores["innings_runs"] < 100)]
            .groupby("player_name")
            .size()
            .reset_index(name="fifties")
        )
        hundreds = (
            innings_scores[innings_scores["innings_runs"] >= 100]
            .groupby("player_name")
            .size()
            .reset_index(name="hundreds")
        )
        batsman_stats = batsman_stats.merge(fifties, on="player_name", how="left")
        batsman_stats = batsman_stats.merge(hundreds, on="player_name", how="left")
        batsman_stats["fifties"] = batsman_stats["fifties"].fillna(0).apply(safe_int)
        batsman_stats["hundreds"] = batsman_stats["hundreds"].fillna(0).apply(safe_int)

        batsman_stats["batting_avg"] = (
            batsman_stats["runs"] / batsman_stats["dismissals"].replace(0, pd.NA)
        ).fillna(batsman_stats["runs"])
        batsman_stats["strike_rate"] = (
            batsman_stats["runs"] / batsman_stats["balls_faced"].replace(0, pd.NA) * 100
        ).fillna(0)

        wicket_type = deliveries.get("wicket_type", pd.Series(index=deliveries.index)).fillna("").astype(str).str.lower().str.strip()
        wicket_mask = (
            (deliveries["player_dismissed"] != "")
            & (~wicket_type.isin(["run out", "retired hurt", "obstructing the field"]))
        )

        wickets_by_bowler = (
            deliveries[wicket_mask]
            .groupby("bowler")
            .size()
            .reset_index(name="wickets")
            .rename(columns={"bowler": "player_name"})
        )

        bowler_stats = (
            deliveries.groupby("bowler", dropna=False)
            .agg(
                matches_bowled=("match_id", "nunique"),
                runs_conceded=("total_runs", "sum"),
                balls_bowled=("ball", "count"),
            )
            .reset_index()
            .rename(columns={"bowler": "player_name"})
        )
        bowler_stats = bowler_stats.merge(wickets_by_bowler, on="player_name", how="left")
        bowler_stats["wickets"] = bowler_stats["wickets"].fillna(0).apply(safe_int)
        bowler_stats["overs_bowled"] = bowler_stats["balls_bowled"] / 6.0
        bowler_stats["economy"] = (
            bowler_stats["runs_conceded"] / bowler_stats["overs_bowled"].replace(0, pd.NA)
        ).fillna(0)
        bowler_stats["bowling_avg"] = (
            bowler_stats["runs_conceded"] / bowler_stats["wickets"].replace(0, pd.NA)
        ).fillna(0)
        bowler_stats = bowler_stats[["player_name", "matches_bowled", "wickets", "bowling_avg", "economy"]]

        batsman_team_map = (
            deliveries.groupby("striker")["batting_team"]
            .agg(mode_or_unknown)
            .reset_index()
            .rename(columns={"striker": "player_name", "batting_team": "bat_team"})
        )
        bowler_team_map = (
            deliveries.groupby("bowler")["bowling_team"]
            .agg(mode_or_unknown)
            .reset_index()
            .rename(columns={"bowler": "player_name", "bowling_team": "bowl_team"})
        )

    player_pool = set()
    if not squads.empty:
        player_pool.update(squads["player_name"].tolist())
    if not batsman_stats.empty:
        player_pool.update(batsman_stats["player_name"].tolist())
    if not bowler_stats.empty:
        player_pool.update(bowler_stats["player_name"].tolist())

    player_names = sorted([p for p in player_pool if str(p).strip() != ""])
    df = pd.DataFrame({"player_name": player_names})

    squad_team = pd.DataFrame(columns=["player_name", "squad_team"])
    squad_role = pd.DataFrame(columns=["player_name", "squad_role"])
    if not squads.empty:
        squad_team = (
            squads.groupby("player_name")["team"]
            .agg(mode_or_unknown)
            .reset_index()
            .rename(columns={"team": "squad_team"})
        )
        squad_role = (
            squads.groupby("player_name")["role"]
            .agg(mode_or_unknown)
            .reset_index()
            .rename(columns={"role": "squad_role"})
        )

    df = df.merge(squad_team, on="player_name", how="left")
    df = df.merge(squad_role, on="player_name", how="left")
    df = df.merge(batsman_stats, on="player_name", how="left")
    df = df.merge(bowler_stats, on="player_name", how="left")
    df = df.merge(batsman_team_map, on="player_name", how="left")
    df = df.merge(bowler_team_map, on="player_name", how="left")

    df["country"] = (
        df["squad_team"]
        .fillna("")
        .where(df["squad_team"].fillna("") != "", df["bat_team"].fillna(""))
        .where(
            (
                df["squad_team"].fillna("") != ""
            ) | (df["bat_team"].fillna("") != ""),
            df["bowl_team"].fillna(""),
        )
    )
    df["country"] = df["country"].replace("", "Unknown")

    for col in ["runs", "hundreds", "fifties", "wickets", "matches_batted", "matches_bowled"]:
        df[col] = df.get(col, 0).fillna(0).apply(safe_int)

    for col in ["batting_avg", "strike_rate", "bowling_avg", "economy"]:
        df[col] = df.get(col, 0).fillna(0).apply(safe_float)

    remove_outliers_iqr(df, "strike_rate")
    remove_outliers_iqr(df, "batting_avg")

    def infer_role(row: pd.Series) -> str:
        squad_defined = str(row.get("squad_role", "")).strip()
        if squad_defined and squad_defined.lower() != "unknown":
            return squad_defined
        w = safe_float(row.get("wickets", 0))
        r = safe_float(row.get("runs", 0))
        if w >= 20 and r >= 300:
            return "All-Rounder"
        if w >= 20:
            return "Bowler"
        if r >= 300:
            return "Batter"
        if w > 0 and r > 0:
            return "All-Rounder"
        if r > 0:
            return "Batter"
        if w > 0:
            return "Bowler"
        return "Unknown"

    df["role"] = df.apply(infer_role, axis=1)
    df["matches"] = df[["matches_batted", "matches_bowled"]].max(axis=1).fillna(0).apply(safe_int)
    df = df.drop_duplicates(subset=["player_name"]).sort_values("player_name").reset_index(drop=True)
    df["player_id"] = ["P" + str(i + 1).zfill(5) for i in range(len(df))]

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

    if df.empty:
        # Fallback: derive venues from match metadata if raw_venues is empty.
        df = pd.read_sql("SELECT DISTINCT venue AS venue_name, city FROM bronze.raw_matches", engine)

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
