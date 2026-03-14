"""
Feature Engineering for all ML models.
Builds ML-ready feature matrix from Silver/Gold layers.
"""

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)


def normalize_gender_value(value: str | None, default: str = "all") -> str:
    raw = str(value or "").strip().lower()
    if raw in {"male", "men", "man", "m", "boys"}:
        return "male"
    if raw in {"female", "women", "woman", "f", "girls"}:
        return "female"
    if raw in {"all", "both", "mixed", "any", ""}:
        return default
    return default


def infer_gender_from_text(*texts: str) -> str:
    blob = " ".join(str(t or "") for t in texts).lower()
    if any(token in blob for token in ["women", "female", "girls"]):
        return "female"
    if any(token in blob for token in ["men", "male", "boys"]):
        return "male"
    return "unknown"


def attach_match_gender(matches: pd.DataFrame) -> pd.DataFrame:
    frame = matches.copy()
    gender_cols = [col for col in ["gender", "match_gender", "event_gender"] if col in frame.columns]

    if gender_cols:
        base_col = gender_cols[0]
        frame["match_gender"] = frame[base_col].apply(lambda v: normalize_gender_value(v, default="unknown"))
    else:
        text_cols = [
            col
            for col in ["event_name", "event", "competition", "tournament_name", "series_name", "match_type"]
            if col in frame.columns
        ]
        if text_cols:
            frame["match_gender"] = frame[text_cols].fillna("").astype(str).agg(" ".join, axis=1).apply(
                lambda v: infer_gender_from_text(v)
            )
        else:
            frame["match_gender"] = "unknown"

    frame["match_gender"] = frame["match_gender"].apply(lambda v: normalize_gender_value(v, default="unknown"))
    return frame


def load_matches_and_deliveries(gender: str | None = None, strict_gender: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)
    deliveries = pd.read_sql("SELECT * FROM silver.clean_deliveries", engine)
    matches = attach_match_gender(matches)

    selected_gender = normalize_gender_value(gender, default="all")
    if selected_gender in {"male", "female"} and "match_gender" in matches.columns:
        filtered = matches[matches["match_gender"] == selected_gender].copy()
        if not filtered.empty:
            matches = filtered
        elif strict_gender:
            raise ValueError(f"No matches found for gender='{selected_gender}'")
        else:
            print(f"⚠️ No matches found for gender='{selected_gender}'. Falling back to full dataset.")

    if not deliveries.empty and "match_id" in deliveries.columns and "match_id" in matches.columns:
        match_ids = set(matches["match_id"].astype(str).tolist())
        deliveries = deliveries[deliveries["match_id"].astype(str).isin(match_ids)].copy()

    return matches, deliveries


