"""ETL: Silver to Gold layer.

Populates all dimension tables and the fact table for star schema analytics.
"""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def reset_gold_tables() -> None:
    """Drop existing Gold tables to avoid FK conflicts during reload."""
    print("\nResetting existing Gold tables (if any)")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS gold.fact_match_performance CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_match CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_date CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_player CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_team CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_venue CASCADE"))
    print("  Gold tables dropped")


def load_dim_team() -> None:
    """Populate gold.dim_team from silver.clean_matches."""
    print("\nLoading -> gold.dim_team")
    matches = pd.read_sql("SELECT team1, team2 FROM silver.clean_matches", engine)
    teams = pd.concat([matches["team1"], matches["team2"]], ignore_index=True).dropna().astype(str).str.strip()
    teams = teams[teams != ""].drop_duplicates().sort_values().reset_index(drop=True)

    df = pd.DataFrame({"team_name": teams})
    df["team_id"] = range(1, len(df) + 1)
    df["icc_ranking"] = range(1, len(df) + 1)
    df["icc_rating"] = 0.0
    df["captain"] = "TBD"
    df["coach"] = "TBD"
    df["home_country"] = df["team_name"]

    keep = ["team_id", "team_name", "icc_ranking", "icc_rating", "captain", "coach", "home_country"]
    df[keep].to_sql("dim_team", engine, schema="gold", if_exists="replace", index=False)
    print(f"  {len(df)} teams -> gold.dim_team")


def load_dim_venue() -> None:
    """Populate gold.dim_venue from silver.clean_venues."""
    print("\nLoading -> gold.dim_venue")
    df = pd.read_sql("SELECT * FROM silver.clean_venues", engine)

    df["venue_id"] = range(1, len(df) + 1)
    df["avg_first_innings"] = 160.0
    df["capacity"] = 50000
    df["is_day_night"] = True

    keep = [
        "venue_id",
        "stadium_name",
        "city",
        "country",
        "pitch_type",
        "avg_first_innings",
        "capacity",
        "is_day_night",
    ]
    df[keep].to_sql("dim_venue", engine, schema="gold", if_exists="replace", index=False)
    print(f"  {len(df)} venues -> gold.dim_venue")


def load_dim_player() -> None:
    """Populate gold.dim_player from silver.clean_players."""
    print("\nLoading -> gold.dim_player")
    df = pd.read_sql("SELECT * FROM silver.clean_players", engine)

    df["batting_style"] = "Right-hand bat"
    df["bowling_style"] = "Unknown"
    df["age"] = 0
    df["is_active"] = True

    keep = [
        "player_id",
        "player_name",
        "country",
        "role",
        "batting_style",
        "bowling_style",
        "age",
        "is_active",
    ]
    df[keep].to_sql("dim_player", engine, schema="gold", if_exists="replace", index=False)
    print(f"  {len(df)} players -> gold.dim_player")


def load_dim_date() -> None:
    """Populate gold.dim_date from silver.clean_matches dates."""
    print("\nLoading -> gold.dim_date")
    matches = pd.read_sql(
        "SELECT DISTINCT match_date, tournament_phase FROM silver.clean_matches", engine
    )
    matches["match_date"] = pd.to_datetime(matches["match_date"], errors="coerce")
    matches = matches.dropna(subset=["match_date"]).copy()

    df = matches.copy()
    df["year"] = df["match_date"].dt.year
    df["month"] = df["match_date"].dt.month
    df["month_name"] = df["match_date"].dt.strftime("%B")
    df["day_of_week"] = df["match_date"].dt.strftime("%A")
    df["is_knockout"] = df["tournament_phase"].isin(["Semi Final", "Final"])
    df["is_final"] = df["tournament_phase"].eq("Final")

    keep = [
        "match_date",
        "year",
        "month",
        "month_name",
        "day_of_week",
        "tournament_phase",
        "is_knockout",
        "is_final",
    ]
    date_df = df[keep].drop_duplicates(subset=["match_date"]).sort_values("match_date").reset_index(drop=True)
    date_df["date_id"] = range(1, len(date_df) + 1)
    date_keep = [
        "date_id",
        "match_date",
        "year",
        "month",
        "month_name",
        "day_of_week",
        "tournament_phase",
        "is_knockout",
        "is_final",
    ]
    date_df[date_keep].to_sql(
        "dim_date", engine, schema="gold", if_exists="replace", index=False
    )
    print(f"  {len(date_df)} dates -> gold.dim_date")


