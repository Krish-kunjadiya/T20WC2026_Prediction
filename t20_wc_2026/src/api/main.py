"""FastAPI backend for ML predictions and analytics metadata."""

from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
import os
import pickle
import re
import time
from contextvars import ContextVar
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


@app.middleware("http")
async def request_gender_middleware(request, call_next):
    """Store request gender selector in context for downstream data/model filtering."""
    token = _REQUEST_GENDER.set(
        normalize_gender_value(request.query_params.get("gender"), default=normalize_gender_value(DEFAULT_GENDER, "male"))
    )
    try:
        return await call_next(request)
    finally:
        _REQUEST_GENDER.reset(token)

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
DEFAULT_GENDER = os.getenv("DEFAULT_GENDER", "male")
_REQUEST_GENDER: ContextVar[str] = ContextVar("request_gender", default=DEFAULT_GENDER)


def normalize_gender_value(value: str | None, default: str = "all") -> str:
    """Normalize user-provided gender token to male/female/all."""
    raw = str(value or "").strip().lower()
    if raw in {"male", "men", "man", "m", "boys"}:
        return "male"
    if raw in {"female", "women", "woman", "f", "girls"}:
        return "female"
    if raw in {"all", "both", "mixed", "any", ""}:
        return default
    return default


def infer_gender_from_text(*texts: str) -> str:
    """Best-effort gender inference from free text (event/team labels)."""
    blob = " ".join(str(t or "") for t in texts).lower()
    if any(token in blob for token in ["women", "female", "girls"]):
        return "female"
    if any(token in blob for token in ["men", "male", "boys"]):
        return "male"
    return "unknown"


def get_request_gender() -> str:
    """Resolve request-scoped gender from middleware context."""
    return normalize_gender_value(_REQUEST_GENDER.get(), default=normalize_gender_value(DEFAULT_GENDER, "male"))


def _suffix_filename_with_gender(filename: str, gender: str) -> str:
    stem, ext = os.path.splitext(filename)
    return f"{stem}_{gender}{ext}"


def load_model_for_gender(filename: str, gender: str) -> Any:
    """Load gender-specific model if present, fallback to generic model."""
    g = normalize_gender_value(gender, default="all")
    if g in {"male", "female"}:
        gender_file = _suffix_filename_with_gender(filename, g)
        model = load_model(gender_file)
        if model is not None:
            return model
    return load_model(filename)


def read_csv_for_gender(filename: str, gender: str) -> pd.DataFrame:
    """Read gender-specific result CSV if present, fallback to generic CSV."""
    g = normalize_gender_value(gender, default="all")
    if g in {"male", "female"}:
        gender_path = os.path.join(RESULTS_DIR, _suffix_filename_with_gender(filename, g))
        frame = read_csv_if_exists(gender_path)
        if not frame.empty:
            return frame
    return read_csv_if_exists(os.path.join(RESULTS_DIR, filename))


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


def _normalize_text_token(value: str | None) -> str:
    """Normalize free text into an alphanumeric comparison token."""
    token = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", token)


def _split_venue_city(raw_venue: str | None, raw_city: str | None) -> tuple[str, str]:
    """Split a venue string into stadium/city components using both venue and city fields."""
    venue_text = " ".join(str(raw_venue or "").split()).strip()
    city_text = " ".join(str(raw_city or "").split()).strip()

    stadium = venue_text
    city_from_venue = ""
    if "," in venue_text:
        parts = [part.strip() for part in venue_text.split(",") if part.strip()]
        if parts:
            stadium = parts[0]
            if len(parts) > 1:
                city_from_venue = parts[-1]

    city_value = city_text if city_text.lower() not in {"", "unknown", "nan", "none", "null"} else city_from_venue
    return (stadium or venue_text), city_value


def _majority_city_name(city_values: list[str]) -> str:
    """Pick a canonical city label using frequency and fuzzy clustering for near-duplicates."""
    groups: list[dict[str, Any]] = []
    for city in city_values:
        clean_city = " ".join(str(city or "").split()).strip()
        if not clean_city:
            continue
        token = _normalize_text_token(clean_city).replace(" ", "")
        if not token:
            continue

        matched_group = None
        for group in groups:
            ratio = SequenceMatcher(None, token, group["token"]).ratio()
            if ratio >= 0.88:
                matched_group = group
                break

        if matched_group is None:
            groups.append({"token": token, "values": [clean_city]})
        else:
            matched_group["values"].append(clean_city)

    if not groups:
        return ""

    best_group = max(groups, key=lambda g: len(g["values"]))
    city_counts = Counter(best_group["values"])
    return city_counts.most_common(1)[0][0]


def canonicalize_venue_columns(matches: pd.DataFrame) -> pd.DataFrame:
    """Create canonical venue labels to collapse duplicates and city spelling variants."""
    if matches.empty:
        return matches

    frame = matches.copy()
    stadium_values_by_key: dict[str, list[str]] = defaultdict(list)
    city_values_by_key: dict[str, list[str]] = defaultdict(list)

    for _, row in frame.iterrows():
        stadium_raw, city_raw = _split_venue_city(row.get("venue"), row.get("city"))
        key = _normalize_text_token(stadium_raw or row.get("venue"))
        if not key:
            continue
        if stadium_raw:
            stadium_values_by_key[key].append(stadium_raw)
        if city_raw:
            city_values_by_key[key].append(city_raw)

    stadium_by_key: dict[str, str] = {}
    for key, names in stadium_values_by_key.items():
        counts = Counter([" ".join(str(name).split()).strip() for name in names if str(name).strip()])
        if not counts:
            stadium_by_key[key] = key.title()
            continue

        top_frequency = counts.most_common(1)[0][1]
        candidates = [name for name, freq in counts.items() if freq == top_frequency]
        stadium_by_key[key] = sorted(candidates, key=lambda n: (-len(n), n.lower()))[0]

    city_by_key: dict[str, str] = {
        key: _majority_city_name(values) for key, values in city_values_by_key.items()
    }

    venue_keys: list[str] = []
    canonical_venues: list[str] = []
    canonical_cities: list[str] = []

    for _, row in frame.iterrows():
        stadium_raw, city_raw = _split_venue_city(row.get("venue"), row.get("city"))
        key = _normalize_text_token(stadium_raw or row.get("venue"))
        venue_keys.append(key)

        stadium_name = stadium_by_key.get(key, stadium_raw or " ".join(str(row.get("venue") or "").split()).strip())
        city_name = city_by_key.get(key, city_raw)
        city_name = " ".join(str(city_name or "").split()).strip()

        canonical_cities.append(city_name)
        if city_name and city_name.lower() not in {"unknown", "nan", "none", "null"}:
            canonical_venues.append(f"{stadium_name}, {city_name}")
        else:
            canonical_venues.append(stadium_name)

    frame["venue_key"] = venue_keys
    frame["venue_canonical"] = pd.Series(canonical_venues, index=frame.index)
    frame["city_canonical"] = pd.Series(canonical_cities, index=frame.index)
    return frame


def normalize_venue_name(venue: str | None) -> str:
    """Normalize venue label from UI selectors."""
    raw = " ".join(str(venue or "").split()).strip()
    if not raw or raw.lower() in {"neutral venue", "all venues"}:
        return ""
    return raw


def list_unique_venues(matches: pd.DataFrame) -> list[str]:
    """Return sorted canonical venue options for selectors."""
    if matches.empty:
        return ["Neutral Venue"]

    venue_col = "venue_canonical" if "venue_canonical" in matches.columns else "venue"
    venues = sorted(
        {
            str(v).strip()
            for v in matches.get(venue_col, pd.Series(dtype=object)).dropna().astype(str).tolist()
            if str(v).strip()
        }
    )
    if "Neutral Venue" not in venues:
        venues.append("Neutral Venue")
    return venues


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

    gender_raw = matches.get("gender", pd.Series(["unknown"] * len(matches), index=matches.index))
    matches["gender"] = gender_raw.fillna("").astype(str).str.strip().str.lower()
    matches["gender"] = matches["gender"].apply(lambda g: normalize_gender_value(g, default="unknown"))

    unknown_mask = matches["gender"] == "unknown"
    if unknown_mask.any():
        inferred = matches.apply(
            lambda row: infer_gender_from_text(
                row.get("stage", ""),
                row.get("tournament_phase", ""),
                row.get("team1", ""),
                row.get("team2", ""),
            ),
            axis=1,
        )
        matches.loc[unknown_mask & inferred.isin(["male", "female"]), "gender"] = inferred[unknown_mask & inferred.isin(["male", "female"])]

    matches = canonicalize_venue_columns(matches)

    return matches


def _filter_matches_by_gender(matches: pd.DataFrame, gender: str | None = None) -> pd.DataFrame:
    """Filter matches by normalized gender, fallback safely when tags are unavailable."""
    if matches.empty:
        return matches

    resolved_gender = normalize_gender_value(gender or get_request_gender(), default="all")
    if resolved_gender not in {"male", "female"}:
        return matches

    if "gender" not in matches.columns:
        return matches

    valid_values = set(matches["gender"].dropna().astype(str).unique().tolist())
    if not ({"male", "female"} & valid_values):
        return matches

    return matches[matches["gender"] == resolved_gender].copy()


def load_matches_frame(gender: str | None = None) -> pd.DataFrame:
    """Load and normalize clean matches table using in-memory cache."""
    frame = _get_cached_frame("clean_matches", "SELECT * FROM silver.clean_matches", _normalize_matches_frame)
    filtered = _filter_matches_by_gender(frame, gender)
    return filtered.copy(deep=False)


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
    if "gender" in deliveries.columns:
        deliveries["gender"] = deliveries["gender"].fillna("").astype(str).str.strip().str.lower()
        deliveries["gender"] = deliveries["gender"].apply(lambda g: normalize_gender_value(g, default="unknown"))
    return deliveries


def load_deliveries_frame(gender: str | None = None, matches: pd.DataFrame | None = None) -> pd.DataFrame:
    """Load and normalize clean deliveries table using in-memory cache."""
    frame = _get_cached_frame("clean_deliveries", "SELECT * FROM silver.clean_deliveries", _normalize_deliveries_frame)

    resolved_gender = normalize_gender_value(gender or get_request_gender(), default="all")
    if resolved_gender not in {"male", "female"}:
        return frame.copy(deep=False)

    if "gender" in frame.columns:
        valid_values = set(frame["gender"].dropna().astype(str).unique().tolist())
        if {"male", "female"} & valid_values:
            return frame[frame["gender"] == resolved_gender].copy(deep=False)

    if matches is None:
        matches = load_matches_frame(resolved_gender)
    if matches.empty:
        return frame.iloc[0:0].copy()

    allowed_match_ids = set(matches["match_id"].astype(str).tolist())
    return frame[frame["match_id"].astype(str).isin(allowed_match_ids)].copy(deep=False)


def _normalize_players_frame(players: pd.DataFrame) -> pd.DataFrame:
    """Normalize clean players frame."""
    if players.empty:
        return players

    players["player_name"] = players["player_name"].fillna("").astype(str)
    players["country"] = players["country"].fillna("").astype(str)
    players["role"] = players.get("role", "Unknown").fillna("Unknown").astype(str)
    if "gender" in players.columns:
        players["gender"] = players["gender"].fillna("").astype(str).str.strip().str.lower()
        players["gender"] = players["gender"].apply(lambda g: normalize_gender_value(g, default="unknown"))

    for col in ["runs", "batting_avg", "strike_rate", "wickets", "bowling_avg", "economy", "matches"]:
        players[col] = as_numeric(players.get(col, pd.Series(index=players.index)), 0)
    return players


def load_players_frame(gender: str | None = None, matches: pd.DataFrame | None = None, deliveries: pd.DataFrame | None = None) -> pd.DataFrame:
    """Load and normalize clean players table using in-memory cache."""
    frame = _get_cached_frame("clean_players", "SELECT * FROM silver.clean_players", _normalize_players_frame)

    resolved_gender = normalize_gender_value(gender or get_request_gender(), default="all")
    if resolved_gender not in {"male", "female"}:
        return frame.copy(deep=False)

    if "gender" in frame.columns:
        valid_values = set(frame["gender"].dropna().astype(str).unique().tolist())
        if {"male", "female"} & valid_values:
            return frame[frame["gender"] == resolved_gender].copy(deep=False)

    # Fallback for legacy tables without gender: infer from participation in filtered matches.
    if deliveries is None:
        if matches is None:
            matches = load_matches_frame(resolved_gender)
        deliveries = load_deliveries_frame(resolved_gender, matches=matches)

    if deliveries.empty:
        return frame.iloc[0:0].copy()

    participants = set(deliveries["batsman"].dropna().astype(str)) | set(deliveries["bowler"].dropna().astype(str))
    return frame[frame["player_name"].astype(str).isin(participants)].copy(deep=False)


