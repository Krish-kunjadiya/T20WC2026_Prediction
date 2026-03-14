"""FastAPI backend for ML predictions and analytics metadata."""

from __future__ import annotations

import json
import os
import pickle
import time
from typing import Any, Callable

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text


load_dotenv()

app = FastAPI(
    title="T20 WC 2026 Prediction API",
    description="ML-powered cricket analytics API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)
engine = create_engine(DATABASE_URL)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

_MODEL_CACHE: dict[str, Any] = {}
_DATA_CACHE: dict[str, tuple[float, pd.DataFrame]] = {}
_DATA_CACHE_TTL_SECONDS = int(os.getenv("API_DATA_CACHE_TTL_SECONDS", "120"))
_RESPONSE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_RESPONSE_CACHE_TTL_SECONDS = int(os.getenv("API_RESPONSE_CACHE_TTL_SECONDS", "180"))


def load_model(filename: str) -> Any:
    """Load a pickled model artifact from models directory."""
    if filename in _MODEL_CACHE:
        return _MODEL_CACHE[filename]

    path = os.path.join(MODELS_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as file_handle:
            model = pickle.load(file_handle)
            _MODEL_CACHE[filename] = model
            return model

    _MODEL_CACHE[filename] = None
    return _MODEL_CACHE[filename]


def _get_cached_frame(cache_key: str, query: str, normalize_fn: Callable[[pd.DataFrame], pd.DataFrame]) -> pd.DataFrame:
    """Load and cache large DB tables in memory for a short TTL."""
    now = time.time()
    cached = _DATA_CACHE.get(cache_key)
    if cached:
        ts, frame = cached
        if (now - ts) <= _DATA_CACHE_TTL_SECONDS:
            return frame

    frame = pd.read_sql(query, engine)
    frame = normalize_fn(frame)
    _DATA_CACHE[cache_key] = (now, frame)
    return frame


def clear_runtime_caches() -> None:
    """Clear in-memory model and data caches."""
    _MODEL_CACHE.clear()
    _DATA_CACHE.clear()
    _RESPONSE_CACHE.clear()


def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    """Return cached API payload if still valid."""
    cached = _RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None

    ts, payload = cached
    if (time.time() - ts) > _RESPONSE_CACHE_TTL_SECONDS:
        return None
    return payload


def set_cached_response(cache_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Store API payload in in-memory response cache."""
    _RESPONSE_CACHE[cache_key] = (time.time(), payload)
    return payload


def read_csv_if_exists(path: str) -> pd.DataFrame:
    """Return a DataFrame if CSV exists, else an empty DataFrame."""
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp numeric value to the given bounds."""
    return max(lower, min(upper, value))


def as_numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    """Convert a pandas series to numeric safely."""
    return pd.to_numeric(series, errors="coerce").fillna(default)


def as_bool_int(series: pd.Series) -> pd.Series:
    """Convert boolean-like series to 0/1 integers."""
    if series.empty:
        return series
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)

    text_series = series.fillna(False).astype(str).str.strip().str.lower()
    truthy = {"1", "true", "t", "yes", "y"}
    return text_series.isin(truthy).astype(int)


def normalize_venue_name(venue: str | None) -> str:
    """Normalize frontend venue value for matching in DB records."""
    raw = str(venue or "").strip()
    if not raw or raw.lower() == "neutral venue":
        return ""

    # Frontend often sends "Stadium Name, City".
    if "," in raw:
        raw = raw.split(",", 1)[0].strip()
    return raw


def batting_first_team(row: pd.Series) -> str:
    """Infer batting first team from toss winner and toss decision."""
    team1 = str(row.get("team1") or "")
    team2 = str(row.get("team2") or "")
    toss_winner = str(row.get("toss_winner") or "")
    toss_decision = str(row.get("toss_decision") or "").strip().lower()

    if toss_winner not in {team1, team2}:
        return team1

    if toss_decision == "bat":
        return toss_winner

    if toss_winner == team1:
        return team2
    return team1


def _normalize_matches_frame(matches: pd.DataFrame) -> pd.DataFrame:
    """Normalize clean matches frame."""
    if matches.empty:
        return matches

    matches["team1"] = matches["team1"].fillna("").astype(str)
    matches["team2"] = matches["team2"].fillna("").astype(str)
    matches["winner"] = matches["winner"].fillna("").astype(str)
    matches["toss_winner"] = matches["toss_winner"].fillna("").astype(str)
    matches["toss_decision"] = matches["toss_decision"].fillna("bat").astype(str)
    matches["venue"] = matches["venue"].fillna("").astype(str)
    matches["city"] = matches["city"].fillna("").astype(str)
    matches["match_id"] = matches["match_id"].fillna("").astype(str)
    matches["win_by_runs"] = as_numeric(matches.get("win_by_runs", pd.Series(index=matches.index)), 0).astype(int)
    matches["win_by_wickets"] = as_numeric(matches.get("win_by_wickets", pd.Series(index=matches.index)), 0).astype(int)
    matches["match_date"] = pd.to_datetime(matches.get("match_date"), errors="coerce")
    return matches


def load_matches_frame() -> pd.DataFrame:
    """Load and normalize clean matches table using in-memory cache."""
    frame = _get_cached_frame("clean_matches", "SELECT * FROM silver.clean_matches", _normalize_matches_frame)
    return frame.copy(deep=False)


def _normalize_deliveries_frame(deliveries: pd.DataFrame) -> pd.DataFrame:
    """Normalize clean deliveries frame."""
    if deliveries.empty:
        return deliveries

    deliveries["match_id"] = deliveries["match_id"].fillna("").astype(str)
    deliveries["inning"] = as_numeric(deliveries.get("inning", pd.Series(index=deliveries.index)), 1).astype(int)
    deliveries["over_num"] = as_numeric(deliveries.get("over_num", pd.Series(index=deliveries.index)), 0).astype(int)
    deliveries["ball_num"] = as_numeric(deliveries.get("ball_num", pd.Series(index=deliveries.index)), 1).astype(int)
    deliveries["batting_team"] = deliveries["batting_team"].fillna("").astype(str)
    deliveries["bowling_team"] = deliveries["bowling_team"].fillna("").astype(str)
    deliveries["batsman"] = deliveries["batsman"].fillna("").astype(str)
    deliveries["bowler"] = deliveries["bowler"].fillna("").astype(str)
    deliveries["batsman_runs"] = as_numeric(deliveries.get("batsman_runs", pd.Series(index=deliveries.index)), 0)
    deliveries["total_runs"] = as_numeric(deliveries.get("total_runs", pd.Series(index=deliveries.index)), 0)
    deliveries["is_wicket_int"] = as_bool_int(deliveries.get("is_wicket", pd.Series(index=deliveries.index)))
    return deliveries


def load_deliveries_frame() -> pd.DataFrame:
    """Load and normalize clean deliveries table using in-memory cache."""
    frame = _get_cached_frame("clean_deliveries", "SELECT * FROM silver.clean_deliveries", _normalize_deliveries_frame)
    return frame.copy(deep=False)


def _normalize_players_frame(players: pd.DataFrame) -> pd.DataFrame:
    """Normalize clean players frame."""
    if players.empty:
        return players

    players["player_name"] = players["player_name"].fillna("").astype(str)
    players["country"] = players["country"].fillna("").astype(str)
    players["role"] = players.get("role", "Unknown").fillna("Unknown").astype(str)

    for col in ["runs", "batting_avg", "strike_rate", "wickets", "bowling_avg", "economy", "matches"]:
        players[col] = as_numeric(players.get(col, pd.Series(index=players.index)), 0)
    return players


def load_players_frame() -> pd.DataFrame:
    """Load and normalize clean players table using in-memory cache."""
    frame = _get_cached_frame("clean_players", "SELECT * FROM silver.clean_players", _normalize_players_frame)
    return frame.copy(deep=False)


def filter_matches_by_venue(matches: pd.DataFrame, venue: str | None) -> pd.DataFrame:
    """Filter matches by a normalized venue string."""
    venue_norm = normalize_venue_name(venue)
    if not venue_norm or matches.empty:
        return matches

    mask = matches["venue"].str.lower().str.contains(venue_norm.lower(), regex=False)
    filtered = matches[mask]
    return filtered if not filtered.empty else matches


def team_match_subset(matches: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return match subset where team participated."""
    if matches.empty:
        return matches
    return matches[(matches["team1"] == team) | (matches["team2"] == team)].copy()


def team_win_rate(matches: pd.DataFrame, team: str) -> float:
    """Compute team win rate from a matches frame."""
    subset = team_match_subset(matches, team)
    if subset.empty:
        return 0.5
    return float((subset["winner"] == team).mean())


def recent_form_rate(matches: pd.DataFrame, team: str, last_n: int = 8) -> float:
    """Compute recent form as win rate over latest N matches."""
    subset = team_match_subset(matches, team)
    if subset.empty:
        return 0.5

    subset = subset.sort_values("match_date", kind="stable")
    recent = subset.tail(last_n)
    if recent.empty:
        return 0.5
    return float((recent["winner"] == team).mean())


def team_batting_index(deliveries: pd.DataFrame, team: str) -> float:
    """Composite batting strength score for a team."""
    subset = deliveries[deliveries["batting_team"] == team]
    if subset.empty:
        return 0.0

    run_rate = float(subset["total_runs"].mean() * 6)
    boundary_pct = float((subset["batsman_runs"] >= 4).mean() * 100)
    dot_pct = float((subset["total_runs"] == 0).mean() * 100)
    wicket_pct = float(subset["is_wicket_int"].mean() * 100)
    return (run_rate * 0.62) + (boundary_pct * 0.04) - (dot_pct * 0.02) - (wicket_pct * 0.01)


def team_bowling_index(deliveries: pd.DataFrame, team: str) -> float:
    """Composite bowling pressure score for a team."""
    subset = deliveries[deliveries["bowling_team"] == team]
    if subset.empty:
        return 0.0

    economy = float(subset["total_runs"].mean() * 6)
    wicket_pct = float(subset["is_wicket_int"].mean() * 100)
    dot_pct = float((subset["total_runs"] == 0).mean() * 100)
    return (wicket_pct * 0.08) + (dot_pct * 0.04) - (economy * 0.15)


def venue_bat_first_win_rate(matches: pd.DataFrame, venue: str | None) -> float:
    """Win rate for batting first teams at the selected venue."""
    filtered = filter_matches_by_venue(matches, venue)
    if filtered.empty:
        return 0.5

    first_team = filtered.apply(batting_first_team, axis=1)
    win_mask = first_team == filtered["winner"]
    return float(win_mask.mean()) if len(win_mask) else 0.5


def team_venue_win_rate(matches: pd.DataFrame, team: str, venue: str | None) -> float:
    """Team win rate at selected venue, fallback to global team win rate."""
    filtered = filter_matches_by_venue(matches, venue)
    subset = team_match_subset(filtered, team)
    if subset.empty:
        return team_win_rate(matches, team)
    return float((subset["winner"] == team).mean())


def compute_contextual_win_probability(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    team_a: str,
    team_b: str,
    toss_winner: str,
    toss_decision: str = "bat",
    venue: str | None = None,
) -> dict[str, Any]:
    """Compute calibrated win probability from context features and historical samples."""
    all_h2h = matches[
        ((matches["team1"] == team_a) & (matches["team2"] == team_b))
        | ((matches["team1"] == team_b) & (matches["team2"] == team_a))
    ]
    venue_h2h = filter_matches_by_venue(all_h2h, venue)

    h2h_used = venue_h2h if len(venue_h2h) >= 2 else all_h2h
    h2h_prob = float((h2h_used["winner"] == team_a).mean()) if not h2h_used.empty else 0.5

    overall_a = team_win_rate(matches, team_a)
    overall_b = team_win_rate(matches, team_b)
    overall_prob = clamp(0.5 + ((overall_a - overall_b) * 0.45), 0.05, 0.95)

    form_a = recent_form_rate(matches, team_a, 8)
    form_b = recent_form_rate(matches, team_b, 8)
    form_prob = clamp(0.5 + ((form_a - form_b) * 0.38), 0.05, 0.95)

    venue_a = team_venue_win_rate(matches, team_a, venue)
    venue_b = team_venue_win_rate(matches, team_b, venue)
    venue_prob = clamp(0.5 + ((venue_a - venue_b) * 0.42), 0.05, 0.95)

    batting_a = team_batting_index(deliveries, team_a)
    batting_b = team_batting_index(deliveries, team_b)
    bowling_a = team_bowling_index(deliveries, team_a)
    bowling_b = team_bowling_index(deliveries, team_b)
    strength_delta = (batting_a - bowling_b) - (batting_b - bowling_a)
    strength_prob = clamp(0.5 + (strength_delta * 0.06), 0.05, 0.95)

    prior_prob = (
        (0.30 * h2h_prob)
        + (0.24 * overall_prob)
        + (0.18 * form_prob)
        + (0.16 * venue_prob)
        + (0.12 * strength_prob)
    )

    # Toss impact: smaller effect than old simplistic simulator.
    toss_adj = 0.0
    toss_winner = str(toss_winner or "").strip()
    toss_decision = str(toss_decision or "bat").strip().lower()
    if toss_winner == team_a:
        toss_adj += 0.018
    elif toss_winner == team_b:
        toss_adj -= 0.018

    venue_bat_first = venue_bat_first_win_rate(matches, venue)
    bat_first_bias = (venue_bat_first - 0.5) * 0.07

    if toss_winner in {team_a, team_b}:
        if toss_decision == "bat":
            toss_adj += bat_first_bias if toss_winner == team_a else -bat_first_bias
        else:
            toss_adj -= bat_first_bias if toss_winner == team_a else -bat_first_bias

    adjusted_prob = clamp(prior_prob + toss_adj, 0.03, 0.97)

    # Confidence-driven shrinkage prevents overconfident probabilities on sparse samples.
    sample_score = min(1.0, (len(team_match_subset(matches, team_a)) + len(team_match_subset(matches, team_b)) + len(h2h_used)) / 220.0)
    shrunk = 0.5 + ((adjusted_prob - 0.5) * (0.55 + (0.45 * sample_score)))

    cap = 0.92 if sample_score >= 0.80 else 0.86 if sample_score >= 0.45 else 0.78
    final_prob_a = clamp(shrunk, 1 - cap, cap)

    return {
        "probTeamA": round(final_prob_a * 100, 1),
        "probTeamB": round((1 - final_prob_a) * 100, 1),
        "confidence": round(sample_score * 100, 1),
        "components": {
            "h2hProb": round(h2h_prob * 100, 1),
            "overallWinRateProb": round(overall_prob * 100, 1),
            "recentFormProb": round(form_prob * 100, 1),
            "venueProb": round(venue_prob * 100, 1),
            "strengthProb": round(strength_prob * 100, 1),
            "tossAdjustmentPct": round(toss_adj * 100, 2),
        },
        "sample": {
            "h2hMatches": int(len(h2h_used)),
            "teamAMatches": int(len(team_match_subset(matches, team_a))),
            "teamBMatches": int(len(team_match_subset(matches, team_b))),
            "venueH2HUsed": bool(len(venue_h2h) >= 2),
        },
    }


def build_model_feature_vector(deliveries: pd.DataFrame, matches: pd.DataFrame, team_a: str, team_b: str, toss_winner: str, toss_decision: str, is_knockout: int) -> dict[str, float]:
    """Build feature vector expected by match outcome XGBoost model."""

    def mean_team_value(df: pd.DataFrame, col: str, team_col: str, team: str) -> float:
        subset = df[df[team_col] == team]
        if subset.empty:
            return 0.0
        return float(subset[col].mean())

    def wr(team: str) -> float:
        return team_win_rate(matches, team)

    six_rate_a = float((deliveries[deliveries["batting_team"] == team_a]["batsman_runs"] == 6).mean())
    six_rate_b = float((deliveries[deliveries["batting_team"] == team_b]["batsman_runs"] == 6).mean())
    four_rate_a = float((deliveries[deliveries["batting_team"] == team_a]["batsman_runs"] == 4).mean())
    four_rate_b = float((deliveries[deliveries["batting_team"] == team_b]["batsman_runs"] == 4).mean())

    pp_a = mean_team_value(deliveries[deliveries["over_num"] <= 5], "total_runs", "batting_team", team_a)
    pp_b = mean_team_value(deliveries[deliveries["over_num"] <= 5], "total_runs", "batting_team", team_b)
    death_a = mean_team_value(deliveries[deliveries["over_num"] >= 16], "total_runs", "batting_team", team_a)
    death_b = mean_team_value(deliveries[deliveries["over_num"] >= 16], "total_runs", "batting_team", team_b)

    death_wkt_a = mean_team_value(deliveries[deliveries["over_num"] >= 16], "is_wicket_int", "bowling_team", team_a)
    death_wkt_b = mean_team_value(deliveries[deliveries["over_num"] >= 16], "is_wicket_int", "bowling_team", team_b)

    overall_wkt_a = mean_team_value(deliveries, "is_wicket_int", "bowling_team", team_a)
    overall_wkt_b = mean_team_value(deliveries, "is_wicket_int", "bowling_team", team_b)

    econ_a = mean_team_value(deliveries, "total_runs", "bowling_team", team_a)
    econ_b = mean_team_value(deliveries, "total_runs", "bowling_team", team_b)

    run_rate_a = mean_team_value(deliveries, "batsman_runs", "batting_team", team_a)
    run_rate_b = mean_team_value(deliveries, "batsman_runs", "batting_team", team_b)

    toss_team1 = 1 if toss_winner == team_a else 0
    toss_bat = 1 if toss_decision == "bat" else 0

    return {
        "run_rate_diff": run_rate_a - run_rate_b,
        "six_rate_diff": six_rate_a - six_rate_b,
        "four_rate_diff": four_rate_a - four_rate_b,
        "pp_run_rate_diff": pp_a - pp_b,
        "death_run_rate_diff": death_a - death_b,
        "wicket_rate_diff": overall_wkt_a - overall_wkt_b,
        "death_wkt_rate_diff": death_wkt_a - death_wkt_b,
        "economy_diff": econ_a - econ_b,
        "win_rate_t1": wr(team_a),
        "win_rate_t2": wr(team_b),
        "win_rate_diff": wr(team_a) - wr(team_b),
        "toss_team1": float(toss_team1),
        "toss_bat_first": float(toss_bat),
        "toss_advantage": float(toss_team1 * toss_bat),
        "is_knockout": float(is_knockout),
    }


def build_points_table(matches: pd.DataFrame) -> pd.DataFrame:
    """Build points table from clean_matches with simple NRR proxy."""
    if matches.empty:
        return pd.DataFrame(columns=["Rank", "Team", "P", "W", "L", "Pts", "NRR"])

    teams_all = pd.concat([matches["team1"], matches["team2"]], ignore_index=True).dropna().unique()
    records: list[dict[str, Any]] = []

    for team in teams_all:
        team_matches = matches[(matches["team1"] == team) | (matches["team2"] == team)]
        played = int(len(team_matches))
        won = int((team_matches["winner"] == team).sum())
        lost = max(played - won, 0)
        pts = won * 2

        runs_margin = as_numeric(team_matches.get("win_by_runs", pd.Series(index=team_matches.index)), 0)
        runs_for = runs_margin.where(team_matches["winner"] == team, 0).sum()
        runs_against = runs_margin.where(team_matches["winner"] != team, 0).sum()
        nrr = round(float((runs_for - runs_against) / max(played, 1) * 0.1), 3)

        records.append({"Team": str(team), "P": played, "W": won, "L": lost, "Pts": pts, "NRR": nrr})

    points = pd.DataFrame(records).sort_values(["Pts", "NRR"], ascending=False).reset_index(drop=True)
    points.insert(0, "Rank", points.index + 1)
    return points


def build_projected_points_table(points: pd.DataFrame, team: str, margin_runs: int) -> pd.DataFrame:
    """Simulate one additional result for a team and recompute ranks."""
    simulated = points.copy()
    if simulated.empty or team not in simulated["Team"].values:
        return simulated

    idx = simulated.index[simulated["Team"] == team][0]
    margin_runs = int(margin_runs)

    simulated.loc[idx, "P"] = int(simulated.loc[idx, "P"]) + 1
    if margin_runs >= 0:
        simulated.loc[idx, "W"] = int(simulated.loc[idx, "W"]) + 1
        simulated.loc[idx, "Pts"] = int(simulated.loc[idx, "Pts"]) + 2
    else:
        simulated.loc[idx, "L"] = int(simulated.loc[idx, "L"]) + 1

    simulated.loc[idx, "NRR"] = round(float(simulated.loc[idx, "NRR"]) + (margin_runs * 0.005), 3)

    simulated = simulated.sort_values(["Pts", "NRR"], ascending=False).reset_index(drop=True)
    simulated["Rank"] = simulated.index + 1
    return simulated


def compute_upset_probability(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    favourite_team: str,
    underdog_team: str,
    toss_winner: str,
    toss_bat_first: int,
    is_knockout: int,
) -> float:
    """Compute upset probability with model if available, heuristic fallback otherwise."""
    artifact = load_model("upset_detector_lr.pkl")

    wr_fav = team_win_rate(matches, favourite_team)
    wr_und = team_win_rate(matches, underdog_team)

    fav_rr = float(deliveries[deliveries["batting_team"] == favourite_team]["total_runs"].mean() or 0.0)
    und_rr = float(deliveries[deliveries["batting_team"] == underdog_team]["total_runs"].mean() or 0.0)

    fav_death_wkt = float(deliveries[(deliveries["bowling_team"] == favourite_team) & (deliveries["over_num"] >= 16)]["is_wicket_int"].mean() or 0.0)
    und_death_wkt = float(deliveries[(deliveries["bowling_team"] == underdog_team) & (deliveries["over_num"] >= 16)]["is_wicket_int"].mean() or 0.0)

    if artifact and isinstance(artifact, dict) and "model" in artifact and "features" in artifact:
        feat_cols = artifact["features"]
        model = artifact["model"]

        payload = {
            "win_rate_diff": wr_fav - wr_und,
            "run_rate_diff": fav_rr - und_rr,
            "toss_team1": 1 if toss_winner == favourite_team else 0,
            "toss_bat_first": int(toss_bat_first),
            "pp_run_rate_diff": (fav_rr - und_rr),
            "death_wkt_rate_diff": fav_death_wkt - und_death_wkt,
            "is_knockout": int(is_knockout),
        }
        row = pd.DataFrame([payload]).reindex(columns=feat_cols, fill_value=0)
        upset = float(model.predict_proba(row)[0][1])
        return clamp(upset, 0.02, 0.98)

    # Heuristic fallback if model missing.
    base = 0.18
    base += clamp((wr_fav - wr_und) * -0.45, -0.18, 0.35)
    base += clamp((fav_rr - und_rr) * -0.20, -0.12, 0.20)
    base += 0.03 if toss_winner == underdog_team else -0.03
    base += 0.04 if is_knockout else 0.0
    return clamp(base, 0.02, 0.90)


def build_first_innings_dataset(deliveries: pd.DataFrame) -> pd.DataFrame:
    """Prepare innings-level table for score expectation and historical lookup."""
    if deliveries.empty:
        return pd.DataFrame()

    grouped = (
        deliveries.groupby(["match_id", "inning", "batting_team"])
        .agg(
            total_runs=("total_runs", "sum"),
            total_balls=("total_runs", "count"),
            wickets_lost=("is_wicket_int", "sum"),
            sixes=("batsman_runs", lambda s: int((s == 6).sum())),
            fours=("batsman_runs", lambda s: int((s == 4).sum())),
            pp_runs=("total_runs", lambda s: float(s.head(min(36, len(s))).sum())),
        )
        .reset_index()
    )
    grouped["pp_run_rate"] = grouped["pp_runs"] / 6.0
    grouped["boundary_pct"] = (grouped["sixes"] + grouped["fours"]) / grouped["total_balls"].replace(0, 1)
    return grouped[grouped["total_runs"] > 50].copy()


def build_match_win_probability_timeline(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    match_id: str,
    team_a: str,
    team_b: str,
) -> list[dict[str, Any]]:
    """Build over-level win probability timeline for selected match."""
    match_rows = matches[matches["match_id"] == str(match_id)]
    if match_rows.empty:
        return []

    match_row = match_rows.iloc[0]
    innings_df = deliveries[deliveries["match_id"] == str(match_id)].copy()
    if innings_df.empty:
        return []

    innings_df = innings_df.sort_values(["inning", "over_num", "ball_num"], kind="stable")

    over_stats = (
        innings_df.groupby(["inning", "over_num", "batting_team"], as_index=False)
        .agg(runs=("total_runs", "sum"), wickets=("is_wicket_int", "sum"), balls=("ball_num", "count"))
        .sort_values(["inning", "over_num"], kind="stable")
    )

    first_team = batting_first_team(match_row)
    second_team = str(match_row["team1"] if first_team == match_row["team2"] else match_row["team2"])

    first_innings = build_first_innings_dataset(deliveries)
    first_outcome = pd.DataFrame(columns=["total_runs", "bat_first_win"])
    if not first_innings.empty:
        first_only = first_innings[first_innings["inning"] == 1].copy()
        if not first_only.empty:
            winners = matches[["match_id", "winner", "team1", "team2", "toss_winner", "toss_decision"]].copy()
            first_only = first_only.merge(winners, on="match_id", how="left")
            first_only["bat_first_team"] = first_only.apply(batting_first_team, axis=1)
            first_only["bat_first_win"] = (first_only["winner"] == first_only["bat_first_team"]).astype(int)
            first_outcome = first_only[["total_runs", "bat_first_win"]].copy()

    def defend_probability(projected_total: float) -> float:
        if first_outcome.empty:
            return clamp(0.5 + ((projected_total - 165) * 0.0038), 0.08, 0.92)

        window = first_outcome[
            first_outcome["total_runs"].between(projected_total - 15, projected_total + 15)
        ]
        if len(window) < 12:
            window = first_outcome[
                first_outcome["total_runs"].between(projected_total - 30, projected_total + 30)
            ]
        if window.empty:
            return clamp(0.5 + ((projected_total - 165) * 0.0038), 0.08, 0.92)
        return clamp(float(window["bat_first_win"].mean()), 0.08, 0.92)

    timeline: list[dict[str, Any]] = []
    first_runs = first_balls = first_wickets = 0
    second_runs = second_balls = second_wickets = 0

    for _, row in over_stats.iterrows():
        inning = int(row["inning"])
        over = int(row["over_num"]) + 1
        runs = int(row["runs"])
        wickets = int(row["wickets"])
        balls = int(row["balls"])

        if inning == 1:
            first_runs += runs
            first_wickets += wickets
            first_balls += balls

            run_rate = (first_runs / max(first_balls, 1)) * 6
            projected_total = run_rate * 20
            p_first = defend_probability(projected_total)
            p_team_a = p_first if first_team == team_a else (1 - p_first)
        else:
            second_runs += runs
            second_wickets += wickets
            second_balls += balls

            target = first_runs + 1
            runs_needed = max(target - second_runs, 0)
            balls_left = max(120 - second_balls, 0)

            if runs_needed <= 0:
                p_second = 0.99
            elif balls_left <= 0:
                p_second = 0.01
            else:
                required_rr = (runs_needed * 6) / balls_left
                wickets_left = max(10 - second_wickets, 0)
                p_second = clamp(0.58 - ((required_rr - 8.0) * 0.08) + ((wickets_left - 5) * 0.035), 0.02, 0.98)

            p_team_a = p_second if second_team == team_a else (1 - p_second)

        timeline.append(
            {
                "over": f"Innings {inning} - Over {over}",
                "inning": inning,
                "overNumber": over,
                "probTeamA": round(p_team_a * 100, 1),
                "probTeamB": round((1 - p_team_a) * 100, 1),
            }
        )

    return timeline


def latest_team_momentum(deliveries: pd.DataFrame, team: str, match_id: str | None = None) -> dict[str, Any]:
    """Compute last 3-over momentum against team historical baseline."""
    subset = deliveries[deliveries["batting_team"] == team].copy()
    if subset.empty:
        return {
            "runsLast3Overs": 0,
            "expectedLast3Overs": 0,
            "momentumDelta": 0,
            "indicator": "No data",
        }

    if match_id:
        match_subset = subset[subset["match_id"] == str(match_id)]
        if not match_subset.empty:
            subset = match_subset

    over_runs = subset.groupby(["match_id", "inning", "over_num"], as_index=False)["total_runs"].sum()
    latest_match = over_runs.sort_values(["match_id", "inning", "over_num"], kind="stable").iloc[-1]["match_id"]
    latest_innings = over_runs[over_runs["match_id"] == latest_match].copy()
    latest_innings = latest_innings.sort_values("over_num", kind="stable")

    runs_last3 = float(latest_innings.tail(3)["total_runs"].sum())
    baseline_over = float(over_runs["total_runs"].mean()) if not over_runs.empty else 0.0
    expected_last3 = baseline_over * 3
    delta = runs_last3 - expected_last3

    indicator = "Neutral"
    if delta >= 6:
        indicator = "Surging"
    elif delta <= -6:
        indicator = "Under pressure"

    return {
        "runsLast3Overs": round(runs_last3, 1),
        "expectedLast3Overs": round(expected_last3, 1),
        "momentumDelta": round(delta, 1),
        "indicator": indicator,
    }


def venue_run_rate(deliveries: pd.DataFrame, matches: pd.DataFrame, venue: str | None) -> float:
    """Compute venue average run rate for comparison."""
    venue_matches = filter_matches_by_venue(matches, venue)
    if venue_matches.empty:
        return float(deliveries["total_runs"].mean() * 6) if not deliveries.empty else 0.0

    match_ids = venue_matches["match_id"].astype(str).tolist()
    subset = deliveries[deliveries["match_id"].isin(match_ids)]
    if subset.empty:
        return float(deliveries["total_runs"].mean() * 6) if not deliveries.empty else 0.0

    return float(subset["total_runs"].mean() * 6)


def top_bowler_vs_opponent(deliveries: pd.DataFrame, bowling_team: str, opponent: str) -> dict[str, Any]:
    """Return most successful bowler against an opponent."""
    subset = deliveries[(deliveries["bowling_team"] == bowling_team) & (deliveries["batting_team"] == opponent)]
    if subset.empty:
        return {"bowler": "N/A", "wickets": 0, "balls": 0}

    grouped = (
        subset.groupby("bowler", as_index=False)
        .agg(wickets=("is_wicket_int", "sum"), balls=("ball_num", "count"))
        .sort_values(["wickets", "balls"], ascending=[False, False], kind="stable")
    )
    if grouped.empty:
        return {"bowler": "N/A", "wickets": 0, "balls": 0}

    row = grouped.iloc[0]
    return {"bowler": str(row["bowler"]), "wickets": int(row["wickets"]), "balls": int(row["balls"])}


def best_performer_at_venue(deliveries: pd.DataFrame, matches: pd.DataFrame, venue: str | None) -> dict[str, Any]:
    """Find best all-round performer at selected venue."""
    venue_matches = filter_matches_by_venue(matches, venue)
    if venue_matches.empty:
        return {"player": "N/A", "runs": 0, "wickets": 0, "score": 0.0}

    match_ids = venue_matches["match_id"].astype(str).tolist()
    subset = deliveries[deliveries["match_id"].isin(match_ids)]
    if subset.empty:
        return {"player": "N/A", "runs": 0, "wickets": 0, "score": 0.0}

    runs = subset.groupby("batsman", as_index=False)["batsman_runs"].sum().rename(columns={"batsman": "player", "batsman_runs": "runs"})
    wickets = subset.groupby("bowler", as_index=False)["is_wicket_int"].sum().rename(columns={"bowler": "player", "is_wicket_int": "wickets"})

    merged = runs.merge(wickets, on="player", how="outer").fillna(0)
    if merged.empty:
        return {"player": "N/A", "runs": 0, "wickets": 0, "score": 0.0}

    merged["score"] = merged["runs"] + (merged["wickets"] * 25)
    merged = merged.sort_values("score", ascending=False, kind="stable")
    top = merged.iloc[0]

    return {
        "player": str(top["player"]),
        "runs": int(top["runs"]),
        "wickets": int(top["wickets"]),
        "score": round(float(top["score"]), 1),
    }


def fun_fact_for_team_venue(matches: pd.DataFrame, team: str, venue: str | None) -> str:
    """Generate a simple venue trend fact sentence."""
    filtered = filter_matches_by_venue(matches, venue)
    team_matches = team_match_subset(filtered, team).sort_values("match_date", kind="stable")
    if team_matches.empty:
        return "No strong venue trend found yet for this team."

    recent = team_matches.tail(6)
    wins = int((recent["winner"] == team).sum())
    played = int(len(recent))
    if played == 0:
        return "No recent venue data available."

    return f"{team} has won {wins} of the last {played} matches at this venue."


class MatchRequest(BaseModel):
    team_a: str
    team_b: str
    toss_winner: str
    toss_decision: str = "bat"
    is_knockout: int = 0
    venue: str = "Neutral Venue"


class ScoreRequest(BaseModel):
    total_balls: int = Field(default=120, ge=30, le=120)
    wickets_lost: int = Field(default=2, ge=0, le=10)
    sixes: int = Field(default=5, ge=0, le=36)
    fours: int = Field(default=10, ge=0, le=60)
    pp_runs: int = Field(default=50, ge=0, le=120)
    pp_run_rate: float = Field(default=8.3, ge=0.0, le=20.0)
    boundary_pct: float = Field(default=0.15, ge=0.0, le=1.0)


class QueryRequest(BaseModel):
    sql: str


class ChatRequest(BaseModel):
    prompt: str
    chat_history: list[dict[str, str]] | None = None
    match_context: str | None = None


class MatchPreviewRequest(BaseModel):
    team_a: str
    team_b: str
    venue: str = "Neutral Venue"


class UpsetRequest(BaseModel):
    favourite_team: str
    underdog_team: str
    toss_winner: str
    toss_bat_first: int = 1
    is_knockout: int = 0


class AnalystWinRequest(BaseModel):
    team_a: str
    team_b: str
    toss_winner: str
    toss_decision: str = "bat"
    venue: str = "Neutral Venue"
    is_knockout: int = 0


def build_match_prediction_payload(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    team_a: str,
    team_b: str,
    toss_winner: str,
    toss_decision: str = "bat",
    is_knockout: int = 0,
    venue: str = "Neutral Venue",
) -> dict[str, Any]:
    """Build a calibrated match prediction payload from preloaded dataframes."""
    context_prob = compute_contextual_win_probability(
        matches=matches,
        deliveries=deliveries,
        team_a=team_a,
        team_b=team_b,
        toss_winner=toss_winner,
        toss_decision=toss_decision,
        venue=venue,
    )

    artifact = load_model("match_outcome_xgb.pkl")
    model_prob_a = None

    if artifact and isinstance(artifact, dict) and "model" in artifact and "features" in artifact:
        try:
            feature_vector = build_model_feature_vector(
                deliveries=deliveries,
                matches=matches,
                team_a=team_a,
                team_b=team_b,
                toss_winner=toss_winner,
                toss_decision=toss_decision,
                is_knockout=is_knockout,
            )
            feat_cols = artifact["features"]
            model = artifact["model"]
            X = pd.DataFrame([feature_vector]).reindex(columns=feat_cols, fill_value=0)
            probability = model.predict_proba(X)[0]
            model_prob_a = float(probability[1])
        except Exception:
            model_prob_a = None

    if model_prob_a is None:
        final_prob_a = context_prob["probTeamA"] / 100.0
    else:
        context_weight = 0.58
        model_weight = 0.42
        blended = (context_weight * (context_prob["probTeamA"] / 100.0)) + (model_weight * model_prob_a)

        confidence = context_prob["confidence"] / 100.0
        cap = 0.90 if confidence > 0.7 else 0.85 if confidence > 0.4 else 0.80
        final_prob_a = clamp(blended, 1 - cap, cap)

    final_prob_b = 1 - final_prob_a

    return {
        "team_a": team_a,
        "team_b": team_b,
        "prob_team_a": round(final_prob_a * 100, 1),
        "prob_team_b": round(final_prob_b * 100, 1),
        "predicted_winner": team_a if final_prob_a >= 0.5 else team_b,
        "model_prob_team_a": round(model_prob_a * 100, 1) if model_prob_a is not None else None,
        "context_prob_team_a": context_prob["probTeamA"],
        "confidence": context_prob["confidence"],
        "factors": context_prob["components"],
        "sample": context_prob["sample"],
    }


def build_analyst_win_probability_payload(prediction_payload: dict[str, Any]) -> dict[str, Any]:
    """Map base prediction payload into analyst endpoint contract."""
    context_a = float(prediction_payload.get("context_prob_team_a", 50.0))
    return {
        "teamA": prediction_payload.get("team_a"),
        "teamB": prediction_payload.get("team_b"),
        "probTeamA": prediction_payload.get("prob_team_a"),
        "probTeamB": prediction_payload.get("prob_team_b"),
        "predictedWinner": prediction_payload.get("predicted_winner"),
        "confidence": prediction_payload.get("confidence"),
        "factors": prediction_payload.get("factors"),
        "samples": prediction_payload.get("sample"),
        "contextOnly": {
            "probTeamA": round(context_a, 1),
            "probTeamB": round(100.0 - context_a, 1),
            "confidence": prediction_payload.get("confidence"),
            "components": prediction_payload.get("factors"),
            "sample": prediction_payload.get("sample"),
        },
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "models": [f for f in os.listdir(MODELS_DIR) if f.endswith(".pkl")] if os.path.exists(MODELS_DIR) else [],
    }


@app.post("/cache/refresh")
def refresh_runtime_caches() -> dict[str, Any]:
    """Manually refresh in-memory caches after data/model updates."""
    clear_runtime_caches()
    return {"status": "ok", "message": "Runtime caches cleared"}


@app.post("/predict/match")
def predict_match(req: MatchRequest) -> dict[str, Any]:
    matches = load_matches_frame()
    deliveries = load_deliveries_frame()

    return build_match_prediction_payload(
        matches=matches,
        deliveries=deliveries,
        team_a=req.team_a,
        team_b=req.team_b,
        toss_winner=req.toss_winner,
        toss_decision=req.toss_decision,
        is_knockout=req.is_knockout,
        venue=req.venue,
    )


@app.post("/predict/score")
def predict_score(req: ScoreRequest) -> dict[str, Any]:
    if req.sixes + req.fours > req.total_balls:
        raise HTTPException(status_code=422, detail="Sixes + fours cannot exceed total balls")
    if req.pp_runs > req.total_balls * 2:
        raise HTTPException(status_code=422, detail="Powerplay runs are unrealistically high for the entered state")

    artifact = load_model("score_predictor_lgbm.pkl")
    if not artifact:
        raise HTTPException(status_code=500, detail="Score model not found")

    model = artifact["model"]
    feat_cols = artifact["features"]

    payload = req.model_dump()
    payload["pp_run_rate"] = req.pp_runs / 6.0
    payload["boundary_pct"] = (req.sixes + req.fours) / max(req.total_balls, 1)

    X = pd.DataFrame([payload]).reindex(columns=feat_cols, fill_value=0)
    model_pred = float(model.predict(X)[0])

    deliveries = load_deliveries_frame()
    innings = build_first_innings_dataset(deliveries)

    historical_pred = None
    similar_count = 0
    if not innings.empty:
        similar = innings[
            innings["wickets_lost"].between(req.wickets_lost - 2, req.wickets_lost + 2)
            & innings["pp_runs"].between(req.pp_runs - 14, req.pp_runs + 14)
            & innings["sixes"].between(req.sixes - 6, req.sixes + 6)
            & innings["fours"].between(req.fours - 8, req.fours + 8)
        ]
        similar_count = int(len(similar))
        if similar_count >= 6:
            historical_pred = float(similar["total_runs"].median())

    if historical_pred is None:
        final_pred = model_pred
    else:
        blend = 0.30 if similar_count >= 20 else 0.20 if similar_count >= 12 else 0.15
        final_pred = ((1 - blend) * model_pred) + (blend * historical_pred)

    lower_bound = req.pp_runs
    upper_bound = max(90, req.pp_runs + ((120 - req.total_balls) * 3) + 70)
    pred = int(round(clamp(final_pred, lower_bound, upper_bound)))

    avg_score = float(innings["total_runs"].mean()) if not innings.empty else 160.0
    classification = "above_avg" if pred >= avg_score else "below_avg"

    return {
        "predicted_score": pred,
        "classification": classification,
        "avg_reference_score": round(avg_score, 1),
        "model_prediction": round(model_pred, 1),
        "historical_anchor": round(historical_pred, 1) if historical_pred is not None else None,
        "historical_sample_size": similar_count,
    }


@app.get("/teams")
def get_teams() -> dict[str, list[str]]:
    teams = pd.read_sql("SELECT DISTINCT team_name FROM gold.dim_team ORDER BY team_name", engine)
    return {"teams": teams["team_name"].dropna().astype(str).tolist()}


@app.get("/venues")
def get_venues() -> dict[str, list[str]]:
    venues = pd.read_sql(
        "SELECT DISTINCT stadium_name, city FROM silver.clean_venues ORDER BY stadium_name, city",
        engine,
    )
    venue_list: list[str] = []
    for _, row in venues.iterrows():
        stadium = str(row.get("stadium_name") or "").strip()
        city = str(row.get("city") or "").strip()
        if not stadium:
            continue
        venue_list.append(f"{stadium}, {city}" if city and city.lower() != "unknown" else stadium)

    if "Neutral Venue" not in venue_list:
        venue_list.append("Neutral Venue")
    return {"venues": venue_list}


@app.get("/players/{country}")
def get_players(country: str) -> dict[str, Any]:
    sql = text(
        """
        SELECT player_name, role, runs, batting_avg, strike_rate, wickets, economy
        FROM silver.clean_players
        WHERE country = :country
        ORDER BY runs DESC
        LIMIT 20
        """
    )
    with engine.connect() as conn:
        frame = pd.read_sql(sql, conn, params={"country": country})
    return {"players": frame.to_dict(orient="records")}


@app.get("/strategist/overview")
def strategist_overview() -> dict[str, Any]:
    matches = load_matches_frame()
    points = build_points_table(matches)

    qual_data: list[dict[str, Any]] = []
    if not points.empty:
        top_eight = points.head(8).copy()
        max_pts = float(top_eight["Pts"].max()) if float(top_eight["Pts"].max()) > 0 else 1.0
        top_eight["QualPct"] = ((top_eight["Pts"] / max_pts * 72) + (top_eight["NRR"].rank(pct=True) * 28)).clip(0, 100).round(1)
        qual_data = [
            {
                "team": str(row["Team"]),
                "qualPct": float(row["QualPct"]),
                "pts": int(row["Pts"]),
                "nrr": float(row["NRR"]),
            }
            for _, row in top_eight.iterrows()
        ]

    run_by_margin: list[dict[str, Any]] = []
    wicket_by_margin: list[dict[str, Any]] = []
    if not matches.empty:
        run_hist = as_numeric(matches["win_by_runs"], 0).astype(int)
        wicket_hist = as_numeric(matches["win_by_wickets"], 0).astype(int)

        run_counts = run_hist[run_hist > 0].value_counts().sort_index()
        wicket_counts = wicket_hist[wicket_hist > 0].value_counts().sort_index()

        run_by_margin = [{"margin": int(idx), "count": int(val)} for idx, val in run_counts.items()]
        wicket_by_margin = [{"margin": int(idx), "count": int(val)} for idx, val in wicket_counts.items()]

    return {
        "pointsTable": points.to_dict(orient="records"),
        "qualificationData": qual_data,
        "runsMarginDistribution": run_by_margin,
        "wicketsMarginDistribution": wicket_by_margin,
    }


@app.get("/strategist/nrr-simulate")
def strategist_nrr_simulate(team: str, margin_runs: int = 20) -> dict[str, Any]:
    matches = load_matches_frame()
    points = build_points_table(matches)
    if points.empty or team not in points["Team"].values:
        raise HTTPException(status_code=404, detail="Team not found")

    current = points[points["Team"] == team].iloc[0]
    current_nrr = float(current["NRR"])
    current_rank = int(current["Rank"])

    projected_table = build_projected_points_table(points, team, margin_runs)
    projected_row = projected_table[projected_table["Team"] == team].iloc[0]
    projected_nrr = float(projected_row["NRR"])
    projected_rank = int(projected_row["Rank"])

    return {
        "team": team,
        "currentNrr": current_nrr,
        "projectedNrr": projected_nrr,
        "currentRank": current_rank,
        "projectedRank": projected_rank,
        "rankDelta": current_rank - projected_rank,
        "nrrDelta": round(projected_nrr - current_nrr, 3),
    }


@app.get("/metrics")
def get_metrics() -> Any:
    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as file_handle:
            return json.load(file_handle)
    raise HTTPException(status_code=404, detail="Metrics not found")


@app.post("/query")
def execute_query(req: QueryRequest) -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            frame = pd.read_sql(text(req.sql), conn)
        return {"data": frame.to_dict(orient="records")}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> dict[str, str]:
    try:
        from genai.rag_engine import ask_cricai

        answer = ask_cricai(req.prompt, chat_history=req.chat_history)
        return {"response": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat/preview")
def chat_preview_endpoint(req: MatchPreviewRequest) -> dict[str, str]:
    try:
        from genai.rag_engine import generate_match_preview

        preview = generate_match_preview(req.team_a, req.team_b, req.venue)
        return {"preview": preview}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/dashboard/kpis")
def get_dashboard_kpis() -> dict[str, Any]:
    cached = get_cached_response("dashboard_kpis")
    if cached is not None:
        return cached

    matches = load_matches_frame()
    deliveries = load_deliveries_frame()

    total_matches = int(len(matches))
    teams = sorted(set(matches["team1"].tolist() + matches["team2"].tolist())) if not matches.empty else []
    total_teams = len([t for t in teams if str(t).strip()])

    first_innings = build_first_innings_dataset(deliveries)
    avg_first_score = int(round(float(first_innings[first_innings["inning"] == 1]["total_runs"].mean()))) if not first_innings.empty else 0

    if not matches.empty:
        first_team = matches.apply(batting_first_team, axis=1)
        chase_win = (matches["winner"] != first_team).mean() * 100
    else:
        chase_win = 0.0

    payload = {
        "total_matches": total_matches,
        "total_teams": total_teams,
        "avg_first_innings_score": avg_first_score,
        "chasing_win_pct": round(float(chase_win), 1),
    }
    return set_cached_response("dashboard_kpis", payload)


@app.get("/dashboard/charts")
def get_dashboard_charts() -> dict[str, Any]:
    cached = get_cached_response("dashboard_charts")
    if cached is not None:
        return cached

    matches = load_matches_frame()
    deliveries = load_deliveries_frame()
    players = load_players_frame()

    evolution_data: list[dict[str, Any]] = []
    if not matches.empty and not deliveries.empty:
        first = (
            deliveries[deliveries["inning"] == 1]
            .groupby("match_id", as_index=False)
            .agg(total_runs=("total_runs", "sum"), balls=("total_runs", "count"), wkt=("is_wicket_int", "mean"))
        )
        first = first.merge(matches[["match_id", "match_date"]], on="match_id", how="left")
        first["year"] = first["match_date"].dt.year
        first["strike_rate"] = (first["total_runs"] / first["balls"].replace(0, 1)) * 100
        first["wkt_pct"] = first["wkt"] * 100
        yearly = (
            first.dropna(subset=["year"])
            .groupby("year", as_index=False)
            .agg(avgScore=("total_runs", "mean"), strikeRate=("strike_rate", "mean"), wktProb=("wkt_pct", "mean"))
            .sort_values("year")
        )
        evolution_data = [
            {
                "year": int(row["year"]),
                "avgScore": round(float(row["avgScore"]), 1),
                "strikeRate": round(float(row["strikeRate"]), 2),
                "wktProb": round(float(row["wktProb"]), 2),
            }
            for _, row in yearly.iterrows()
        ]

    top_batsmen_data: list[dict[str, Any]] = []
    if not deliveries.empty:
        top_bat = (
            deliveries.groupby("batsman", as_index=False)["batsman_runs"]
            .sum()
            .sort_values("batsman_runs", ascending=False)
            .head(10)
        )
        top_batsmen_data = [
            {"player": str(row["batsman"]), "runs": int(row["batsman_runs"])}
            for _, row in top_bat.iterrows()
        ]

    top_bowlers_data: list[dict[str, Any]] = []
    if not deliveries.empty:
        top_bowl = (
            deliveries.groupby("bowler", as_index=False)["is_wicket_int"]
            .sum()
            .sort_values("is_wicket_int", ascending=False)
            .head(10)
        )
        top_bowlers_data = [
            {"player": str(row["bowler"]), "wickets": int(row["is_wicket_int"])}
            for _, row in top_bowl.iterrows()
        ]

    venue_matches_data: list[dict[str, Any]] = []
    venue_win_style_data: list[dict[str, Any]] = []
    toss_impact_data: list[dict[str, Any]] = []
    match_competitiveness_data: list[dict[str, Any]] = []

    if not matches.empty:
        venue_counts = matches.groupby("venue", as_index=False).size().rename(columns={"size": "matches"})
        venue_counts = venue_counts.sort_values("matches", ascending=False).head(10)
        venue_matches_data = [
            {"venue": str(row["venue"]), "matches": int(row["matches"])}
            for _, row in venue_counts.iterrows()
        ]

        temp = matches.copy()
        temp["bat_first_team"] = temp.apply(batting_first_team, axis=1)
        temp["win_style"] = temp.apply(
            lambda row: "Bat First Win" if str(row["winner"]) == str(row["bat_first_team"]) else "Chasing Win",
            axis=1,
        )
        grouped = (
            temp.groupby(["venue", "win_style"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
        top_venue_names = venue_counts["venue"].tolist()
        grouped = grouped[grouped["venue"].isin(top_venue_names)]
        pivot = grouped.pivot_table(index="venue", columns="win_style", values="count", fill_value=0).reset_index()

        for _, row in pivot.iterrows():
            venue_win_style_data.append(
                {
                    "venue": str(row["venue"]),
                    "batFirstWins": int(row.get("Bat First Win", 0)),
                    "chasingWins": int(row.get("Chasing Win", 0)),
                }
            )

        toss_df = matches.copy()
        toss_df["toss_helped"] = (toss_df["toss_winner"] == toss_df["winner"]).astype(int)
        toss_summary = (
            toss_df.groupby("toss_decision", as_index=False)
            .agg(winPct=("toss_helped", "mean"), matches=("match_id", "count"))
            .sort_values("matches", ascending=False)
        )
        toss_summary["winPct"] = toss_summary["winPct"] * 100
        toss_impact_data = [
            {
                "decision": str(row["toss_decision"]).capitalize(),
                "winPct": round(float(row["winPct"]), 1),
                "matches": int(row["matches"]),
            }
            for _, row in toss_summary.iterrows()
        ]

        run_margin = as_numeric(matches["win_by_runs"], 0).astype(int)
        wkt_margin = as_numeric(matches["win_by_wickets"], 0).astype(int)

        buckets = {"Close": 0, "Competitive": 0, "Dominant": 0}
        for runs, wkts in zip(run_margin.tolist(), wkt_margin.tolist()):
            if runs <= 0 and wkts <= 0:
                continue
            if (0 < runs <= 10) or (0 < wkts <= 3):
                buckets["Close"] += 1
            elif (10 < runs <= 35) or (3 < wkts <= 6):
                buckets["Competitive"] += 1
            else:
                buckets["Dominant"] += 1

        match_competitiveness_data = [
            {"bucket": key, "matches": int(val)} for key, val in buckets.items()
        ]

    powerplay_leaders_data: list[dict[str, Any]] = []
    death_bowling_leaders_data: list[dict[str, Any]] = []

    if not deliveries.empty:
        pp = deliveries[deliveries["over_num"] <= 5]
        if not pp.empty:
            pp_stats = (
                pp.groupby("batting_team", as_index=False)
                .agg(runs=("total_runs", "sum"), balls=("total_runs", "count"))
            )
            pp_stats["runRate"] = (pp_stats["runs"] / pp_stats["balls"].replace(0, 1)) * 6
            pp_stats = pp_stats.sort_values("runRate", ascending=False).head(10)
            powerplay_leaders_data = [
                {"team": str(row["batting_team"]), "runRate": round(float(row["runRate"]), 2)}
                for _, row in pp_stats.iterrows()
            ]

        death = deliveries[deliveries["over_num"] >= 16]
        if not death.empty:
            death_stats = (
                death.groupby("bowling_team", as_index=False)
                .agg(runs=("total_runs", "sum"), balls=("total_runs", "count"), wickets=("is_wicket_int", "sum"))
            )
            death_stats = death_stats[death_stats["balls"] >= 60]
            if not death_stats.empty:
                death_stats["economy"] = (death_stats["runs"] / death_stats["balls"].replace(0, 1)) * 6
                death_stats = death_stats.sort_values("economy", ascending=True).head(10)
                death_bowling_leaders_data = [
                    {
                        "team": str(row["bowling_team"]),
                        "economy": round(float(row["economy"]), 2),
                        "wickets": int(row["wickets"]),
                    }
                    for _, row in death_stats.iterrows()
                ]

    player_archetypes_data: list[dict[str, Any]] = []
    if not players.empty:
        sample = players[(players["runs"] > 100) & (players["strike_rate"] > 0) & (players["batting_avg"] > 0)].copy()
        sample = sample.sort_values("runs", ascending=False).head(120)
        player_archetypes_data = [
            {
                "name": str(row["player_name"]),
                "average": round(float(row["batting_avg"]), 2),
                "strikeRate": round(float(row["strike_rate"]), 2),
                "runs": int(row["runs"]),
                "type": str(row.get("role", "Unknown")),
            }
            for _, row in sample.iterrows()
        ]

    payload = {
        "evolutionData": evolution_data,
        "topBatsmenData": top_batsmen_data,
        "topBowlersData": top_bowlers_data,
        "venueMatchesData": venue_matches_data,
        "venueWinStyleData": venue_win_style_data,
        "tossImpactData": toss_impact_data,
        "matchCompetitivenessData": match_competitiveness_data,
        "powerplayLeadersData": powerplay_leaders_data,
        "deathBowlingLeadersData": death_bowling_leaders_data,
        "playerArchetypesData": player_archetypes_data,
    }
    return set_cached_response("dashboard_charts", payload)


@app.get("/dashboard/summary")
def get_dashboard_summary() -> dict[str, Any]:
    cached = get_cached_response("dashboard_summary")
    if cached is not None:
        return cached

    payload = {
        "kpis": get_dashboard_kpis(),
        "charts": get_dashboard_charts(),
    }
    return set_cached_response("dashboard_summary", payload)


@app.on_event("startup")
def prewarm_dashboard_summary_cache() -> None:
    """Warm dashboard caches so first UI load is faster."""
    if os.getenv("API_PREWARM_DASHBOARD", "1") != "1":
        return

    try:
        get_dashboard_summary()
    except Exception:
        # Do not block API startup if prewarm fails.
        pass


@app.get("/commentator/meta")
def commentator_meta() -> dict[str, Any]:
    matches = load_matches_frame()

    teams = sorted(
        {
            str(team)
            for team in pd.concat([matches.get("team1", pd.Series()), matches.get("team2", pd.Series())], ignore_index=True)
            .dropna()
            .astype(str)
            .tolist()
            if str(team).strip()
        }
    )

    venues = sorted({str(v) for v in matches.get("venue", pd.Series()).dropna().astype(str).tolist() if str(v).strip()})
    if "Neutral Venue" not in venues:
        venues.append("Neutral Venue")

    ordered = matches.sort_values(["match_date", "match_id"], ascending=[False, False], kind="stable")
    options = [
        {
            "matchId": str(row["match_id"]),
            "label": f"{row['team1']} vs {row['team2']} | {row['venue']}",
            "team1": str(row["team1"]),
            "team2": str(row["team2"]),
            "venue": str(row["venue"]),
            "winner": str(row["winner"]),
        }
        for _, row in ordered.head(400).iterrows()
    ]

    return {"teams": teams, "venues": venues, "matches": options}


@app.get("/commentator/live-feed")
def commentator_live_feed(limit: int = 18) -> dict[str, Any]:
    try:
        sql = text(
            """
            SELECT event_id, over_num, ball_num, batting_team, striker_name, bowler_name, runs_scored, is_wicket, created_at
            FROM public.live_ball_events
            ORDER BY event_id DESC
            LIMIT :limit
            """
        )
        with engine.connect() as conn:
            frame = pd.read_sql(sql, conn, params={"limit": int(max(1, min(limit, 100)))})
        if frame.empty:
            return {"available": False, "events": []}

        frame["is_wicket"] = as_bool_int(frame.get("is_wicket", pd.Series(index=frame.index))).astype(int)
        frame = frame.sort_values("event_id", ascending=False)
        return {"available": True, "events": frame.to_dict(orient="records")}
    except Exception:
        return {"available": False, "events": []}


@app.get("/commentator/overview")
def commentator_overview() -> dict[str, Any]:
    deliveries = load_deliveries_frame()
    if deliveries.empty:
        return {
            "topRunScorers": [],
            "topWicketTakers": [],
            "mostSixes": [],
            "teamTotalRuns": [],
            "recordHighlights": {
                "highestIndividualScore": 0,
                "highestTeamTotal": 0,
                "totalSixes": 0,
                "totalFours": 0,
            },
        }

    top_runs = (
        deliveries.groupby("batsman", as_index=False)["batsman_runs"]
        .sum()
        .sort_values("batsman_runs", ascending=False)
        .head(10)
    )
    top_runs = top_runs.rename(columns={"batsman": "player", "batsman_runs": "runs"})

    top_wkts = (
        deliveries.groupby("bowler", as_index=False)["is_wicket_int"]
        .sum()
        .sort_values("is_wicket_int", ascending=False)
        .head(10)
    )
    top_wkts = top_wkts.rename(columns={"bowler": "bowler", "is_wicket_int": "wickets"})

    sixes = (
        deliveries[deliveries["batsman_runs"] == 6]
        .groupby("batsman", as_index=False)
        .size()
        .rename(columns={"batsman": "player", "size": "sixes"})
        .sort_values("sixes", ascending=False)
        .head(10)
    )

    team_totals = (
        deliveries.groupby("batting_team", as_index=False)["batsman_runs"]
        .sum()
        .rename(columns={"batting_team": "team", "batsman_runs": "runs"})
        .sort_values("runs", ascending=False)
        .head(12)
    )

    highest_individual = (
        deliveries.groupby(["match_id", "batsman"], as_index=False)["batsman_runs"]
        .sum()["batsman_runs"]
        .max()
    )
    highest_team_total = (
        deliveries.groupby(["match_id", "batting_team"], as_index=False)["total_runs"]
        .sum()["total_runs"]
        .max()
    )

    return {
        "topRunScorers": top_runs.to_dict(orient="records"),
        "topWicketTakers": top_wkts.to_dict(orient="records"),
        "mostSixes": sixes.to_dict(orient="records"),
        "teamTotalRuns": team_totals.to_dict(orient="records"),
        "recordHighlights": {
            "highestIndividualScore": int(highest_individual or 0),
            "highestTeamTotal": int(highest_team_total or 0),
            "totalSixes": int((deliveries["batsman_runs"] == 6).sum()),
            "totalFours": int((deliveries["batsman_runs"] == 4).sum()),
        },
    }


@app.get("/commentator/insights")
def commentator_insights(
    team: str,
    opponent: str,
    venue: str = "Neutral Venue",
    match_id: str | None = None,
) -> dict[str, Any]:
    matches = load_matches_frame()
    deliveries = load_deliveries_frame()
    players = load_players_frame()

    top_team_batter = players[players["country"] == team].sort_values("runs", ascending=False).head(1)
    top_run_scorer = {
        "player": str(top_team_batter.iloc[0]["player_name"]) if not top_team_batter.empty else "N/A",
        "runs": int(top_team_batter.iloc[0]["runs"]) if not top_team_batter.empty else 0,
    }

    fastest_team_player = players[players["country"] == team].sort_values("strike_rate", ascending=False).head(1)
    fastest_scorer = {
        "player": str(fastest_team_player.iloc[0]["player_name"]) if not fastest_team_player.empty else "N/A",
        "strikeRate": round(float(fastest_team_player.iloc[0]["strike_rate"]), 2) if not fastest_team_player.empty else 0.0,
    }

    milestones = [500, 1000, 1500, 2000, 2500, 3000, 3500]
    current_runs = top_run_scorer["runs"]
    next_milestone = next((m for m in milestones if m > current_runs), ((current_runs // 500) + 1) * 500)
    milestone_needed = max(next_milestone - current_runs, 0)
    milestone_alert = (
        f"{top_run_scorer['player']} needs {milestone_needed} runs to reach {next_milestone} tournament runs."
        if top_run_scorer["player"] != "N/A"
        else "No player milestone data available."
    )

    venue_best = best_performer_at_venue(deliveries, matches, venue)

    global_sixes = (
        deliveries[deliveries["batsman_runs"] == 6]
        .groupby("batsman", as_index=False)
        .size()
        .rename(columns={"batsman": "player", "size": "sixes"})
        .sort_values("sixes", ascending=False)
    )
    team_sixes = (
        deliveries[(deliveries["batsman_runs"] == 6) & (deliveries["batting_team"] == team)]
        .groupby("batsman", as_index=False)
        .size()
        .rename(columns={"batsman": "player", "size": "sixes"})
        .sort_values("sixes", ascending=False)
    )

    record_watch = "Record watch unavailable."
    if not global_sixes.empty and not team_sixes.empty:
        all_time = global_sixes.iloc[0]
        team_top = team_sixes.iloc[0]
        gap = int(all_time["sixes"] - team_top["sixes"])
        if gap <= 0:
            record_watch = f"{team_top['player']} is currently tied for most sixes in tournament history ({int(team_top['sixes'])})."
        else:
            record_watch = f"{team_top['player']} needs {gap} more sixes to match the all-time tournament record ({int(all_time['sixes'])})."

    momentum = latest_team_momentum(deliveries, team, match_id)

    current_rr = 0.0
    if match_id:
        current_subset = deliveries[(deliveries["match_id"] == str(match_id)) & (deliveries["batting_team"] == team)]
        if not current_subset.empty:
            current_rr = float(current_subset["total_runs"].mean() * 6)
    if current_rr == 0.0:
        team_subset = deliveries[deliveries["batting_team"] == team]
        current_rr = float(team_subset["total_runs"].mean() * 6) if not team_subset.empty else 0.0

    venue_rr = venue_run_rate(deliveries, matches, venue)
    run_rate_comparison = {
        "currentRunRate": round(current_rr, 2),
        "venueAvgRunRate": round(venue_rr, 2),
        "delta": round(current_rr - venue_rr, 2),
    }

    best_vs_opponent = top_bowler_vs_opponent(deliveries, team, opponent)
    fun_fact = fun_fact_for_team_venue(matches, team, venue)

    selected_match = None
    if match_id:
        mm = matches[matches["match_id"] == str(match_id)]
        if not mm.empty:
            selected_match = mm.iloc[0]

    if selected_match is None:
        fallback = matches[
            ((matches["team1"] == team) & (matches["team2"] == opponent))
            | ((matches["team1"] == opponent) & (matches["team2"] == team))
        ].sort_values("match_date", ascending=False, kind="stable")
        if not fallback.empty:
            selected_match = fallback.iloc[0]

    timeline: list[dict[str, Any]] = []
    if selected_match is not None:
        match_a = str(selected_match["team1"])
        match_b = str(selected_match["team2"])
        timeline = build_match_win_probability_timeline(
            matches=matches,
            deliveries=deliveries,
            match_id=str(selected_match["match_id"]),
            team_a=match_a,
            team_b=match_b,
        )

    current_probability = timeline[-1] if timeline else {"probTeamA": 50.0, "probTeamB": 50.0, "inning": 0}

    return {
        "topRunScorer": top_run_scorer,
        "milestoneAlert": milestone_alert,
        "bestPerformerAtVenue": venue_best,
        "fastestScorer": fastest_scorer,
        "recordWatch": record_watch,
        "teamMomentum": momentum,
        "runRateComparison": run_rate_comparison,
        "bestBowlerVsOpponent": best_vs_opponent,
        "funFact": fun_fact,
        "winProbabilityTimeline": timeline,
        "currentWinProbability": current_probability,
    }


@app.get("/analyst/meta")
def analyst_meta() -> dict[str, Any]:
    matches = load_matches_frame()
    teams = sorted(
        {
            str(team)
            for team in pd.concat([matches.get("team1", pd.Series()), matches.get("team2", pd.Series())], ignore_index=True)
            .dropna()
            .astype(str)
            .tolist()
            if str(team).strip()
        }
    )

    venues = sorted({str(v) for v in matches.get("venue", pd.Series()).dropna().astype(str).tolist() if str(v).strip()})
    if "Neutral Venue" not in venues:
        venues.append("Neutral Venue")

    return {"teams": teams, "venues": venues}


@app.post("/analyst/win-probability")
def analyst_win_probability(req: AnalystWinRequest) -> dict[str, Any]:
    matches = load_matches_frame()
    deliveries = load_deliveries_frame()
    model_payload = build_match_prediction_payload(
        matches=matches,
        deliveries=deliveries,
        team_a=req.team_a,
        team_b=req.team_b,
        toss_winner=req.toss_winner,
        toss_decision=req.toss_decision,
        is_knockout=req.is_knockout,
        venue=req.venue,
    )
    return build_analyst_win_probability_payload(model_payload)


@app.get("/analyst/insights")
def analyst_insights(
    team: str,
    opponent: str,
    venue: str = "Neutral Venue",
    toss_winner: str | None = None,
    toss_decision: str = "bat",
) -> dict[str, Any]:
    matches = load_matches_frame()
    deliveries = load_deliveries_frame()

    # Expected first-innings score at venue for selected team.
    innings = build_first_innings_dataset(deliveries)
    venue_matches = filter_matches_by_venue(matches, venue)
    venue_ids = set(venue_matches["match_id"].astype(str).tolist()) if not venue_matches.empty else set()

    expected_pool = innings[(innings["batting_team"] == team) & (innings["inning"] == 1)]
    if venue_ids:
        venue_specific = expected_pool[expected_pool["match_id"].astype(str).isin(venue_ids)]
        if len(venue_specific) >= 4:
            expected_pool = venue_specific

    expected_score = float(expected_pool["total_runs"].mean()) if not expected_pool.empty else 0.0
    score_q25 = float(expected_pool["total_runs"].quantile(0.25)) if not expected_pool.empty else 0.0
    score_q75 = float(expected_pool["total_runs"].quantile(0.75)) if not expected_pool.empty else 0.0

    # Venue performance index.
    team_venue_matches = team_match_subset(venue_matches, team)
    venue_win_pct = float((team_venue_matches["winner"] == team).mean() * 100) if not team_venue_matches.empty else 0.0

    # Head-to-head dominance.
    h2h = matches[
        ((matches["team1"] == team) & (matches["team2"] == opponent))
        | ((matches["team1"] == opponent) & (matches["team2"] == team))
    ]
    h2h_wins = int((h2h["winner"] == team).sum()) if not h2h.empty else 0
    h2h_total = int(len(h2h))
    h2h_ratio = round((h2h_wins / h2h_total) * 100, 1) if h2h_total > 0 else 50.0

    # Toss impact analysis for selected team.
    team_matches = team_match_subset(matches, team)
    bat_first_wins = 0
    bat_first_total = 0
    chase_wins = 0
    chase_total = 0

    if not team_matches.empty:
        for _, row in team_matches.iterrows():
            first_team = batting_first_team(row)
            batted_first = first_team == team
            won = row["winner"] == team
            if batted_first:
                bat_first_total += 1
                bat_first_wins += int(won)
            else:
                chase_total += 1
                chase_wins += int(won)

    bat_first_win_pct = round((bat_first_wins / bat_first_total) * 100, 1) if bat_first_total > 0 else 0.0
    chase_win_pct = round((chase_wins / chase_total) * 100, 1) if chase_total > 0 else 0.0

    # Team strength comparison.
    team_bat_idx = team_batting_index(deliveries, team)
    opp_bat_idx = team_batting_index(deliveries, opponent)
    team_bowl_idx = team_bowling_index(deliveries, team)
    opp_bowl_idx = team_bowling_index(deliveries, opponent)

    batting_vs_opp_bowling = round(team_bat_idx - opp_bowl_idx, 2)
    opp_batting_vs_team_bowling = round(opp_bat_idx - team_bowl_idx, 2)

    # Upset probability indicator based on points table rank.
    points = build_points_table(matches)
    rank_team = int(points[points["Team"] == team]["Rank"].iloc[0]) if team in points["Team"].values else 999
    rank_opp = int(points[points["Team"] == opponent]["Rank"].iloc[0]) if opponent in points["Team"].values else 999

    favourite = team if rank_team < rank_opp else opponent
    underdog = opponent if favourite == team else team

    upset_prob = compute_upset_probability(
        matches=matches,
        deliveries=deliveries,
        favourite_team=favourite,
        underdog_team=underdog,
        toss_winner=toss_winner or team,
        toss_bat_first=1 if toss_decision == "bat" else 0,
        is_knockout=0,
    )

    # Phase-wise run scoring efficiency.
    def phase_run_rates(team_name: str) -> dict[str, float]:
        subset = deliveries[deliveries["batting_team"] == team_name]
        if subset.empty:
            return {"Powerplay": 0.0, "Middle": 0.0, "Death": 0.0}

        powerplay = subset[subset["over_num"] <= 5]
        middle = subset[(subset["over_num"] >= 6) & (subset["over_num"] <= 14)]
        death = subset[subset["over_num"] >= 15]

        return {
            "Powerplay": float(powerplay["total_runs"].mean() * 6) if not powerplay.empty else 0.0,
            "Middle": float(middle["total_runs"].mean() * 6) if not middle.empty else 0.0,
            "Death": float(death["total_runs"].mean() * 6) if not death.empty else 0.0,
        }

    team_phase = phase_run_rates(team)
    opp_phase = phase_run_rates(opponent)
    phase_efficiency = [
        {
            "phase": phase,
            "teamRunRate": round(team_phase[phase], 2),
            "opponentRunRate": round(opp_phase[phase], 2),
        }
        for phase in ["Powerplay", "Middle", "Death"]
    ]

    # Bowling pressure metric.
    bowl_subset = deliveries[deliveries["bowling_team"] == team]
    dot_pct = float((bowl_subset["total_runs"] == 0).mean() * 100) if not bowl_subset.empty else 0.0
    wicket_freq = float(bowl_subset["is_wicket_int"].mean() * 100) if not bowl_subset.empty else 0.0

    # Qualification probability from points + NRR blend.
    qualification_pct = 0.0
    if not points.empty and team in points["Team"].values:
        top = points.head(10).copy()
        max_pts = float(top["Pts"].max()) if float(top["Pts"].max()) > 0 else 1.0
        top["qual_pct"] = ((top["Pts"] / max_pts * 72) + (top["NRR"].rank(pct=True) * 28)).clip(0, 100)
        row = top[top["Team"] == team]
        qualification_pct = float(row["qual_pct"].iloc[0]) if not row.empty else 0.0

    # Match win probability derived from already loaded dataframes.
    prediction_payload = build_match_prediction_payload(
        matches=matches,
        deliveries=deliveries,
        team_a=team,
        team_b=opponent,
        toss_winner=toss_winner or team,
        toss_decision=toss_decision,
        is_knockout=0,
        venue=venue,
    )
    win_prob = build_analyst_win_probability_payload(prediction_payload)

    return {
        "matchWinProbability": win_prob,
        "expectedFirstInningsScore": {
            "mean": round(expected_score, 1),
            "q25": round(score_q25, 1),
            "q75": round(score_q75, 1),
            "samples": int(len(expected_pool)),
        },
        "venuePerformanceIndex": {
            "team": team,
            "venue": normalize_venue_name(venue) or "All venues",
            "winPct": round(venue_win_pct, 1),
            "matches": int(len(team_venue_matches)),
        },
        "headToHeadDominance": {
            "team": team,
            "opponent": opponent,
            "wins": h2h_wins,
            "matches": h2h_total,
            "winPct": h2h_ratio,
        },
        "tossImpactAnalysis": {
            "batFirstWinPct": bat_first_win_pct,
            "chasingWinPct": chase_win_pct,
            "batFirstMatches": bat_first_total,
            "chasingMatches": chase_total,
        },
        "teamStrengthComparison": {
            "battingIndex": round(team_bat_idx, 2),
            "opponentBowlingIndex": round(opp_bowl_idx, 2),
            "differential": batting_vs_opp_bowling,
            "opponentBattingIndex": round(opp_bat_idx, 2),
            "teamBowlingIndex": round(team_bowl_idx, 2),
            "reverseDifferential": opp_batting_vs_team_bowling,
        },
        "upsetProbabilityIndicator": {
            "favourite": favourite,
            "underdog": underdog,
            "upsetPct": round(upset_prob * 100, 1),
            "riskLevel": "HIGH RISK" if upset_prob >= 0.40 else "Moderate" if upset_prob >= 0.25 else "Low",
        },
        "phaseWiseRunScoringEfficiency": phase_efficiency,
        "bowlingPressureMetric": {
            "dotBallPct": round(dot_pct, 2),
            "wicketFrequencyPct": round(wicket_freq, 2),
            "pressureScore": round((dot_pct * 0.6) + (wicket_freq * 0.4), 2),
        },
        "qualificationProbability": {
            "team": team,
            "probabilityPct": round(qualification_pct, 1),
        },
    }


@app.post("/predict/upset")
def predict_upset(req: UpsetRequest) -> dict[str, Any]:
    matches = load_matches_frame()
    deliveries = load_deliveries_frame()

    upset_prob = compute_upset_probability(
        matches=matches,
        deliveries=deliveries,
        favourite_team=req.favourite_team,
        underdog_team=req.underdog_team,
        toss_winner=req.toss_winner,
        toss_bat_first=req.toss_bat_first,
        is_knockout=req.is_knockout,
    )

    return {
        "favouriteTeam": req.favourite_team,
        "underdogTeam": req.underdog_team,
        "upsetProbability": round(upset_prob * 100, 1),
        "riskLevel": "HIGH RISK" if upset_prob > 0.35 else "Normal",
    }


@app.get("/ml/player-clusters")
def get_player_clusters() -> dict[str, Any]:
    path = os.path.join(RESULTS_DIR, "player_clusters.csv")
    frame = read_csv_if_exists(path)
    if frame.empty:
        return {"available": False, "clusters": [], "topByType": {}}

    keep_cols = [
        "player_name",
        "player_type",
        "cluster",
        "total_runs",
        "strike_rate_live",
        "wickets",
        "economy_live",
    ]
    present = [col for col in keep_cols if col in frame.columns]
    base = frame[present].copy()

    top_by_type: dict[str, list[dict[str, Any]]] = {}
    if "player_type" in base.columns:
        for player_type, group in base.groupby("player_type"):
            top_by_type[str(player_type)] = (
                group.sort_values("total_runs", ascending=False)
                .head(10)
                .to_dict(orient="records")
            )

    return {
        "available": True,
        "clusters": base.to_dict(orient="records"),
        "topByType": top_by_type,
    }


@app.get("/ml/association-rules")
def get_association_rules() -> dict[str, Any]:
    path = os.path.join(RESULTS_DIR, "association_rules.csv")
    frame = read_csv_if_exists(path)
    if frame.empty:
        return {"available": False, "rules": []}

    rules = (
        frame[frame["consequents"].astype(str).str.contains("won", case=False, na=False)]
        .sort_values("lift", ascending=False)
        .head(30)
        .copy()
    )
    if rules.empty:
        return {"available": True, "rules": []}

    rules["confidence_pct"] = (as_numeric(rules["confidence"], 0) * 100).round(1)
    rules["support_pct"] = (as_numeric(rules["support"], 0) * 100).round(1)
    rules["lift"] = as_numeric(rules["lift"], 0).round(3)

    return {
        "available": True,
        "rules": rules[["antecedents", "consequents", "support_pct", "confidence_pct", "lift"]].to_dict(orient="records"),
    }


@app.get("/optimization/teams")
def get_optimization_teams() -> dict[str, list[str]]:
    teams = pd.read_sql(
        "SELECT DISTINCT country FROM silver.clean_players WHERE country IS NOT NULL ORDER BY country",
        engine,
    )
    team_list = [t for t in teams["country"].astype(str).tolist() if t and t.lower() != "nan"]
    return {"teams": ["All Teams"] + team_list}


@app.get("/optimization/optimal-xi")
def optimization_optimal_xi(country: str = "All Teams") -> dict[str, Any]:
    try:
        try:
            from ml.optimizer import select_optimal_xi
        except Exception:
            from src.ml.optimizer import select_optimal_xi

        selected_country = None if country == "All Teams" else country
        xi = select_optimal_xi(selected_country)
        if "role" in xi.columns:
            role_dist = xi["role"].value_counts().reset_index()
            role_dist.columns = ["role", "count"]
        else:
            role_dist = pd.DataFrame(columns=["role", "count"])

        return {
            "xi": xi.to_dict(orient="records"),
            "roleDistribution": role_dist.to_dict(orient="records"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/optimization/batting-order")
def optimization_batting_order(country: str = "All Teams") -> dict[str, Any]:
    try:
        try:
            from ml.optimizer import optimize_batting_order
        except Exception:
            from src.ml.optimizer import optimize_batting_order

        selected_country = None if country == "All Teams" else country
        order_df = optimize_batting_order(selected_country)
        return {"battingOrder": order_df.to_dict(orient="records")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/optimization/shap")
def optimization_get_shap() -> dict[str, Any]:
    path = os.path.join(RESULTS_DIR, "shap_importance.csv")
    frame = read_csv_if_exists(path)
    if frame.empty:
        return {"available": False, "shap": []}

    frame["SHAP_Value"] = as_numeric(frame.get("SHAP_Value", pd.Series(index=frame.index)), 0)
    return {"available": True, "shap": frame.to_dict(orient="records")}


@app.post("/optimization/shap/compute")
def optimization_compute_shap() -> dict[str, Any]:
    try:
        try:
            from ml.optimizer import compute_shap_importance
        except Exception:
            from src.ml.optimizer import compute_shap_importance

        shap_df = compute_shap_importance()
        if shap_df.empty:
            raise HTTPException(status_code=500, detail="SHAP computation returned no data")
        return {"available": True, "shap": shap_df.to_dict(orient="records")}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