def load_dim_match() -> None:
    """Populate gold.dim_match from silver.clean_matches + dim_team mapping."""
    print("\nLoading -> gold.dim_match")
    df = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    teams = pd.read_sql("SELECT team_id, team_name FROM gold.dim_team", engine)

    team_map = dict(zip(teams["team_name"], teams["team_id"]))

    df["toss_winner_id"] = df["toss_winner"].map(team_map)
    df["weather_condition"] = "Clear"

    if "win_by_runs" in df.columns and "win_by_wickets" in df.columns:
        df["result_type"] = df.apply(
            lambda r: "runs" if int(r.get("win_by_runs", 0) or 0) > 0 else "wickets",
            axis=1,
        )
        df["result_margin"] = df.apply(
            lambda r: int(r.get("win_by_runs", 0) or 0)
            if int(r.get("win_by_runs", 0) or 0) > 0
            else int(r.get("win_by_wickets", 0) or 0),
            axis=1,
        )
    else:
        df["result_type"] = "unknown"
        df["result_margin"] = 0

    keep = [
        "match_id",
        "toss_winner_id",
        "toss_decision",
        "weather_condition",
        "is_day_night",
        "result_type",
        "result_margin",
    ]
    df[[c for c in keep if c in df.columns]].to_sql(
        "dim_match", engine, schema="gold", if_exists="replace", index=False
    )
    print(f"  {len(df)} matches -> gold.dim_match")