def filter_matches_by_venue(matches: pd.DataFrame, venue: str | None, strict: bool = False) -> pd.DataFrame:
    """Filter matches by venue; strict mode returns empty frame when no match is found."""
    venue_norm = normalize_venue_name(venue)
    if not venue_norm or matches.empty:
        return matches

    venue_col = "venue_canonical" if "venue_canonical" in matches.columns else "venue"
    venue_series = matches.get(venue_col, pd.Series(index=matches.index, dtype=object)).fillna("").astype(str)
    normalized_series = venue_series.str.lower().str.strip()
    target = venue_norm.lower().strip()

    exact_mask = normalized_series == target
    if exact_mask.any():
        return matches[exact_mask].copy()

    target_stadium = target.split(",", 1)[0].strip()
    contains_mask = normalized_series.str.contains(target_stadium, regex=False)
    filtered = matches[contains_mask].copy()
    if not filtered.empty:
        return filtered

    return matches.iloc[0:0].copy() if strict else matches


def canonical_team_pair(team_a: str, team_b: str) -> tuple[str, str]:
    """Return a deterministic ordering for team pairs so A-vs-B equals B-vs-A."""
    a = str(team_a or "").strip()
    b = str(team_b or "").strip()
    if not a or not b:
        return a, b
    ordered = sorted([a, b], key=lambda value: value.lower())
    return ordered[0], ordered[1]


def normalize_toss_result_filter(value: str | None) -> str:
    """Normalize toss result filter token."""
    raw = str(value or "all").strip().lower()
    if raw in {"won", "win", "toss_won"}:
        return "won"
    if raw in {"lost", "lose", "toss_lost"}:
        return "lost"
    return "all"


def normalize_toss_decision_filter(value: str | None) -> str:
    """Normalize toss decision filter token."""
    raw = str(value or "any").strip().lower()
    if raw in {"bat", "batting", "batted"}:
        return "bat"
    if raw in {"field", "bowl", "bowling"}:
        return "field"
    return "any"


def apply_analyst_match_filters(
    matches: pd.DataFrame,
    team: str,
    opponent: str,
    venue: str | None,
    use_venue_filter: bool,
    use_toss_filter: bool,
    toss_result_filter: str,
    toss_decision_filter: str,
) -> pd.DataFrame:
    """Apply optional analyst filters over an already gender-scoped matches frame."""
    if matches.empty:
        return matches

    filtered = matches[
        ((matches["team1"] == team) & (matches["team2"] == opponent))
        | ((matches["team1"] == opponent) & (matches["team2"] == team))
    ].copy()

    if filtered.empty:
        return filtered

    if use_venue_filter:
        filtered = filter_matches_by_venue(filtered, venue, strict=True)

    if filtered.empty:
        return filtered

    if use_toss_filter:
        toss_result = normalize_toss_result_filter(toss_result_filter)
        toss_decision = normalize_toss_decision_filter(toss_decision_filter)

        if toss_result == "won":
            filtered = filtered[filtered["toss_winner"] == team]
        elif toss_result == "lost":
            filtered = filtered[filtered["toss_winner"] != team]

        if not filtered.empty and toss_decision in {"bat", "field"}:
            filtered = filtered[filtered["toss_decision"].astype(str).str.lower() == toss_decision]

    return filtered.copy()


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


def compute_qualification_probability(points: pd.DataFrame, team: str, playoff_slots: int = 4) -> float:
    """Estimate playoff qualification probability from current rank, points, and NRR cushion."""
    if points.empty or team not in points.get("Team", pd.Series(dtype=object)).astype(str).values:
        return 0.0

    slots = max(1, int(playoff_slots))
    table = points.copy()
    table["Rank"] = as_numeric(table.get("Rank", pd.Series(index=table.index)), 999).astype(int)
    table["Pts"] = as_numeric(table.get("Pts", pd.Series(index=table.index)), 0)
    table["NRR"] = as_numeric(table.get("NRR", pd.Series(index=table.index)), 0)

    row = table[table["Team"].astype(str) == str(team)].head(1)
    if row.empty:
        return 0.0

    rank = int(row.iloc[0]["Rank"])
    pts = float(row.iloc[0]["Pts"])
    nrr = float(row.iloc[0]["NRR"])

    playoff_band = table.nsmallest(slots, "Rank")
    cutoff_pts = float(playoff_band["Pts"].min()) if not playoff_band.empty else pts
    cutoff_nrr = float(playoff_band["NRR"].min()) if not playoff_band.empty else 0.0

    if rank <= slots:
        base = 68.0 + max(0, slots - rank) * 7.0
        base += max(0.0, pts - cutoff_pts) * 5.0
    else:
        gap = rank - slots
        base = 48.0 - (gap * 11.0)
        base += max(0.0, pts - cutoff_pts) * 6.5

    base += (nrr - cutoff_nrr) * 14.0
    return round(float(clamp(base, 1.0, 99.0)), 1)


def compute_upset_probability(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    favourite_team: str,
    underdog_team: str,
    toss_winner: str,
    toss_bat_first: int,
    is_knockout: int,
    gender: str | None = None,
) -> float:
    """Compute upset probability with model if available, heuristic fallback otherwise."""
    artifact = load_model_for_gender("upset_detector_lr.pkl", gender or get_request_gender())

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
    gender: str | None = None


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
    gender: str | None = None


class AnalystWinRequest(BaseModel):
    team_a: str
    team_b: str
    toss_winner: str
    toss_decision: str = "bat"
    venue: str = "Neutral Venue"
    is_knockout: int = 0
    gender: str | None = None
    use_venue_filter: bool = False
    use_toss_filter: bool = False
    toss_result_filter: str = "all"
    toss_decision_filter: str = "any"


def build_match_prediction_payload(
    matches: pd.DataFrame,
    deliveries: pd.DataFrame,
    team_a: str,
    team_b: str,
    toss_winner: str,
    toss_decision: str = "bat",
    is_knockout: int = 0,
    venue: str = "Neutral Venue",
    gender: str | None = None,
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

    artifact = load_model_for_gender("match_outcome_xgb.pkl", gender or get_request_gender())
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
    selected_gender = normalize_gender_value(req.gender or get_request_gender(), default=normalize_gender_value(DEFAULT_GENDER, "male"))
    team_a, team_b = canonical_team_pair(req.team_a, req.team_b)
    toss_winner = req.toss_winner if req.toss_winner in {team_a, team_b} else team_a

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)

    return build_match_prediction_payload(
        matches=matches,
        deliveries=deliveries,
        team_a=team_a,
        team_b=team_b,
        toss_winner=toss_winner,
        toss_decision=req.toss_decision,
        is_knockout=req.is_knockout,
        venue=req.venue,
        gender=selected_gender,
    )


@app.post("/predict/score")
def predict_score(req: ScoreRequest, gender: str | None = None) -> dict[str, Any]:
    if req.sixes + req.fours > req.total_balls:
        raise HTTPException(status_code=422, detail="Sixes + fours cannot exceed total balls")
    if req.pp_runs > req.total_balls * 2:
        raise HTTPException(status_code=422, detail="Powerplay runs are unrealistically high for the entered state")

    selected_gender = normalize_gender_value(gender or get_request_gender(), default=normalize_gender_value(DEFAULT_GENDER, "male"))
    artifact = load_model_for_gender("score_predictor_lgbm.pkl", selected_gender)
    if not artifact:
        raise HTTPException(status_code=500, detail="Score model not found")

    model = artifact["model"]
    feat_cols = artifact["features"]

    payload = req.model_dump()
    payload["pp_run_rate"] = req.pp_runs / 6.0
    payload["boundary_pct"] = (req.sixes + req.fours) / max(req.total_balls, 1)

    X = pd.DataFrame([payload]).reindex(columns=feat_cols, fill_value=0)
    model_pred = float(model.predict(X)[0])

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)
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
    matches = load_matches_frame(get_request_gender())
    team_values = pd.concat(
        [
            matches.get("team1", pd.Series(dtype=object)),
            matches.get("team2", pd.Series(dtype=object)),
        ],
        ignore_index=True,
    )
    teams = sorted({str(t).strip() for t in team_values.dropna().astype(str).tolist() if str(t).strip()})
    return {"teams": teams}


@app.get("/venues")
def get_venues() -> dict[str, list[str]]:
    matches = load_matches_frame(get_request_gender())
    return {"venues": list_unique_venues(matches)}


@app.get("/players/{country}")
def get_players(country: str) -> dict[str, Any]:
    selected_gender = get_request_gender()
    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    players = load_players_frame(selected_gender, matches=matches, deliveries=deliveries)

    if players.empty:
        frame = pd.DataFrame(columns=["player_name", "role", "runs", "batting_avg", "strike_rate", "wickets", "economy"])
    else:
        frame = players.copy()
        frame["country"] = frame.get("country", pd.Series(dtype=object)).astype(str)
        frame = frame[frame["country"].str.lower() == country.strip().lower()].copy()
        if "runs" in frame.columns:
            frame["runs"] = as_numeric(frame["runs"], default=0)
            frame = frame.sort_values("runs", ascending=False)
        frame = frame.head(20)

    required_cols = ["player_name", "role", "runs", "batting_avg", "strike_rate", "wickets", "economy"]
    for col in required_cols:
        if col not in frame.columns:
            frame[col] = pd.NA

    return {"players": frame.to_dict(orient="records")}