def build_match_features(gender: str | None = None, strict_gender: bool = False) -> pd.DataFrame:
    """
    Build feature matrix for match outcome prediction.
    One row per match with engineered features.
    """
    matches, deliveries = load_matches_and_deliveries(gender=gender, strict_gender=strict_gender)

    # Team-level aggregates from deliveries
    team_bat = (
        deliveries.groupby("batting_team")
        .agg(
            avg_runs_per_ball=("batsman_runs", "mean"),
            avg_total_runs=("total_runs", "mean"),
            six_rate=("batsman_runs", lambda x: (x == 6).mean()),
            four_rate=("batsman_runs", lambda x: (x == 4).mean()),
        )
        .reset_index()
        .rename(columns={"batting_team": "team"})
    )

    team_bowl = (
        deliveries.groupby("bowling_team")
        .agg(
            avg_wickets_per_ball=("is_wicket", "mean"),
            avg_economy=("total_runs", "mean"),
        )
        .reset_index()
        .rename(columns={"bowling_team": "team"})
    )

    # Win counts per team
    win_counts = matches["winner"].value_counts().reset_index()
    win_counts.columns = ["team", "total_wins"]

    match_counts = (
        pd.concat([matches["team1"], matches["team2"]]).value_counts().reset_index()
    )
    match_counts.columns = ["team", "total_matches"]

    team_stats = (
        team_bat.merge(team_bowl, on="team", how="outer")
        .merge(win_counts, on="team", how="left")
        .merge(match_counts, on="team", how="left")
    )
    team_stats["win_rate"] = (
        team_stats["total_wins"] / team_stats["total_matches"].replace(0, 1)
    ).fillna(0.5)

    # Powerplay and death stats
    pp = deliveries[deliveries["over_num"] <= 6]
    death = deliveries[deliveries["over_num"] >= 16]

    pp_runs = pp.groupby("batting_team")["total_runs"].mean().reset_index()
    pp_runs.columns = ["team", "pp_run_rate"]

    death_runs = death.groupby("batting_team")["total_runs"].mean().reset_index()
    death_runs.columns = ["team", "death_run_rate"]

    death_wkts = death.groupby("bowling_team")["is_wicket"].mean().reset_index()
    death_wkts.columns = ["team", "death_wicket_rate"]

    team_stats = team_stats.merge(pp_runs, on="team", how="left")
    team_stats = team_stats.merge(death_runs, on="team", how="left")
    team_stats = team_stats.merge(death_wkts, on="team", how="left")
    team_stats = team_stats.fillna(team_stats.median(numeric_only=True))

    # Build per-match feature rows
    rows = []
    for _, m in matches.iterrows():
        t1 = team_stats[team_stats["team"] == m["team1"]]
        t2 = team_stats[team_stats["team"] == m["team2"]]
        if t1.empty or t2.empty:
            continue
        t1, t2 = t1.iloc[0], t2.iloc[0]

        toss_team1 = 1 if m.get("toss_winner") == m["team1"] else 0
        toss_bat = 1 if m.get("toss_decision") == "bat" else 0

        row = {
            "run_rate_diff": t1["avg_runs_per_ball"] - t2["avg_runs_per_ball"],
            "six_rate_diff": t1["six_rate"] - t2["six_rate"],
            "four_rate_diff": t1["four_rate"] - t2["four_rate"],
            "pp_run_rate_diff": t1["pp_run_rate"] - t2["pp_run_rate"],
            "death_run_rate_diff": t1["death_run_rate"] - t2["death_run_rate"],
            "wicket_rate_diff": t1["avg_wickets_per_ball"] - t2["avg_wickets_per_ball"],
            "death_wkt_rate_diff": t1["death_wicket_rate"] - t2["death_wicket_rate"],
            "economy_diff": t1["avg_economy"] - t2["avg_economy"],
            "win_rate_t1": t1["win_rate"],
            "win_rate_t2": t2["win_rate"],
            "win_rate_diff": t1["win_rate"] - t2["win_rate"],
            "toss_team1": toss_team1,
            "toss_bat_first": toss_bat,
            "toss_advantage": toss_team1 * toss_bat,
            "is_knockout": 1 if m.get("tournament_phase") in ["Semi Final", "Final"] else 0,
            "target": 1 if m.get("winner") == m["team1"] else 0,
            "match_id": m.get("match_id", ""),
            "team1": m["team1"],
            "team2": m["team2"],
        }
        rows.append(row)

    df = pd.DataFrame(rows).fillna(0)
    selected_gender = normalize_gender_value(gender, default="all")
    df["match_gender_scope"] = selected_gender
    print(f"✅ Feature matrix: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def build_player_features(gender: str | None = None, strict_gender: bool = False) -> pd.DataFrame:
    """Build player feature matrix for clustering."""
    _, deliveries = load_matches_and_deliveries(gender=gender, strict_gender=strict_gender)

    if deliveries.empty:
        cols = ["player_name", "total_runs", "balls_faced", "strike_rate_live", "sixes", "fours", "wickets", "economy_live"]
        return pd.DataFrame(columns=cols)

    bat_stats = (
        deliveries.groupby("batsman")
        .agg(
            total_runs=("batsman_runs", "sum"),
            balls_faced=("batsman_runs", "count"),
            sixes=("batsman_runs", lambda x: (x == 6).sum()),
            fours=("batsman_runs", lambda x: (x == 4).sum()),
        )
        .reset_index()
    )
    bat_stats["strike_rate_live"] = (
        bat_stats["total_runs"] / bat_stats["balls_faced"].replace(0, 1) * 100
    ).round(2)

    bowl_stats = (
        deliveries.groupby("bowler")
        .agg(
            wickets=("is_wicket", "sum"),
            balls_bowled=("total_runs", "count"),
            runs_given=("total_runs", "sum"),
        )
        .reset_index()
    )
    bowl_stats["economy_live"] = (
        bowl_stats["runs_given"] / (bowl_stats["balls_bowled"] / 6).replace(0, 1)
    ).round(2)

    df = bat_stats.merge(bowl_stats, left_on="batsman", right_on="bowler", how="outer")
    df["player_name"] = df["batsman"].fillna(df["bowler"])
    df = df.fillna(0)

    feature_cols = ["total_runs", "balls_faced", "strike_rate_live", "sixes", "fours", "wickets", "economy_live"]
    player_df = df[["player_name"] + feature_cols].copy()
    print(f"✅ Player features: {player_df.shape[0]} players")
    return player_df


if __name__ == "__main__":
    build_match_features()
    build_player_features()