def load_fact_table() -> None:
    """Populate gold.fact_match_performance from silver tables."""
    print("\nLoading -> gold.fact_match_performance")

    deliveries = pd.read_sql("SELECT * FROM silver.clean_deliveries", engine)
    matches = pd.read_sql(
        "SELECT match_id, team1, team2, winner, venue, match_date, player_of_match FROM silver.clean_matches",
        engine,
    )
    players = pd.read_sql("SELECT player_id, player_name FROM gold.dim_player", engine)
    teams = pd.read_sql("SELECT team_id, team_name FROM gold.dim_team", engine)
    venues = pd.read_sql("SELECT venue_id, stadium_name FROM gold.dim_venue", engine)
    dates = pd.read_sql("SELECT date_id, match_date FROM gold.dim_date", engine)

    # Normalize key fields for reliable joins.
    players["_k"] = players["player_name"].astype(str).str.strip().str.title()
    teams["_k"] = teams["team_name"].astype(str).str.strip()
    venues["_k"] = venues["stadium_name"].astype(str).str.strip()

    player_map = dict(zip(players["_k"], players["player_id"]))
    team_map = dict(zip(teams["_k"], teams["team_id"]))
    venue_map = dict(zip(venues["_k"], venues["venue_id"]))

    matches["match_date"] = pd.to_datetime(matches["match_date"], errors="coerce")
    dates["match_date"] = pd.to_datetime(dates["match_date"], errors="coerce")
    date_map = dict(zip(dates["match_date"].dt.date, dates["date_id"]))

    bat_agg = (
        deliveries.groupby(["match_id", "batsman", "batting_team"], dropna=False)
        .agg(
            runs_scored=("batsman_runs", "sum"),
            balls_faced=("batsman_runs", "count"),
            fours=("batsman_runs", lambda x: int((x == 4).sum())),
            sixes=("batsman_runs", lambda x: int((x == 6).sum())),
        )
        .reset_index()
        .rename(columns={"batsman": "player_name", "batting_team": "team_name"})
    )

    bowl_agg = (
        deliveries.groupby(["match_id", "bowler", "bowling_team"], dropna=False)
        .agg(
            wickets_taken=("is_wicket", "sum"),
            runs_conceded=("total_runs", "sum"),
            balls_bowled=("total_runs", "count"),
        )
        .reset_index()
        .rename(columns={"bowler": "player_name", "bowling_team": "team_name"})
    )
    bowl_agg["overs_bowled"] = (bowl_agg["balls_bowled"] / 6.0).round(1)
    bowl_agg["economy_rate"] = (
        bowl_agg["runs_conceded"] / bowl_agg["overs_bowled"].replace(0, 1)
    ).round(2)

    fact = bat_agg.merge(
        bowl_agg[["match_id", "player_name", "wickets_taken", "runs_conceded", "overs_bowled", "economy_rate"]],
        on=["match_id", "player_name"],
        how="outer",
    )

    fact["_player_k"] = fact["player_name"].astype(str).str.strip().str.title()
    fact["_team_k"] = fact["team_name"].astype(str).str.strip()
    fact["player_id"] = fact["_player_k"].map(player_map)
    fact["team_id"] = fact["_team_k"].map(team_map)

    fact = fact.merge(matches, on="match_id", how="left")
    fact["date_id"] = pd.to_datetime(fact["match_date"], errors="coerce").dt.date.map(date_map)
    fact["venue_id"] = fact["venue"].astype(str).str.strip().map(venue_map).fillna(1).astype(int)

    # Opponent lookup from team1/team2 per row.
    fact["opponent_team_name"] = fact.apply(
        lambda r: r["team2"] if str(r.get("team_name")) == str(r.get("team1")) else r.get("team1"),
        axis=1,
    )
    fact["opponent_team_id"] = fact["opponent_team_name"].astype(str).str.strip().map(team_map)

    fact["match_result"] = fact.apply(
        lambda r: "W" if str(r.get("team_name")) == str(r.get("winner")) else "L", axis=1
    )

    for col in ["runs_scored", "balls_faced", "fours", "sixes", "wickets_taken", "runs_conceded"]:
        fact[col] = fact.get(col, 0).fillna(0).astype(int)

    fact["strike_rate"] = fact.apply(
        lambda r: round((r["runs_scored"] / r["balls_faced"]) * 100, 2) if r["balls_faced"] > 0 else 0.0,
        axis=1,
    )
    fact["overs_bowled"] = fact.get("overs_bowled", 0).fillna(0.0)
    fact["economy_rate"] = fact.get("economy_rate", 0).fillna(0.0)
    fact["catches"] = 0
    fact["is_player_of_match"] = (
        fact["player_name"].astype(str).str.strip().str.title()
        == fact.get("player_of_match", "").astype(str).str.strip().str.title()
    )

    keep = [
        "match_id",
        "player_id",
        "team_id",
        "opponent_team_id",
        "venue_id",
        "date_id",
        "runs_scored",
        "balls_faced",
        "strike_rate",
        "fours",
        "sixes",
        "wickets_taken",
        "overs_bowled",
        "runs_conceded",
        "economy_rate",
        "catches",
        "match_result",
        "is_player_of_match",
    ]
    fact_clean = fact[keep].dropna(subset=["player_id", "team_id"])

    fact_clean.to_sql("fact_match_performance", engine, schema="gold", if_exists="replace", index=False)
    print(f"  {len(fact_clean)} rows -> gold.fact_match_performance")


if __name__ == "__main__":
    print("=" * 55)
    print("ETL: SILVER -> GOLD - STARTING")
    print("=" * 55)
    reset_gold_tables()
    load_dim_team()
    load_dim_venue()
    load_dim_player()
    load_dim_date()
    load_dim_match()
    load_fact_table()
    print("\n" + "=" * 55)
    print("SILVER -> GOLD ETL COMPLETE")
    print("=" * 55)