@app.get("/strategist/overview")
def strategist_overview() -> dict[str, Any]:
    matches = load_matches_frame()
    points = build_points_table(matches)

    qual_data: list[dict[str, Any]] = []
    if not points.empty:
        table = points.copy()
        table["QualPct"] = table["Team"].apply(lambda team_name: compute_qualification_probability(points, str(team_name), playoff_slots=4))
        qual_data = [
            {
                "team": str(row["Team"]),
                "qualPct": float(row["QualPct"]),
                "pts": int(row["Pts"]),
                "nrr": float(row["NRR"]),
            }
            for _, row in table.head(10).iterrows()
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


@app.get("/strategist/team-insights")
def strategist_team_insights(team: str, opponent: str, venue: str = "Neutral Venue") -> dict[str, Any]:
    """Team-vs-opponent strategist payload for qualification and tactical planning."""
    selected_gender = get_request_gender()
    team = str(team or "").strip()
    opponent = str(opponent or "").strip()

    if not team or not opponent or team == opponent:
        raise HTTPException(status_code=422, detail="team and opponent must be different non-empty values")

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)

    if matches.empty:
        raise HTTPException(status_code=404, detail="No match data available")

    team_matches = team_match_subset(matches, team)
    opponent_matches = team_match_subset(matches, opponent)
    pair_matches = matches[
        ((matches["team1"] == team) & (matches["team2"] == opponent))
        | ((matches["team1"] == opponent) & (matches["team2"] == team))
    ].copy()

    points = build_points_table(matches)
    if points.empty or team not in points["Team"].values:
        raise HTTPException(status_code=404, detail="Team not found in points table")

    current_row = points[points["Team"] == team].iloc[0]
    current_rank = int(current_row["Rank"])
    current_pts = int(current_row["Pts"])
    current_nrr = float(current_row["NRR"])
    qualification_pct = compute_qualification_probability(points, team, playoff_slots=4)

    top_four = points.nsmallest(4, "Rank") if not points.empty else pd.DataFrame()
    cutoff_pts = int(top_four["Pts"].min()) if not top_four.empty else current_pts

    def phase_run_rates(side: str) -> dict[str, float]:
        if deliveries.empty:
            return {"powerplay": 0.0, "middle": 0.0, "death": 0.0}

        side_deliveries = deliveries[deliveries["batting_team"] == side]
        if side_deliveries.empty:
            return {"powerplay": 0.0, "middle": 0.0, "death": 0.0}

        def rr(frame: pd.DataFrame) -> float:
            if frame.empty:
                return 0.0
            return round(float(frame["total_runs"].sum() * 6.0 / max(len(frame), 1)), 2)

        powerplay = side_deliveries[side_deliveries["over_num"] <= 5]
        middle = side_deliveries[(side_deliveries["over_num"] >= 6) & (side_deliveries["over_num"] <= 14)]
        death = side_deliveries[side_deliveries["over_num"] >= 15]

        return {
            "powerplay": rr(powerplay),
            "middle": rr(middle),
            "death": rr(death),
        }

    def lower_order_profile(side: str) -> tuple[float, int]:
        if deliveries.empty:
            return 0.0, 0

        side_batting = deliveries[deliveries["batting_team"] == side].copy()
        if side_batting.empty:
            return 0.0, 0

        lineup = (
            side_batting.groupby(["match_id", "inning", "batting_team", "batsman"], as_index=False)
            .agg(first_over=("over_num", "min"), first_ball=("ball_num", "min"))
            .sort_values(["match_id", "inning", "first_over", "first_ball", "batsman"], kind="stable")
        )
        lineup["batting_position"] = lineup.groupby(["match_id", "inning", "batting_team"]).cumcount() + 1

        batter_runs = (
            side_batting.groupby(["match_id", "inning", "batting_team", "batsman"], as_index=False)
            .agg(runs=("batsman_runs", "sum"))
        )

        depth = lineup.merge(batter_runs, on=["match_id", "inning", "batting_team", "batsman"], how="left")
        depth = depth[depth["batting_position"].between(6, 8)]
        if depth.empty:
            return 0.0, 0

        return round(float(depth["runs"].mean()), 2), int(len(depth))

    team_win_pct = round(float((team_matches["winner"] == team).mean() * 100), 1) if not team_matches.empty else 0.0
    recent_team_matches = team_matches.sort_values("match_date", ascending=False, kind="stable").head(5)
    recent_win_pct = round(float((recent_team_matches["winner"] == team).mean() * 100), 1) if not recent_team_matches.empty else 0.0
    h2h_win_pct = round(float((pair_matches["winner"] == team).mean() * 100), 1) if not pair_matches.empty else 0.0

    team_batting = deliveries[deliveries["batting_team"] == team].copy() if not deliveries.empty else deliveries.iloc[0:0].copy()
    innings_totals = (
        team_batting.groupby(["match_id", "inning", "batting_team"], as_index=False)
        .agg(total_runs=("total_runs", "sum"))
        if not team_batting.empty
        else pd.DataFrame(columns=["match_id", "inning", "batting_team", "total_runs"])
    )
    average_team_score = round(float(innings_totals["total_runs"].mean()), 1) if not innings_totals.empty else 0.0

    team_phase = phase_run_rates(team)
    opponent_phase = phase_run_rates(opponent)

    strategy_index = round(
        float(
            clamp(
                (team_win_pct * 0.36)
                + (recent_win_pct * 0.26)
                + (h2h_win_pct * 0.20)
                + (current_nrr * 12.0),
                0.0,
                100.0,
            )
        ),
        1,
    )

    if strategy_index >= 68:
        strategy_signal = "Strong momentum. Prioritize control and matchup execution."
    elif strategy_index >= 50:
        strategy_signal = "Balanced setup. Small tactical edges should decide outcomes."
    else:
        strategy_signal = "Pressure phase. Aggressive tactical targeting is required."

    team_bat_first = team_matches[team_matches.apply(batting_first_team, axis=1) == team] if not team_matches.empty else team_matches
    team_chasing = team_matches[team_matches.apply(batting_first_team, axis=1) != team] if not team_matches.empty else team_matches

    bat_first_win_pct = round(float((team_bat_first["winner"] == team).mean() * 100), 1) if not team_bat_first.empty else 0.0
    chasing_win_pct = round(float((team_chasing["winner"] == team).mean() * 100), 1) if not team_chasing.empty else 0.0

    innings = build_first_innings_dataset(deliveries)
    venue_norm = normalize_venue_name(venue)
    venue_matches = filter_matches_by_venue(matches, venue, strict=True) if venue_norm else matches
    if venue_matches.empty:
        venue_matches = matches
    venue_ids = set(venue_matches["match_id"].astype(str).tolist())
    venue_first_innings = (
        innings[(innings["inning"] == 1) & (innings["match_id"].astype(str).isin(venue_ids))]
        if not innings.empty
        else pd.DataFrame(columns=["total_runs"])
    )
    venue_avg_first_innings = round(float(venue_first_innings["total_runs"].mean()), 1) if not venue_first_innings.empty else 0.0

    if bat_first_win_pct == chasing_win_pct:
        recommended_toss_decision = "Bat First" if venue_avg_first_innings >= 165 else "Chase"
    else:
        bias = 3.0 if venue_avg_first_innings >= 168 else 0.0
        recommended_toss_decision = "Bat First" if (bat_first_win_pct + bias) >= chasing_win_pct else "Chase"

    weak_phase = min(opponent_phase, key=opponent_phase.get) if any(opponent_phase.values()) else "powerplay"
    spin_proxy = opponent_phase.get("middle", 0.0)
    pace_proxy = (opponent_phase.get("powerplay", 0.0) + opponent_phase.get("death", 0.0)) / 2.0
    weakness_type = "Spin" if spin_proxy <= pace_proxy else "Pace"

    opponent_chasing = opponent_matches[opponent_matches.apply(batting_first_team, axis=1) != opponent] if not opponent_matches.empty else opponent_matches
    opponent_chasing_win_pct = round(float((opponent_chasing["winner"] == opponent).mean() * 100), 1) if not opponent_chasing.empty else 0.0
    poor_chasing_record = opponent_chasing_win_pct < 45.0

    opponent_lower_avg, opponent_lower_samples = lower_order_profile(opponent)
    team_lower_avg, _ = lower_order_profile(team)
    weak_lower_order = bool(opponent_lower_samples > 0 and opponent_lower_avg < max(14.0, team_lower_avg * 0.82))

    team_bat_agg = (
        deliveries[deliveries["batting_team"] == team]
        .groupby("batsman", as_index=False)
        .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"))
        .rename(columns={"batsman": "player"})
        if not deliveries.empty
        else pd.DataFrame(columns=["player", "runs", "balls"])
    )
    team_bat_agg["strike_rate"] = (team_bat_agg["runs"] * 100.0 / team_bat_agg["balls"].replace(0, 1)).round(2) if not team_bat_agg.empty else 0

    team_bowl_agg = (
        deliveries[deliveries["bowling_team"] == team]
        .groupby("bowler", as_index=False)
        .agg(wickets=("is_wicket_int", "sum"), balls_bowled=("total_runs", "count"), runs_conceded=("total_runs", "sum"))
        .rename(columns={"bowler": "player"})
        if not deliveries.empty
        else pd.DataFrame(columns=["player", "wickets", "balls_bowled", "runs_conceded"])
    )
    team_bowl_agg["economy"] = (team_bowl_agg["runs_conceded"] * 6.0 / team_bowl_agg["balls_bowled"].replace(0, 1)).round(2) if not team_bowl_agg.empty else 0

    impact = team_bat_agg.merge(team_bowl_agg, on="player", how="outer")
    if impact.empty:
        impact = pd.DataFrame(columns=["player", "runs", "balls", "strike_rate", "wickets", "balls_bowled", "runs_conceded", "economy", "impact_score"])
    else:
        for col in ["runs", "balls", "strike_rate", "wickets", "balls_bowled", "runs_conceded", "economy"]:
            impact[col] = as_numeric(impact.get(col, pd.Series(index=impact.index)), 0)
        impact["impact_score"] = (
            (impact["runs"] * 0.22)
            + (impact["strike_rate"] * 0.08)
            + (impact["wickets"] * 18.0)
            - (impact["economy"] * 2.2)
        ).round(2)
        impact = impact.sort_values("impact_score", ascending=False, kind="stable")

    team_wins = team_matches[team_matches["winner"] == team] if not team_matches.empty else team_matches
    match_winning_counts = (
        team_wins.get("player_of_match", pd.Series(dtype=object))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    match_winning_counts = match_winning_counts[match_winning_counts != ""].value_counts()

    close_wins = team_wins[
        ((team_wins["win_by_runs"] > 0) & (team_wins["win_by_runs"] <= 15))
        | ((team_wins["win_by_wickets"] > 0) & (team_wins["win_by_wickets"] <= 4))
    ] if not team_wins.empty else team_wins
    clutch_counts = (
        close_wins.get("player_of_match", pd.Series(dtype=object))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    clutch_counts = clutch_counts[clutch_counts != ""].value_counts()

    vs_bat = (
        deliveries[(deliveries["batting_team"] == team) & (deliveries["bowling_team"] == opponent)]
        .groupby("batsman", as_index=False)
        .agg(runs_vs_opponent=("batsman_runs", "sum"), balls_vs_opponent=("batsman_runs", "count"))
        .rename(columns={"batsman": "player"})
        if not deliveries.empty
        else pd.DataFrame(columns=["player", "runs_vs_opponent", "balls_vs_opponent"])
    )
    vs_bat["strike_rate_vs_opponent"] = (
        vs_bat["runs_vs_opponent"] * 100.0 / vs_bat["balls_vs_opponent"].replace(0, 1)
    ).round(2) if not vs_bat.empty else 0

    vs_bowl = (
        deliveries[(deliveries["bowling_team"] == team) & (deliveries["batting_team"] == opponent)]
        .groupby("bowler", as_index=False)
        .agg(wickets_vs_opponent=("is_wicket_int", "sum"), balls_bowled_vs_opponent=("total_runs", "count"), runs_conceded_vs_opponent=("total_runs", "sum"))
        .rename(columns={"bowler": "player"})
        if not deliveries.empty
        else pd.DataFrame(columns=["player", "wickets_vs_opponent", "balls_bowled_vs_opponent", "runs_conceded_vs_opponent"])
    )
    vs_bowl["economy_vs_opponent"] = (
        vs_bowl["runs_conceded_vs_opponent"] * 6.0 / vs_bowl["balls_bowled_vs_opponent"].replace(0, 1)
    ).round(2) if not vs_bowl.empty else 0

    player_vs_opponent = vs_bat.merge(vs_bowl, on="player", how="outer")
    if player_vs_opponent.empty:
        player_vs_opponent = pd.DataFrame(columns=["player", "runs_vs_opponent", "wickets_vs_opponent", "matchup_score"])
    else:
        for col in [
            "runs_vs_opponent",
            "balls_vs_opponent",
            "strike_rate_vs_opponent",
            "wickets_vs_opponent",
            "balls_bowled_vs_opponent",
            "runs_conceded_vs_opponent",
            "economy_vs_opponent",
        ]:
            player_vs_opponent[col] = as_numeric(player_vs_opponent.get(col, pd.Series(index=player_vs_opponent.index)), 0)

        player_vs_opponent["matchup_score"] = (
            (player_vs_opponent["runs_vs_opponent"] * 0.18)
            + (player_vs_opponent["strike_rate_vs_opponent"] * 0.05)
            + (player_vs_opponent["wickets_vs_opponent"] * 14.0)
            - (player_vs_opponent["economy_vs_opponent"] * 1.8)
        ).round(2)
        player_vs_opponent = player_vs_opponent.sort_values("matchup_score", ascending=False, kind="stable")

    top_impact_players = [
        {
            "player": str(row["player"]),
            "impactScore": float(row["impact_score"]),
            "runs": int(row["runs"]),
            "wickets": int(row["wickets"]),
            "strikeRate": round(float(row["strike_rate"]), 2),
            "economy": round(float(row["economy"]), 2),
        }
        for _, row in impact.head(6).iterrows()
    ]

    match_winning_performances = [
        {"player": str(name), "performances": int(count)}
        for name, count in match_winning_counts.head(6).items()
    ]

    clutch_indicators: list[dict[str, Any]] = []
    for row in top_impact_players[:6]:
        player_name = str(row["player"])
        clutch = int(clutch_counts.get(player_name, 0))
        match_wins = int(match_winning_counts.get(player_name, 0))
        if clutch >= 2 or (match_wins > 0 and (clutch / max(match_wins, 1)) >= 0.4):
            indicator = "HIGH"
        elif clutch >= 1:
            indicator = "MEDIUM"
        else:
            indicator = "LOW"

        clutch_indicators.append(
            {
                "player": player_name,
                "clutchWins": clutch,
                "matchWinningPerformances": match_wins,
                "indicator": indicator,
            }
        )

    player_vs_opponent_rows = [
        {
            "player": str(row["player"]),
            "runsVsOpponent": int(row["runs_vs_opponent"]),
            "wicketsVsOpponent": int(row["wickets_vs_opponent"]),
            "strikeRateVsOpponent": round(float(row["strike_rate_vs_opponent"]), 2),
            "economyVsOpponent": round(float(row["economy_vs_opponent"]), 2),
            "matchupScore": float(row["matchup_score"]),
        }
        for _, row in player_vs_opponent.head(6).iterrows()
    ]

    scenario_templates = [
        ("winNext", "If team wins next match", 20),
        ("loseNext", "If team loses next match", -20),
        ("winBigMargin", "If team wins by big margin", 50),
    ]
    scenario_results: list[dict[str, Any]] = []
    for scenario_id, label, margin in scenario_templates:
        projected = build_projected_points_table(points, team, margin)
        if projected.empty or team not in projected["Team"].values:
            continue
        projected_row = projected[projected["Team"] == team].iloc[0]
        projected_rank = int(projected_row["Rank"])
        projected_nrr = float(projected_row["NRR"])
        projected_pts = int(projected_row["Pts"])

        scenario_results.append(
            {
                "scenarioId": scenario_id,
                "label": label,
                "projectedRank": projected_rank,
                "projectedPoints": projected_pts,
                "projectedNrr": round(projected_nrr, 3),
                "rankDelta": int(current_rank - projected_rank),
                "nrrDelta": round(projected_nrr - current_nrr, 3),
                "qualificationProbability": compute_qualification_probability(projected, team, playoff_slots=4),
            }
        )

    exploit_notes = [
        f"Opponent's weakest phase is {weak_phase.title()} (run rate {opponent_phase.get(weak_phase, 0.0)}).",
        f"Opponent appears more vulnerable to {weakness_type.lower()} pressure.",
    ]
    if poor_chasing_record:
        exploit_notes.append(f"Opponent chasing win rate is low at {opponent_chasing_win_pct}%.")
    if weak_lower_order:
        exploit_notes.append(f"Opponent lower-order average (positions 6-8) is {opponent_lower_avg}, below benchmark.")

    ai_strategy_insights: list[str] = []
    if qualification_pct >= 75:
        ai_strategy_insights.append(f"{team} is in a strong playoff position ({qualification_pct}% qualification probability). Prioritize low-risk plans.")
    elif qualification_pct >= 50:
        ai_strategy_insights.append(f"{team} remains in a competitive playoff race ({qualification_pct}%). Small NRR gains can be decisive.")
    else:
        ai_strategy_insights.append(f"{team} is under playoff pressure ({qualification_pct}%). High-impact tactical calls are required immediately.")

    ai_strategy_insights.append(
        f"Toss strategy leans to {recommended_toss_decision.lower()} based on {bat_first_win_pct}% bat-first win rate, {chasing_win_pct}% chasing win rate, and venue first-innings average {venue_avg_first_innings}."
    )
    ai_strategy_insights.append(" ".join(exploit_notes))

    if top_impact_players:
        top_player = top_impact_players[0]
        ai_strategy_insights.append(
            f"Highest impact player is {top_player['player']} (impact {top_player['impactScore']}, runs {top_player['runs']}, wickets {top_player['wickets']})."
        )

    if scenario_results:
        best_case = max(scenario_results, key=lambda item: item["qualificationProbability"])
        worst_case = min(scenario_results, key=lambda item: item["qualificationProbability"])
        ai_strategy_insights.append(
            f"Scenario spread: best case '{best_case['label']}' reaches {best_case['qualificationProbability']}% qualification chance vs {worst_case['qualificationProbability']}% in worst case."
        )

    return {
        "team": team,
        "opponent": opponent,
        "venue": venue_norm or "All venues",
        "qualificationProbability": {
            "team": team,
            "probabilityPct": qualification_pct,
            "currentRank": current_rank,
            "currentPoints": current_pts,
            "currentNrr": round(current_nrr, 3),
            "playoffCutoffPoints": cutoff_pts,
        },
        "matchStrategyOverview": {
            "overallWinPct": team_win_pct,
            "recentWinPct": recent_win_pct,
            "headToHeadWinPct": h2h_win_pct,
            "nrr": round(current_nrr, 3),
            "averageTeamScore": average_team_score,
            "powerplayRunRate": team_phase.get("powerplay", 0.0),
            "middleRunRate": team_phase.get("middle", 0.0),
            "deathRunRate": team_phase.get("death", 0.0),
            "strategyIndex": strategy_index,
            "strategySignal": strategy_signal,
        },
        "optimalTossStrategy": {
            "batFirstWinPct": bat_first_win_pct,
            "chasingWinPct": chasing_win_pct,
            "batFirstMatches": int(len(team_bat_first)),
            "chasingMatches": int(len(team_chasing)),
            "venueAvgFirstInningsScore": venue_avg_first_innings,
            "recommendedTossDecision": recommended_toss_decision,
        },
        "opponentWeaknessAnalysis": {
            "weaknessVsType": weakness_type,
            "weakPhase": weak_phase.title(),
            "phaseRunRates": {
                "powerplay": opponent_phase.get("powerplay", 0.0),
                "middle": opponent_phase.get("middle", 0.0),
                "death": opponent_phase.get("death", 0.0),
            },
            "chasingWinPct": opponent_chasing_win_pct,
            "poorChasingRecord": poor_chasing_record,
            "lowerOrderAverageRuns": opponent_lower_avg,
            "weakLowerOrder": weak_lower_order,
            "recommendedExploitation": exploit_notes,
        },
        "keyPlayerImpactAnalysis": {
            "topImpactPlayers": top_impact_players,
            "matchWinningPerformances": match_winning_performances,
            "clutchPerformanceIndicator": clutch_indicators,
            "playerVsOpponentRecord": player_vs_opponent_rows,
        },
        "scenarioSimulation": scenario_results,
        "aiStrategyInsights": ai_strategy_insights,
    }


@app.get("/coach/meta")
def coach_meta() -> dict[str, Any]:
    """Return available teams for coach analytics."""
    selected_gender = get_request_gender()
    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    players = load_players_frame(selected_gender, matches=matches, deliveries=deliveries)

    teams = sorted(
        {
            str(team).strip()
            for team in players.get("country", pd.Series(dtype=object)).dropna().astype(str).tolist()
            if str(team).strip()
        }
    )
    if not teams:
        teams = sorted(
            {
                str(team).strip()
                for team in pd.concat(
                    [
                        matches.get("team1", pd.Series(dtype=object)),
                        matches.get("team2", pd.Series(dtype=object)),
                    ],
                    ignore_index=True,
                )
                .dropna()
                .astype(str)
                .tolist()
                if str(team).strip()
            }
        )

    return {"teams": teams}


@app.get("/coach/insights")
def coach_insights(team: str, opponent: str | None = None, recent_matches: int = 5) -> dict[str, Any]:
    """Coach dashboard payload with form, phase, matchup, and XI recommendations."""
    selected_gender = get_request_gender()
    team = str(team or "").strip()
    opponent = str(opponent or "").strip()
    recent_n = int(max(3, min(int(recent_matches or 5), 12)))

    if not team:
        raise HTTPException(status_code=422, detail="team is required")

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    players = load_players_frame(selected_gender, matches=matches, deliveries=deliveries)

    team_matches = team_match_subset(matches, team).sort_values("match_date", ascending=False, kind="stable")
    recent_match_frame = team_matches.head(recent_n).copy()
    recent_ids = set(recent_match_frame.get("match_id", pd.Series(dtype=object)).astype(str).tolist())

    team_bat = deliveries[deliveries["batting_team"] == team].copy() if "batting_team" in deliveries.columns else deliveries.iloc[0:0].copy()
    team_bowl = deliveries[deliveries["bowling_team"] == team].copy() if "bowling_team" in deliveries.columns else deliveries.iloc[0:0].copy()

    recent_bat = team_bat[team_bat["match_id"].astype(str).isin(recent_ids)].copy() if recent_ids else team_bat.iloc[0:0].copy()
    recent_bowl = team_bowl[team_bowl["match_id"].astype(str).isin(recent_ids)].copy() if recent_ids else team_bowl.iloc[0:0].copy()

    # Recent form index (last N matches): batting + bowling contribution blended per player-match.
    bat_pm = pd.DataFrame(columns=["match_id", "player_name", "runs", "balls"])
    bowl_pm = pd.DataFrame(columns=["match_id", "player_name", "wickets", "runs_conceded", "balls_bowled"])

    if not recent_bat.empty:
        bat_pm = (
            recent_bat.groupby(["match_id", "batsman"], as_index=False)
            .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"))
            .rename(columns={"batsman": "player_name"})
        )

    if not recent_bowl.empty:
        bowl_pm = (
            recent_bowl.groupby(["match_id", "bowler"], as_index=False)
            .agg(
                wickets=("is_wicket_int", "sum"),
                runs_conceded=("total_runs", "sum"),
                balls_bowled=("total_runs", "count"),
            )
            .rename(columns={"bowler": "player_name"})
        )

    contrib = bat_pm.merge(bowl_pm, on=["match_id", "player_name"], how="outer")
    if contrib.empty:
        contrib = pd.DataFrame(
            columns=[
                "match_id",
                "player_name",
                "runs",
                "balls",
                "wickets",
                "runs_conceded",
                "balls_bowled",
                "form_score",
            ]
        )
    else:
        for col in ["runs", "balls", "wickets", "runs_conceded", "balls_bowled"]:
            contrib[col] = as_numeric(contrib.get(col, pd.Series(index=contrib.index)), 0)

        contrib["strike_rate"] = (contrib["runs"] * 100.0 / contrib["balls"].replace(0, 1)).round(2)
        contrib["economy"] = (contrib["runs_conceded"] * 6.0 / contrib["balls_bowled"].replace(0, 1)).round(2)
        contrib["form_score"] = (
            contrib["runs"]
            + (contrib["wickets"] * 22.0)
            + (contrib["strike_rate"] * 0.18)
            - (contrib["economy"] * 1.6)
        ).round(2)

    if not contrib.empty and not recent_match_frame.empty:
        contrib = contrib.merge(recent_match_frame[["match_id", "match_date"]], on="match_id", how="left")

    form_index = pd.DataFrame(columns=["player_name", "form_index", "matches", "total_runs", "total_wickets", "variance"])
    if not contrib.empty:
        form_index = (
            contrib.groupby("player_name", as_index=False)
            .agg(
                form_index=("form_score", "mean"),
                matches=("match_id", "nunique"),
                total_runs=("runs", "sum"),
                total_wickets=("wickets", "sum"),
                variance=("form_score", lambda s: float(s.var(ddof=0)) if len(s) > 0 else 0.0),
            )
            .sort_values(["form_index", "total_runs"], ascending=[False, False], kind="stable")
        )

    top_form = form_index.head(5).copy() if not form_index.empty else pd.DataFrame()
    top_form_players = (
        [
            {
                "player": str(row["player_name"]),
                "formIndex": round(float(row["form_index"]), 2),
                "matches": int(row["matches"]),
                "runs": int(row["total_runs"]),
                "wickets": int(row["total_wickets"]),
            }
            for _, row in top_form.iterrows()
        ]
        if not top_form.empty
        else []
    )

    # Best powerplay batter: highest strike rate in overs 1-6.
    pp = team_bat[team_bat["over_num"].between(0, 5)].copy()
    pp_stats = pd.DataFrame(columns=["player", "runs", "balls", "strikeRate"])
    if not pp.empty:
        pp_stats = (
            pp.groupby("batsman", as_index=False)
            .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"))
            .rename(columns={"batsman": "player"})
        )
        pp_stats = pp_stats[pp_stats["balls"] >= 24] if (pp_stats["balls"] >= 24).any() else pp_stats
        pp_stats["strikeRate"] = (pp_stats["runs"] * 100.0 / pp_stats["balls"].replace(0, 1)).round(2)
        pp_stats = pp_stats.sort_values(["strikeRate", "runs"], ascending=[False, False], kind="stable")

    best_powerplay = (
        {
            "player": str(pp_stats.iloc[0]["player"]),
            "strikeRate": float(pp_stats.iloc[0]["strikeRate"]),
            "runs": int(pp_stats.iloc[0]["runs"]),
            "balls": int(pp_stats.iloc[0]["balls"]),
        }
        if not pp_stats.empty
        else {"player": "N/A", "strikeRate": 0.0, "runs": 0, "balls": 0}
    )

    # Most reliable middle-order batter: highest average in overs 7-15.
    middle = team_bat[team_bat["over_num"].between(6, 14)].copy()
    middle_stats = pd.DataFrame(columns=["player", "runs", "balls", "dismissals", "average"])
    if not middle.empty:
        middle_stats = (
            middle.groupby("batsman", as_index=False)
            .agg(
                runs=("batsman_runs", "sum"),
                balls=("batsman_runs", "count"),
                dismissals=("is_wicket_int", "sum"),
            )
            .rename(columns={"batsman": "player"})
        )
        middle_stats = middle_stats[middle_stats["balls"] >= 24] if (middle_stats["balls"] >= 24).any() else middle_stats
        middle_stats["average"] = (
            middle_stats["runs"]
            / middle_stats["dismissals"].replace(0, 1)
        ).round(2)
        middle_stats = middle_stats.sort_values(["average", "runs"], ascending=[False, False], kind="stable")

    best_middle = (
        {
            "player": str(middle_stats.iloc[0]["player"]),
            "average": float(middle_stats.iloc[0]["average"]),
            "runs": int(middle_stats.iloc[0]["runs"]),
            "dismissals": int(middle_stats.iloc[0]["dismissals"]),
        }
        if not middle_stats.empty
        else {"player": "N/A", "average": 0.0, "runs": 0, "dismissals": 0}
    )

    # Best death over bowler: lowest economy in overs 16-20.
    death = team_bowl[team_bowl["over_num"] >= 15].copy()
    death_stats = pd.DataFrame(columns=["player", "runs_conceded", "balls", "wickets", "economy"])
    if not death.empty:
        death_stats = (
            death.groupby("bowler", as_index=False)
            .agg(
                runs_conceded=("total_runs", "sum"),
                balls=("total_runs", "count"),
                wickets=("is_wicket_int", "sum"),
            )
            .rename(columns={"bowler": "player"})
        )
        death_stats = death_stats[death_stats["balls"] >= 24] if (death_stats["balls"] >= 24).any() else death_stats
        death_stats["economy"] = (death_stats["runs_conceded"] * 6.0 / death_stats["balls"].replace(0, 1)).round(2)
        death_stats = death_stats.sort_values(["economy", "wickets"], ascending=[True, False], kind="stable")

    best_death_bowler = (
        {
            "player": str(death_stats.iloc[0]["player"]),
            "economy": float(death_stats.iloc[0]["economy"]),
            "wickets": int(death_stats.iloc[0]["wickets"]),
            "balls": int(death_stats.iloc[0]["balls"]),
        }
        if not death_stats.empty
        else {"player": "N/A", "economy": 0.0, "wickets": 0, "balls": 0}
    )

    # Player matchup advantage: batter success rates vs selected opponent bowlers.
    matchup_data = pd.DataFrame(columns=["batter", "bowler", "runs", "balls", "dismissals", "success_rate", "advantage_score"])
    if opponent and opponent != team:
        matchup_subset = deliveries[
            (deliveries["batting_team"] == team)
            & (deliveries["bowling_team"] == opponent)
        ].copy()
        if not matchup_subset.empty:
            matchup_data = (
                matchup_subset.groupby(["batsman", "bowler"], as_index=False)
                .agg(
                    runs=("batsman_runs", "sum"),
                    balls=("batsman_runs", "count"),
                    dismissals=("is_wicket_int", "sum"),
                )
                .rename(columns={"batsman": "batter"})
            )
            matchup_data = matchup_data[matchup_data["balls"] >= 12] if (matchup_data["balls"] >= 12).any() else matchup_data
            matchup_data["success_rate"] = (matchup_data["runs"] * 100.0 / matchup_data["balls"].replace(0, 1)).round(2)
            matchup_data["dismissal_rate"] = (matchup_data["dismissals"] * 100.0 / matchup_data["balls"].replace(0, 1)).round(2)
            matchup_data["advantage_score"] = (
                matchup_data["success_rate"] - (matchup_data["dismissal_rate"] * 1.4)
            ).round(2)
            matchup_data = matchup_data.sort_values(["advantage_score", "runs"], ascending=[False, False], kind="stable")

    matchup_advantage = (
        {
            "batter": str(matchup_data.iloc[0]["batter"]),
            "bowler": str(matchup_data.iloc[0]["bowler"]),
            "successRate": float(matchup_data.iloc[0]["success_rate"]),
            "runs": int(matchup_data.iloc[0]["runs"]),
            "balls": int(matchup_data.iloc[0]["balls"]),
        }
        if not matchup_data.empty
        else {"batter": "N/A", "bowler": "N/A", "successRate": 0.0, "runs": 0, "balls": 0}
    )

    # Most consistent performer: lowest variance in player contribution score over recent matches.
    consistency_table = pd.DataFrame(columns=["player_name", "variance", "form_index", "matches"])
    if not form_index.empty:
        consistency_table = form_index.copy()
        min_matches = 3 if recent_n >= 5 else 2
        consistency_table = consistency_table[consistency_table["matches"] >= min_matches]
        if consistency_table.empty:
            consistency_table = form_index.copy()
        consistency_table = consistency_table.sort_values(["variance", "form_index"], ascending=[True, False], kind="stable")

    most_consistent = (
        {
            "player": str(consistency_table.iloc[0]["player_name"]),
            "variance": round(float(consistency_table.iloc[0]["variance"]), 2),
            "formIndex": round(float(consistency_table.iloc[0]["form_index"]), 2),
            "matches": int(consistency_table.iloc[0]["matches"]),
        }
        if not consistency_table.empty
        else {"player": "N/A", "variance": 0.0, "formIndex": 0.0, "matches": 0}
    )

    # Batting depth strength: average runs by positions 6-8.
    depth_by_position: list[dict[str, Any]] = []
    depth_average = 0.0
    if not recent_bat.empty:
        lineup = (
            recent_bat.groupby(["match_id", "inning", "batting_team", "batsman"], as_index=False)
            .agg(first_over=("over_num", "min"), first_ball=("ball_num", "min"))
            .sort_values(["match_id", "inning", "first_over", "first_ball", "batsman"], kind="stable")
        )
        lineup["batting_position"] = lineup.groupby(["match_id", "inning", "batting_team"]).cumcount() + 1

        batter_runs = (
            recent_bat.groupby(["match_id", "inning", "batting_team", "batsman"], as_index=False)
            .agg(runs=("batsman_runs", "sum"))
        )
        depth_table = lineup.merge(batter_runs, on=["match_id", "inning", "batting_team", "batsman"], how="left")
        depth_table = depth_table[depth_table["batting_position"].between(6, 8)]
        if not depth_table.empty:
            depth_avg_df = (
                depth_table.groupby("batting_position", as_index=False)["runs"]
                .mean()
                .sort_values("batting_position")
            )
            depth_by_position = [
                {"position": int(row["batting_position"]), "avgRuns": round(float(row["runs"]), 2)}
                for _, row in depth_avg_df.iterrows()
            ]
            depth_average = round(float(depth_table["runs"].mean()), 2)

    # Bowling phase effectiveness: wickets by phase.
    phase_table = recent_bowl.copy()
    phase_wickets: list[dict[str, Any]] = []
    best_phase = {"phase": "N/A", "wickets": 0}
    if not phase_table.empty:
        phase_table["phase"] = phase_table["over_num"].apply(
            lambda ov: "Powerplay" if int(ov) <= 5 else "Middle" if int(ov) <= 14 else "Death"
        )
        phase_agg = (
            phase_table.groupby("phase", as_index=False)["is_wicket_int"]
            .sum()
            .rename(columns={"is_wicket_int": "wickets"})
        )
        order = ["Powerplay", "Middle", "Death"]
        phase_agg["phase_order"] = phase_agg["phase"].map({name: idx for idx, name in enumerate(order)})
        phase_agg = phase_agg.sort_values("phase_order")
        phase_wickets = [
            {"phase": str(row["phase"]), "wickets": int(row["wickets"])}
            for _, row in phase_agg.iterrows()
        ]
        top_phase = phase_agg.sort_values("wickets", ascending=False).head(1)
        if not top_phase.empty:
            best_phase = {
                "phase": str(top_phase.iloc[0]["phase"]),
                "wickets": int(top_phase.iloc[0]["wickets"]),
            }

    # Player weakness indicator: lowest strike-rate phase profile among regular batters.
    weakness_indicator = {
        "player": "N/A",
        "phase": "N/A",
        "strikeRate": 0.0,
        "dismissalRate": 0.0,
        "note": "Insufficient recent batting samples.",
    }
    if not recent_bat.empty:
        weakness = recent_bat.copy()
        weakness["phase"] = weakness["over_num"].apply(
            lambda ov: "Powerplay" if int(ov) <= 5 else "Middle" if int(ov) <= 14 else "Death"
        )
        weakness = (
            weakness.groupby(["batsman", "phase"], as_index=False)
            .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"), dismissals=("is_wicket_int", "sum"))
            .rename(columns={"batsman": "player"})
        )
        weakness = weakness[weakness["balls"] >= 18] if (weakness["balls"] >= 18).any() else weakness
        if not weakness.empty:
            weakness["strike_rate"] = (weakness["runs"] * 100.0 / weakness["balls"].replace(0, 1)).round(2)
            weakness["dismissal_rate"] = (weakness["dismissals"] * 100.0 / weakness["balls"].replace(0, 1)).round(2)
            weakness = weakness.sort_values(["strike_rate", "dismissal_rate"], ascending=[True, False], kind="stable")
            row = weakness.iloc[0]
            weakness_indicator = {
                "player": str(row["player"]),
                "phase": str(row["phase"]),
                "strikeRate": float(row["strike_rate"]),
                "dismissalRate": float(row["dismissal_rate"]),
                "note": f"{row['player']} has the lowest recent strike rate in {row['phase']} overs.",
            }

    # Optimal XI suggestion with form and matchup-aware boost.
    optimal_xi: list[dict[str, Any]] = []
    try:
        try:
            from ml.optimizer import select_optimal_xi
        except Exception:
            from src.ml.optimizer import select_optimal_xi

        xi_df = select_optimal_xi(country=team, gender=selected_gender)
        if not xi_df.empty:
            xi_df = xi_df.copy()
            form_map = dict(zip(form_index.get("player_name", pd.Series(dtype=object)), form_index.get("form_index", pd.Series(dtype=float))))

            matchup_bonus_map: dict[str, float] = {}
            if not matchup_data.empty:
                batter_bonus = matchup_data.groupby("batter", as_index=False)["advantage_score"].mean()
                matchup_bonus_map = dict(zip(batter_bonus["batter"], batter_bonus["advantage_score"]))

            xi_df["form_index"] = xi_df.get("player_name", pd.Series(index=xi_df.index)).map(form_map).fillna(0.0)
            xi_df["matchup_bonus"] = xi_df.get("player_name", pd.Series(index=xi_df.index)).map(matchup_bonus_map).fillna(0.0)
            xi_df["perf_score"] = as_numeric(xi_df.get("perf_score", pd.Series(index=xi_df.index)), 0)
            xi_df["composite_score"] = (
                xi_df["perf_score"] + (xi_df["form_index"] * 0.6) + (xi_df["matchup_bonus"] * 0.08)
            ).round(2)
            xi_df = xi_df.sort_values("composite_score", ascending=False, kind="stable").head(11).reset_index(drop=True)
            xi_df["xi_rank"] = xi_df.index + 1

            keep_cols = [
                "xi_rank",
                "player_name",
                "role",
                "perf_score",
                "form_index",
                "matchup_bonus",
                "composite_score",
            ]
            present_cols = [col for col in keep_cols if col in xi_df.columns]
            optimal_xi = xi_df[present_cols].to_dict(orient="records")
    except Exception:
        optimal_xi = []

    return {
        "team": team,
        "opponent": opponent,
        "recentMatchesAnalyzed": int(len(recent_match_frame)),
        "topFormPlayers": top_form_players,
        "bestPowerplayBatter": best_powerplay,
        "mostReliableMiddleOrderBatter": best_middle,
        "bestDeathOverBowler": best_death_bowler,
        "playerMatchupAdvantage": matchup_advantage,
        "matchupRows": matchup_data.head(12).to_dict(orient="records") if not matchup_data.empty else [],
        "mostConsistentPerformer": most_consistent,
        "battingDepthStrength": {
            "averageRuns": depth_average,
            "positions": depth_by_position,
        },
        "bowlingPhaseEffectiveness": {
            "bestPhase": best_phase,
            "phaseWickets": phase_wickets,
        },
        "playerWeaknessIndicator": weakness_indicator,
        "optimalPlayingXI": optimal_xi,
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
    selected_gender = get_request_gender()
    cache_key = f"dashboard_kpis::{selected_gender}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)

    total_matches = int(len(matches))
    teams = (
        sorted(
            {
                str(team).strip()
                for team in pd.concat([matches.get("team1", pd.Series()), matches.get("team2", pd.Series())], ignore_index=True)
                .dropna()
                .astype(str)
                .tolist()
                if str(team).strip()
            }
        )
        if not matches.empty
        else []
    )

    innings_totals = pd.DataFrame(columns=["match_id", "inning", "batting_team", "total_runs", "balls"])
    if not deliveries.empty:
        innings_totals = (
            deliveries.groupby(["match_id", "inning", "batting_team"], as_index=False)
            .agg(total_runs=("total_runs", "sum"), balls=("total_runs", "count"))
        )
        innings_totals["match_id"] = innings_totals["match_id"].astype(str)

    avg_team_score = float(innings_totals["total_runs"].mean()) if not innings_totals.empty else 0.0
    highest_team_score = int(innings_totals["total_runs"].max()) if not innings_totals.empty else 0

    lowest_defended_score = 0
    if not matches.empty and not innings_totals.empty:
        match_core = matches[["match_id", "team1", "team2", "winner", "toss_winner", "toss_decision"]].copy()
        match_core["match_id"] = match_core["match_id"].astype(str)
        match_core["bat_first_team"] = match_core.apply(batting_first_team, axis=1)

        first_innings = innings_totals[innings_totals["inning"] == 1].copy()
        defended = first_innings.merge(match_core[["match_id", "winner", "bat_first_team"]], on="match_id", how="left")
        defended = defended[
            (defended["batting_team"] == defended["winner"])
            & (defended["batting_team"] == defended["bat_first_team"])
        ]
        if not defended.empty:
            lowest_defended_score = int(defended["total_runs"].min())

    top_nrr = 0.0
    top_nrr_team = "N/A"
    if not deliveries.empty:
        runs_for = (
            deliveries.groupby("batting_team", as_index=False)
            .agg(runs_for=("total_runs", "sum"), balls_for=("total_runs", "count"))
            .rename(columns={"batting_team": "team"})
        )
        runs_against = (
            deliveries.groupby("bowling_team", as_index=False)
            .agg(runs_against=("total_runs", "sum"), balls_against=("total_runs", "count"))
            .rename(columns={"bowling_team": "team"})
        )
        nrr_table = runs_for.merge(runs_against, on="team", how="outer").fillna(0)
        if not nrr_table.empty:
            nrr_table["for_rr"] = (nrr_table["runs_for"] * 6.0) / nrr_table["balls_for"].replace(0, 1)
            nrr_table["against_rr"] = (nrr_table["runs_against"] * 6.0) / nrr_table["balls_against"].replace(0, 1)
            nrr_table["nrr"] = nrr_table["for_rr"] - nrr_table["against_rr"]
            top_row = nrr_table.sort_values("nrr", ascending=False).head(1)
            if not top_row.empty:
                top_nrr = float(top_row.iloc[0]["nrr"])
                top_nrr_team = str(top_row.iloc[0]["team"])

    if not matches.empty:
        first_team = matches.apply(batting_first_team, axis=1)
        chase_win = (matches["winner"] != first_team).mean() * 100
    else:
        chase_win = 0.0

    payload = {
        "total_matches_played": total_matches,
        "average_team_score": round(avg_team_score, 1),
        "net_run_rate": round(top_nrr, 2),
        "net_run_rate_team": top_nrr_team,
        "highest_team_score": highest_team_score,
        "lowest_defended_score": int(lowest_defended_score),
        "total_matches": total_matches,
        "total_teams": len(teams),
        "avg_first_innings_score": int(round(avg_team_score)),
        "chasing_win_pct": round(float(chase_win), 1),
    }
    return set_cached_response(cache_key, payload)


@app.get("/dashboard/charts")
def get_dashboard_charts() -> dict[str, Any]:
    selected_gender = get_request_gender()
    cache_key = f"dashboard_charts::{selected_gender}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)

    def dominant_team(series: pd.Series) -> str:
        clean = series.dropna().astype(str).str.strip()
        clean = clean[clean != ""]
        if clean.empty:
            return ""
        return str(clean.value_counts().index[0])

    team_options = sorted(
        {
            str(team).strip()
            for team in pd.concat([matches.get("team1", pd.Series()), matches.get("team2", pd.Series())], ignore_index=True)
            .dropna()
            .astype(str)
            .tolist()
            if str(team).strip()
        }
    )

    innings_totals = pd.DataFrame(columns=["match_id", "inning", "batting_team", "total_runs", "balls", "wickets_lost"])
    if not deliveries.empty:
        innings_totals = (
            deliveries.groupby(["match_id", "inning", "batting_team"], as_index=False)
            .agg(total_runs=("total_runs", "sum"), balls=("total_runs", "count"), wickets_lost=("is_wicket_int", "sum"))
        )
        innings_totals["match_id"] = innings_totals["match_id"].astype(str)

    match_core = matches.copy()
    if not match_core.empty:
        for col in ["stage", "tournament_phase", "venue_canonical", "venue"]:
            if col not in match_core.columns:
                match_core[col] = ""

        match_core["match_id"] = match_core["match_id"].astype(str)
        match_core["win_by_runs"] = as_numeric(match_core.get("win_by_runs", pd.Series(index=match_core.index)), 0).astype(int)
        match_core["win_by_wickets"] = as_numeric(match_core.get("win_by_wickets", pd.Series(index=match_core.index)), 0).astype(int)
        match_core["bat_first_team"] = match_core.apply(batting_first_team, axis=1)

        if not deliveries.empty:
            total_runs_match = (
                deliveries.groupby("match_id", as_index=False)["total_runs"]
                .sum()
                .rename(columns={"total_runs": "match_total_runs"})
            )
            total_runs_match["match_id"] = total_runs_match["match_id"].astype(str)
            match_core = match_core.merge(total_runs_match, on="match_id", how="left")
        else:
            match_core["match_total_runs"] = 0

        match_core["match_total_runs"] = as_numeric(
            match_core.get("match_total_runs", pd.Series(index=match_core.index)),
            0,
        )

    innings_enriched = pd.DataFrame()
    if not innings_totals.empty and not match_core.empty:
        innings_enriched = innings_totals.merge(
            match_core[
                [
                    "match_id",
                    "winner",
                    "bat_first_team",
                    "team1",
                    "team2",
                    "match_date",
                    "match_total_runs",
                    "venue_canonical",
                    "venue",
                    "win_by_runs",
                    "win_by_wickets",
                ]
            ],
            on="match_id",
            how="left",
        )

    bat_stats = pd.DataFrame(columns=["player", "runs", "balls", "fours", "sixes", "strike_rate", "team"])
    bowl_stats = pd.DataFrame(columns=["player", "wickets", "balls_bowled", "runs_conceded", "economy", "team"])
    player_perf = pd.DataFrame()

    if not deliveries.empty:
        bat_stats = (
            deliveries.groupby("batsman", as_index=False)
            .agg(
                runs=("batsman_runs", "sum"),
                balls=("batsman_runs", "count"),
                fours=("batsman_runs", lambda s: int((s == 4).sum())),
                sixes=("batsman_runs", lambda s: int((s == 6).sum())),
            )
            .rename(columns={"batsman": "player"})
        )
        bat_stats["strike_rate"] = (bat_stats["runs"] * 100.0 / bat_stats["balls"].replace(0, 1)).round(2)
        bat_team = (
            deliveries.groupby("batsman")["batting_team"]
            .agg(dominant_team)
            .reset_index()
            .rename(columns={"batsman": "player", "batting_team": "team"})
        )
        bat_stats = bat_stats.merge(bat_team, on="player", how="left")

        bowl_stats = (
            deliveries.groupby("bowler", as_index=False)
            .agg(
                wickets=("is_wicket_int", "sum"),
                balls_bowled=("total_runs", "count"),
                runs_conceded=("total_runs", "sum"),
            )
            .rename(columns={"bowler": "player"})
        )
        bowl_stats["economy"] = (bowl_stats["runs_conceded"] * 6.0 / bowl_stats["balls_bowled"].replace(0, 1)).round(2)
        bowl_team = (
            deliveries.groupby("bowler")["bowling_team"]
            .agg(dominant_team)
            .reset_index()
            .rename(columns={"bowler": "player", "bowling_team": "team"})
        )
        bowl_stats = bowl_stats.merge(bowl_team, on="player", how="left")

        player_perf = bat_stats.merge(bowl_stats, on="player", how="outer", suffixes=("_bat", "_bowl"))
        player_perf["team"] = player_perf.get("team_bat", pd.Series(index=player_perf.index)).fillna(
            player_perf.get("team_bowl", pd.Series(index=player_perf.index))
        ).fillna("")

        for col in ["runs", "balls", "fours", "sixes", "strike_rate", "wickets", "balls_bowled", "runs_conceded", "economy"]:
            if col not in player_perf.columns:
                player_perf[col] = 0
            player_perf[col] = as_numeric(player_perf[col], 0)

        player_perf["impact"] = (
            (player_perf["runs"] * 0.28)
            + (player_perf["wickets"] * 17.0)
            + (player_perf["strike_rate"] * 0.08)
            - (player_perf["economy"] * 2.4)
        ).round(2)

    nrr_by_team: dict[str, float] = {}
    if not deliveries.empty:
        runs_for = (
            deliveries.groupby("batting_team", as_index=False)
            .agg(runs_for=("total_runs", "sum"), balls_for=("total_runs", "count"))
            .rename(columns={"batting_team": "team"})
        )
        runs_against = (
            deliveries.groupby("bowling_team", as_index=False)
            .agg(runs_against=("total_runs", "sum"), balls_against=("total_runs", "count"))
            .rename(columns={"bowling_team": "team"})
        )
        nrr_table = runs_for.merge(runs_against, on="team", how="outer").fillna(0)
        nrr_table["for_rr"] = (nrr_table["runs_for"] * 6.0) / nrr_table["balls_for"].replace(0, 1)
        nrr_table["against_rr"] = (nrr_table["runs_against"] * 6.0) / nrr_table["balls_against"].replace(0, 1)
        nrr_table["nrr"] = nrr_table["for_rr"] - nrr_table["against_rr"]
        nrr_by_team = {
            str(row["team"]): round(float(row["nrr"]), 3)
            for _, row in nrr_table.iterrows()
            if str(row["team"]).strip()
        }

    team_metrics_rows: list[dict[str, Any]] = []
    team_breakdown: list[dict[str, Any]] = []

    for team in team_options:
        team_matches = match_core[
            (match_core["team1"] == team) | (match_core["team2"] == team)
        ].copy()
        if team_matches.empty:
            continue

        team_matches = team_matches.sort_values(["match_date", "match_id"], kind="stable")
        matches_played = int(len(team_matches))
        wins = int((team_matches["winner"] == team).sum())
        losses = max(matches_played - wins, 0)
        win_pct = round((wins / max(matches_played, 1)) * 100, 1)

        team_innings = innings_totals[innings_totals["batting_team"] == team].copy()
        avg_score = float(team_innings["total_runs"].mean()) if not team_innings.empty else 0.0
        best_score = int(team_innings["total_runs"].max()) if not team_innings.empty else 0

        defended_low = 0
        highest_chase = 0
        if not innings_enriched.empty:
            team_enriched = innings_enriched[innings_enriched["batting_team"] == team].copy()
            defended = team_enriched[
                (team_enriched["winner"] == team)
                & (team_enriched["batting_team"] == team_enriched["bat_first_team"])
            ]
            chased = team_enriched[
                (team_enriched["winner"] == team)
                & (team_enriched["batting_team"] != team_enriched["bat_first_team"])
            ]
            if not defended.empty:
                defended_low = int(defended["total_runs"].min())
            if not chased.empty:
                highest_chase = int(chased["total_runs"].max())

        defend_matches = team_matches[team_matches["bat_first_team"] == team]
        chase_matches = team_matches[team_matches["bat_first_team"] != team]
        defend_win_pct = round(
            ((defend_matches["winner"] == team).mean() * 100) if not defend_matches.empty else 0.0,
            1,
        )
        chase_win_pct = round(
            ((chase_matches["winner"] == team).mean() * 100) if not chase_matches.empty else 0.0,
            1,
        )

        close_wins = team_matches[
            (team_matches["winner"] == team)
            & (
                ((team_matches["win_by_runs"] > 0) & (team_matches["win_by_runs"] <= 15))
                | ((team_matches["win_by_wickets"] > 0) & (team_matches["win_by_wickets"] <= 4))
            )
        ]
        close_win_pct = round((len(close_wins) / max(wins, 1)) * 100, 1)

        nrr = float(nrr_by_team.get(team, 0.0))
        captaincy_index = round(
            (win_pct * 0.56)
            + (nrr * 11.5)
            + (defend_win_pct * 0.14)
            + (chase_win_pct * 0.14)
            + (close_win_pct * 0.16),
            2,
        )

        team_scores = team_innings[["match_id", "total_runs"]].rename(columns={"total_runs": "team_score"})
        history = team_matches.merge(team_scores, on="match_id", how="left")
        history["team_score"] = as_numeric(history.get("team_score", pd.Series(index=history.index)), 0).astype(int)
        history["opponent"] = history.apply(
            lambda row: row["team2"] if str(row["team1"]) == team else row["team1"],
            axis=1,
        )
        history["result"] = (history["winner"] == team).astype(int)
        history["match_index"] = range(1, len(history) + 1)
        history["cum_wins"] = history["result"].cumsum()
        history["cumulative_win_pct"] = (history["cum_wins"] / history["match_index"].replace(0, 1) * 100).round(1)
        history["match_label"] = history["opponent"].apply(lambda opponent: f"vs {opponent}")

        trend_rows = [
            {
                "matchIndex": int(row["match_index"]),
                "matchLabel": str(row["match_label"]),
                "teamScore": int(row["team_score"]),
                "cumulativeWinPct": float(row["cumulative_win_pct"]),
                "result": "W" if int(row["result"]) == 1 else "L",
            }
            for _, row in history.tail(16).iterrows()
        ]

        team_h2h = (
            history.groupby("opponent", as_index=False)
            .agg(matches=("match_id", "count"), wins=("result", "sum"))
            .sort_values(["matches", "wins"], ascending=[False, False], kind="stable")
        )
        team_h2h["winPct"] = (team_h2h["wins"] / team_h2h["matches"].replace(0, 1) * 100).round(1)
        team_h2h_rows = [
            {
                "opponent": str(row["opponent"]),
                "matches": int(row["matches"]),
                "wins": int(row["wins"]),
                "winPct": float(row["winPct"]),
            }
            for _, row in team_h2h.head(6).iterrows()
        ]

        team_players_rows: list[dict[str, Any]] = []
        if not player_perf.empty:
            team_players = player_perf[player_perf["team"].astype(str) == team].copy()
            team_players = team_players.sort_values("impact", ascending=False, kind="stable").head(8)
            team_players_rows = [
                {
                    "player": str(row["player"]),
                    "runs": int(row["runs"]),
                    "wickets": int(row["wickets"]),
                    "strikeRate": round(float(row["strike_rate"]), 2),
                    "economy": round(float(row["economy"]), 2),
                    "impact": round(float(row["impact"]), 2),
                }
                for _, row in team_players.iterrows()
            ]

        team_metrics_rows.append(
            {
                "team": team,
                "matches": matches_played,
                "wins": wins,
                "losses": losses,
                "winPct": win_pct,
                "nrr": round(nrr, 2),
                "avgScore": round(avg_score, 1),
                "bestScore": best_score,
                "lowestDefended": defended_low,
                "highestChase": highest_chase,
                "captaincyIndex": captaincy_index,
                "defendWinPct": defend_win_pct,
                "chaseWinPct": chase_win_pct,
            }
        )

        team_breakdown.append(
            {
                "team": team,
                "summary": {
                    "matches": matches_played,
                    "wins": wins,
                    "losses": losses,
                    "winPct": win_pct,
                    "nrr": round(nrr, 2),
                    "avgScore": round(avg_score, 1),
                    "bestScore": best_score,
                    "lowestDefended": defended_low,
                    "highestChase": highest_chase,
                    "defendWinPct": defend_win_pct,
                    "chaseWinPct": chase_win_pct,
                },
                "trend": trend_rows,
                "keyInsights": [
                    {"title": "Overall Record", "value": f"{wins}-{losses} ({win_pct}%)"},
                    {"title": "Net Run Rate", "value": f"{round(nrr, 2)}"},
                    {"title": "Defend vs Chase", "value": f"{defend_win_pct}% vs {chase_win_pct}%"},
                    {
                        "title": "Lowest Defended",
                        "value": str(defended_low) if defended_low > 0 else "N/A",
                    },
                    {
                        "title": "Highest Successful Chase",
                        "value": str(highest_chase) if highest_chase > 0 else "N/A",
                    },
                ],
                "records": [
                    {"metric": "Best Team Score", "value": best_score},
                    {"metric": "Average Team Score", "value": round(avg_score, 1)},
                    {"metric": "Defend Success %", "value": defend_win_pct},
                    {"metric": "Chase Success %", "value": chase_win_pct},
                ],
                "topPlayers": team_players_rows,
                "headToHead": team_h2h_rows,
            }
        )

    team_metrics_df = pd.DataFrame(team_metrics_rows)

    top_teams_data: list[dict[str, Any]] = []
    best_captaincy_data: list[dict[str, Any]] = []
    if not team_metrics_df.empty:
        top_teams_df = team_metrics_df.sort_values(
            ["winPct", "nrr", "avgScore"],
            ascending=[False, False, False],
            kind="stable",
        ).head(7)
        top_teams_data = [
            {
                "team": str(row["team"]),
                "matches": int(row["matches"]),
                "wins": int(row["wins"]),
                "winPct": float(row["winPct"]),
                "nrr": float(row["nrr"]),
                "avgScore": float(row["avgScore"]),
            }
            for _, row in top_teams_df.iterrows()
        ]

        captaincy_df = team_metrics_df.sort_values(
            ["captaincyIndex", "winPct"],
            ascending=[False, False],
            kind="stable",
        ).head(7)
        best_captaincy_data = [
            {
                "team": str(row["team"]),
                "captaincyIndex": float(row["captaincyIndex"]),
                "winPct": float(row["winPct"]),
                "defendWinPct": float(row["defendWinPct"]),
                "chaseWinPct": float(row["chaseWinPct"]),
                "matches": int(row["matches"]),
            }
            for _, row in captaincy_df.iterrows()
        ]

    top_performing_players: list[dict[str, Any]] = []
    top_batsmen_data: list[dict[str, Any]] = []
    top_bowlers_data: list[dict[str, Any]] = []

    if not player_perf.empty:
        top_perf_df = player_perf.sort_values("impact", ascending=False, kind="stable").head(10)
        top_performing_players = [
            {
                "player": str(row["player"]),
                "team": str(row["team"]),
                "runs": int(row["runs"]),
                "wickets": int(row["wickets"]),
                "strikeRate": round(float(row["strike_rate"]), 2),
                "economy": round(float(row["economy"]), 2),
                "impact": round(float(row["impact"]), 2),
            }
            for _, row in top_perf_df.iterrows()
        ]

    if not bat_stats.empty:
        bat_df = bat_stats.sort_values(["runs", "strike_rate"], ascending=[False, False], kind="stable").head(8)
        top_batsmen_data = [
            {
                "player": str(row["player"]),
                "team": str(row.get("team", "")),
                "runs": int(row["runs"]),
                "strikeRate": round(float(row["strike_rate"]), 2),
                "balls": int(row["balls"]),
            }
            for _, row in bat_df.iterrows()
        ]

    if not bowl_stats.empty:
        bowl_df = bowl_stats.copy()
        bowl_df = bowl_df[bowl_df["balls_bowled"] >= 30] if (bowl_df["balls_bowled"] >= 30).any() else bowl_df
        bowl_df = bowl_df.sort_values(["wickets", "economy"], ascending=[False, True], kind="stable").head(8)
        top_bowlers_data = [
            {
                "player": str(row["player"]),
                "team": str(row.get("team", "")),
                "wickets": int(row["wickets"]),
                "economy": round(float(row["economy"]), 2),
                "balls": int(row["balls_bowled"]),
            }
            for _, row in bowl_df.iterrows()
        ]

    key_records_data: list[dict[str, Any]] = []
    highest_team_score = int(innings_totals["total_runs"].max()) if not innings_totals.empty else 0
    lowest_defended = 0
    if not innings_enriched.empty:
        defended = innings_enriched[
            (innings_enriched["batting_team"] == innings_enriched["winner"])
            & (innings_enriched["batting_team"] == innings_enriched["bat_first_team"])
        ]
        if not defended.empty:
            lowest_defended = int(defended["total_runs"].min())

    highest_individual = 0
    if not deliveries.empty:
        individual = (
            deliveries.groupby(["match_id", "batsman"], as_index=False)["batsman_runs"]
            .sum()
            .sort_values("batsman_runs", ascending=False, kind="stable")
        )
        if not individual.empty:
            highest_individual = int(individual.iloc[0]["batsman_runs"])

    best_bowling_fig = "N/A"
    if not deliveries.empty:
        figures = (
            deliveries.groupby(["match_id", "bowler"], as_index=False)
            .agg(wickets=("is_wicket_int", "sum"), runs=("total_runs", "sum"))
            .sort_values(["wickets", "runs"], ascending=[False, True], kind="stable")
        )
        if not figures.empty:
            row = figures.iloc[0]
            best_bowling_fig = f"{int(row['wickets'])}/{int(row['runs'])} by {row['bowler']}"

    key_records_data = [
        {
            "title": "Highest Team Score",
            "value": highest_team_score,
            "context": "Best innings total recorded",
        },
        {
            "title": "Lowest Defended Score",
            "value": int(lowest_defended) if lowest_defended > 0 else "N/A",
            "context": "Lowest winning total while defending",
        },
        {
            "title": "Highest Individual Score",
            "value": highest_individual,
            "context": "Highest score by a batter in one match",
        },
        {
            "title": "Best Bowling Figures",
            "value": best_bowling_fig,
            "context": "Top wicket haul in a single match",
        },
    ]

    head_to_head_data: list[dict[str, Any]] = []
    if not match_core.empty:
        h2h_map: dict[str, dict[str, Any]] = {}
        ordered_matches = match_core.sort_values(["match_date", "match_id"], kind="stable")
        for _, row in ordered_matches.iterrows():
            team_a, team_b = canonical_team_pair(str(row["team1"]), str(row["team2"]))
            if not team_a or not team_b:
                continue

            key = f"{team_a}::{team_b}"
            if key not in h2h_map:
                h2h_map[key] = {
                    "teamA": team_a,
                    "teamB": team_b,
                    "matches": 0,
                    "winsA": 0,
                    "winsB": 0,
                    "lastWinner": "",
                }

            h2h_map[key]["matches"] += 1
            winner = str(row["winner"])
            if winner == team_a:
                h2h_map[key]["winsA"] += 1
            elif winner == team_b:
                h2h_map[key]["winsB"] += 1
            h2h_map[key]["lastWinner"] = winner

        head_to_head_data = [
            {
                "pair": f"{value['teamA']} vs {value['teamB']}",
                "teamA": value["teamA"],
                "teamB": value["teamB"],
                "matches": int(value["matches"]),
                "winsA": int(value["winsA"]),
                "winsB": int(value["winsB"]),
                "lastWinner": value["lastWinner"],
            }
            for value in h2h_map.values()
        ]
        head_to_head_data = sorted(head_to_head_data, key=lambda item: item["matches"], reverse=True)[:10]

    hyped_matches_data: list[dict[str, Any]] = []
    if not match_core.empty:
        for _, row in match_core.iterrows():
            runs_margin = int(row.get("win_by_runs", 0) or 0)
            wickets_margin = int(row.get("win_by_wickets", 0) or 0)
            winner = str(row.get("winner", ""))

            if runs_margin > 0:
                margin_text = f"{winner} won by {runs_margin} runs"
                closeness = max(0, 35 - runs_margin) * 2.1
            elif wickets_margin > 0:
                margin_text = f"{winner} won by {wickets_margin} wickets"
                closeness = max(0, 10 - wickets_margin) * 6.2
            else:
                margin_text = f"Winner: {winner or 'N/A'}"
                closeness = 8.0

            stage_blob = f"{row.get('stage', '')} {row.get('tournament_phase', '')}".lower()
            stage_boost = 12.0 if "final" in stage_blob else 7.0 if "semi" in stage_blob else 0.0
            scoring_boost = float(row.get("match_total_runs", 0.0) or 0.0) / 8.0
            hype_score = round(closeness + scoring_boost + stage_boost, 1)

            hyped_matches_data.append(
                {
                    "matchId": str(row["match_id"]),
                    "fixture": f"{row['team1']} vs {row['team2']}",
                    "winner": winner,
                    "margin": margin_text,
                    "totalRuns": int(row.get("match_total_runs", 0) or 0),
                    "hypeScore": hype_score,
                    "venue": str(row.get("venue_canonical") or row.get("venue") or "Unknown Venue"),
                }
            )

        hyped_matches_data = sorted(
            hyped_matches_data,
            key=lambda item: (item["hypeScore"], item["totalRuns"]),
            reverse=True,
        )[:8]

    key_insights_data: list[dict[str, Any]] = []
    if top_teams_data:
        leader = top_teams_data[0]
        key_insights_data.append(
            {
                "title": "Top Team Throughout",
                "detail": f"{leader['team']} leads with {leader['wins']} wins in {leader['matches']} matches ({leader['winPct']}% win rate).",
            }
        )

    if top_batsmen_data:
        batter = top_batsmen_data[0]
        key_insights_data.append(
            {
                "title": "Top Batter/Woman",
                "detail": f"{batter['player']} ({batter.get('team', 'N/A')}) has scored {batter['runs']} runs at {batter['strikeRate']} SR.",
            }
        )

    if top_bowlers_data:
        bowler = top_bowlers_data[0]
        key_insights_data.append(
            {
                "title": "Top Bowler",
                "detail": f"{bowler['player']} has {bowler['wickets']} wickets with {bowler['economy']} economy.",
            }
        )

    if head_to_head_data:
        rivalry = head_to_head_data[0]
        key_insights_data.append(
            {
                "title": "Most Active Rivalry",
                "detail": f"{rivalry['pair']} has met {rivalry['matches']} times (latest winner: {rivalry['lastWinner'] or 'N/A'}).",
            }
        )

    ai_insight_cards: list[dict[str, Any]] = []
    if top_teams_data:
        leader = top_teams_data[0]
        ai_insight_cards.append(
            {
                "title": "AI Power Rank #1",
                "value": leader["team"],
                "detail": f"Win% {leader['winPct']} | NRR {leader['nrr']} | Avg score {leader['avgScore']}",
            }
        )

    if best_captaincy_data:
        cap = best_captaincy_data[0]
        ai_insight_cards.append(
            {
                "title": "Best Captaincy Proxy",
                "value": cap["team"],
                "detail": f"Captaincy index {cap['captaincyIndex']} from win conversion, pressure wins, defend/chase split.",
            }
        )

    if hyped_matches_data:
        hype = hyped_matches_data[0]
        ai_insight_cards.append(
            {
                "title": "Most Hyped Match",
                "value": hype["fixture"],
                "detail": f"Hype score {hype['hypeScore']} | {hype['margin']} | Total runs {hype['totalRuns']}",
            }
        )

    if top_performing_players:
        top_player = top_performing_players[0]
        ai_insight_cards.append(
            {
                "title": "Top Performing Player",
                "value": top_player["player"],
                "detail": f"Impact {top_player['impact']} | Runs {top_player['runs']} | Wickets {top_player['wickets']}",
            }
        )

    team_breakdown = sorted(
        team_breakdown,
        key=lambda entry: (
            float(entry.get("summary", {}).get("winPct", 0.0)),
            float(entry.get("summary", {}).get("nrr", 0.0)),
        ),
        reverse=True,
    )

    payload = {
        "topPerformingTeamsData": top_teams_data,
        "topPerformingPlayersData": top_performing_players,
        "topBatsmenData": top_batsmen_data,
        "topBowlersData": top_bowlers_data,
        "bestCaptaincyData": best_captaincy_data,
        "keyRecordsData": key_records_data,
        "keyInsightsData": key_insights_data,
        "teamOptions": team_options,
        "teamBreakdown": team_breakdown,
        "headToHeadData": head_to_head_data,
        "hypedMatchesData": hyped_matches_data,
        "aiInsightCards": ai_insight_cards,
        "matchCompetitivenessData": [],
        "playerArchetypesData": [],
        "deathBowlingLeadersData": [],
        "powerplayLeadersData": [],
        "tossImpactData": [],
    }
    return set_cached_response(cache_key, payload)


@app.get("/dashboard/summary")
def get_dashboard_summary() -> dict[str, Any]:
    selected_gender = get_request_gender()
    cache_key = f"dashboard_summary::{selected_gender}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    payload = {
        "kpis": get_dashboard_kpis(),
        "charts": get_dashboard_charts(),
        "gender": selected_gender,
    }
    return set_cached_response(cache_key, payload)


@app.on_event("startup")
def prewarm_dashboard_summary_cache() -> None:
    """Warm dashboard caches so first UI load is faster."""
    if os.getenv("API_PREWARM_DASHBOARD", "1") != "1":
        return

    token = _REQUEST_GENDER.set("male")
    try:
        for g in ["male", "female"]:
            _REQUEST_GENDER.set(g)
            get_dashboard_summary()
    except Exception:
        # Do not block API startup if prewarm fails.
        pass
    finally:
        _REQUEST_GENDER.reset(token)


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

    venues = list_unique_venues(matches)

    ordered = matches.sort_values(["match_date", "match_id"], ascending=[False, False], kind="stable")
    options = [
        {
            "matchId": str(row["match_id"]),
            "label": f"{row['team1']} vs {row['team2']} | {row.get('venue_canonical', row['venue'])}",
            "team1": str(row["team1"]),
            "team2": str(row["team2"]),
            "venue": str(row.get("venue_canonical", row["venue"])),
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
    team, opponent = canonical_team_pair(team, opponent)

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

    venues = list_unique_venues(matches)

    return {"teams": teams, "venues": venues}


@app.post("/analyst/win-probability")
def analyst_win_probability(req: AnalystWinRequest) -> dict[str, Any]:
    selected_gender = normalize_gender_value(req.gender or get_request_gender(), default=normalize_gender_value(DEFAULT_GENDER, "male"))

    team_a, team_b = canonical_team_pair(req.team_a, req.team_b)
    toss_winner = req.toss_winner if req.toss_winner in {team_a, team_b} else team_a

    matches = load_matches_frame(selected_gender)
    analysis_matches = apply_analyst_match_filters(
        matches=matches,
        team=team_a,
        opponent=team_b,
        venue=req.venue,
        use_venue_filter=bool(req.use_venue_filter),
        use_toss_filter=bool(req.use_toss_filter),
        toss_result_filter=req.toss_result_filter,
        toss_decision_filter=req.toss_decision_filter,
    )
    pair_matches = apply_analyst_match_filters(
        matches=matches,
        team=team_a,
        opponent=team_b,
        venue="Neutral Venue",
        use_venue_filter=False,
        use_toss_filter=False,
        toss_result_filter="all",
        toss_decision_filter="any",
    )

    effective_matches = analysis_matches if not analysis_matches.empty else pair_matches
    fallback_used = analysis_matches.empty and not effective_matches.empty

    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    if not effective_matches.empty:
        match_ids = set(effective_matches["match_id"].astype(str).tolist())
        deliveries = deliveries[deliveries["match_id"].astype(str).isin(match_ids)].copy()
    else:
        deliveries = deliveries.iloc[0:0].copy()

    venue_value = req.venue if (req.use_venue_filter and not fallback_used) else "Neutral Venue"
    model_payload = build_match_prediction_payload(
        matches=effective_matches,
        deliveries=deliveries,
        team_a=team_a,
        team_b=team_b,
        toss_winner=toss_winner,
        toss_decision=req.toss_decision,
        is_knockout=req.is_knockout,
        venue=venue_value,
        gender=selected_gender,
    )
    payload = build_analyst_win_probability_payload(model_payload)
    payload["filtersApplied"] = {
        "useVenueFilter": bool(req.use_venue_filter),
        "useTossFilter": bool(req.use_toss_filter),
        "tossResultFilter": normalize_toss_result_filter(req.toss_result_filter),
        "tossDecisionFilter": normalize_toss_decision_filter(req.toss_decision_filter),
        "sampledMatches": int(len(analysis_matches)),
        "effectiveSampledMatches": int(len(effective_matches)),
        "fallbackUsed": bool(fallback_used),
    }
    return payload


@app.get("/analyst/insights")
def analyst_insights(
    team: str,
    opponent: str,
    venue: str = "Neutral Venue",
    toss_winner: str | None = None,
    toss_decision: str = "bat",
    use_venue_filter: bool = False,
    use_toss_filter: bool = False,
    toss_result_filter: str = "all",
    toss_decision_filter: str = "any",
) -> dict[str, Any]:
    selected_gender = get_request_gender()
    team, opponent = canonical_team_pair(team, opponent)

    matches = load_matches_frame(selected_gender)
    analysis_matches = apply_analyst_match_filters(
        matches=matches,
        team=team,
        opponent=opponent,
        venue=venue,
        use_venue_filter=bool(use_venue_filter),
        use_toss_filter=bool(use_toss_filter),
        toss_result_filter=toss_result_filter,
        toss_decision_filter=toss_decision_filter,
    )
    pair_matches = apply_analyst_match_filters(
        matches=matches,
        team=team,
        opponent=opponent,
        venue="Neutral Venue",
        use_venue_filter=False,
        use_toss_filter=False,
        toss_result_filter="all",
        toss_decision_filter="any",
    )

    effective_matches = analysis_matches if not analysis_matches.empty else pair_matches
    fallback_used = analysis_matches.empty and not effective_matches.empty

    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    if not effective_matches.empty:
        allowed_ids = set(effective_matches["match_id"].astype(str).tolist())
        deliveries = deliveries[deliveries["match_id"].astype(str).isin(allowed_ids)].copy()
    else:
        deliveries = deliveries.iloc[0:0].copy()

    # Expected first-innings score at venue for selected team.
    innings = build_first_innings_dataset(deliveries)
    if innings.empty or not {"batting_team", "inning", "total_runs"}.issubset(innings.columns):
        expected_pool = pd.DataFrame(columns=["total_runs"])
    else:
        expected_pool = innings[(innings["batting_team"] == team) & (innings["inning"] == 1)]

    expected_score = float(expected_pool["total_runs"].mean()) if not expected_pool.empty else 0.0
    score_q25 = float(expected_pool["total_runs"].quantile(0.25)) if not expected_pool.empty else 0.0
    score_q75 = float(expected_pool["total_runs"].quantile(0.75)) if not expected_pool.empty else 0.0

    # Venue performance index.
    team_venue_matches = team_match_subset(effective_matches, team)
    venue_win_pct = float((team_venue_matches["winner"] == team).mean() * 100) if not team_venue_matches.empty else 0.0

    # Head-to-head dominance.
    h2h = effective_matches
    h2h_wins = int((h2h["winner"] == team).sum()) if not h2h.empty else 0
    h2h_total = int(len(h2h))
    h2h_ratio = round((h2h_wins / h2h_total) * 100, 1) if h2h_total > 0 else 50.0

    # Toss impact analysis for selected team.
    team_matches = team_match_subset(effective_matches, team)
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
    points = build_points_table(effective_matches)
    rank_team = int(points[points["Team"] == team]["Rank"].iloc[0]) if team in points["Team"].values else 999
    rank_opp = int(points[points["Team"] == opponent]["Rank"].iloc[0]) if opponent in points["Team"].values else 999

    favourite = team if rank_team < rank_opp else opponent
    underdog = opponent if favourite == team else team

    if effective_matches.empty or deliveries.empty:
        upset_prob = 0.0
    else:
        upset_prob = compute_upset_probability(
            matches=effective_matches,
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
        matches=effective_matches,
        deliveries=deliveries,
        team_a=team,
        team_b=opponent,
        toss_winner=toss_winner or team,
        toss_decision=toss_decision,
        is_knockout=0,
        venue=venue if (use_venue_filter and not fallback_used) else "Neutral Venue",
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
            "venue": normalize_venue_name(venue) if (use_venue_filter and not fallback_used) else "All venues",
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
        "filtersApplied": {
            "useVenueFilter": bool(use_venue_filter),
            "useTossFilter": bool(use_toss_filter),
            "tossResultFilter": normalize_toss_result_filter(toss_result_filter),
            "tossDecisionFilter": normalize_toss_decision_filter(toss_decision_filter),
            "sampledMatches": int(len(analysis_matches)),
            "effectiveSampledMatches": int(len(effective_matches)),
            "fallbackUsed": bool(fallback_used),
        },
    }


@app.post("/predict/upset")
def predict_upset(req: UpsetRequest) -> dict[str, Any]:
    selected_gender = normalize_gender_value(req.gender or get_request_gender(), default=normalize_gender_value(DEFAULT_GENDER, "male"))
    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)

    upset_prob = compute_upset_probability(
        matches=matches,
        deliveries=deliveries,
        favourite_team=req.favourite_team,
        underdog_team=req.underdog_team,
        toss_winner=req.toss_winner,
        toss_bat_first=req.toss_bat_first,
        is_knockout=req.is_knockout,
        gender=selected_gender,
    )

    return {
        "favouriteTeam": req.favourite_team,
        "underdogTeam": req.underdog_team,
        "upsetProbability": round(upset_prob * 100, 1),
        "riskLevel": "HIGH RISK" if upset_prob > 0.35 else "Normal",
    }


@app.get("/ml/player-clusters")
def get_player_clusters() -> dict[str, Any]:
    frame = read_csv_for_gender("player_clusters.csv", get_request_gender())
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
    frame = read_csv_for_gender("association_rules.csv", get_request_gender())
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
    selected_gender = get_request_gender()
    matches = load_matches_frame(selected_gender)
    deliveries = load_deliveries_frame(selected_gender, matches=matches)
    players = load_players_frame(selected_gender, matches=matches, deliveries=deliveries)

    if "country" in players.columns and not players.empty:
        team_list = sorted({str(t).strip() for t in players["country"].dropna().astype(str).tolist() if str(t).strip()})
    else:
        team_values = pd.concat(
            [
                matches.get("team1", pd.Series(dtype=object)),
                matches.get("team2", pd.Series(dtype=object)),
            ],
            ignore_index=True,
        )
        team_list = sorted({str(t).strip() for t in team_values.dropna().astype(str).tolist() if str(t).strip()})

    return {"teams": ["All Teams"] + team_list}


@app.get("/optimization/optimal-xi")
def optimization_optimal_xi(country: str = "All Teams") -> dict[str, Any]:
    try:
        try:
            from ml.optimizer import select_optimal_xi
        except Exception:
            from src.ml.optimizer import select_optimal_xi

        selected_country = None if country == "All Teams" else country
        selected_gender = get_request_gender()
        xi = select_optimal_xi(selected_country, gender=selected_gender)
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
        selected_gender = get_request_gender()
        order_df = optimize_batting_order(selected_country, gender=selected_gender)
        return {"battingOrder": order_df.to_dict(orient="records")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/optimization/shap")
def optimization_get_shap() -> dict[str, Any]:
    frame = read_csv_for_gender("shap_importance.csv", get_request_gender())
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

        shap_df = compute_shap_importance(get_request_gender())
        if shap_df.empty:
            raise HTTPException(status_code=500, detail="SHAP computation returned no data")
        return {"available": True, "shap": shap_df.to_dict(orient="records")}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
