"""
Optimization use cases:
  1) Optimal Playing XI selector (constraint-based scoring)
  2) Batting order optimizer (heuristic ordering)
  3) SHAP feature importance (model explainability)
"""

from __future__ import annotations

import os
import pickle
from typing import Optional

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

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str) and value.strip() == "":
            return default
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


# -- OPTIMIZER 1: PLAYING XI SELECTOR ---------------------------------
def compute_player_score(row: pd.Series) -> float:
    """
    Composite performance score for XI selection.
    Weights: batting(40%) + bowling(35%) + allround_bonus(25%).
    """
    bat_score = (
        _safe_float(row.get("batting_avg"), 0.0) * 0.30
        + _safe_float(row.get("strike_rate"), 0.0) * 0.10
    )
    bowl_score = (
        max(0.0, 30.0 - _safe_float(row.get("bowling_avg"), 30.0)) * 0.25
        + max(0.0, 10.0 - _safe_float(row.get("economy"), 8.0)) * 0.10
    )

    has_bat = _safe_float(row.get("runs"), 0.0) > 100
    has_bowl = _safe_float(row.get("wickets"), 0.0) > 5
    ar_bonus = 15.0 if (has_bat and has_bowl) else 0.0

    return round(bat_score + bowl_score + ar_bonus, 2)


def select_optimal_xi(country: Optional[str] = None) -> pd.DataFrame:
    """
    Select optimal 11 players using role composition constraints.
    """
    players = pd.read_sql("SELECT * FROM silver.clean_players", engine)

    if country and country != "All Teams":
        players = players[players["country"] == country].copy()

    if len(players) < 11:
        players = pd.read_sql("SELECT * FROM silver.clean_players", engine)

    players["perf_score"] = players.apply(compute_player_score, axis=1)
    players = players.sort_values("perf_score", ascending=False)

    selected: list[pd.Series] = []
    role_quotas = {
        "Batter": 4,
        "All-Rounder": 2,
        "Bowler": 4,
        "Unknown": 1,
    }
    role_counts = {role: 0 for role in role_quotas}

    for _, player in players.iterrows():
        role = str(player.get("role", "Unknown"))
        if role not in role_counts:
            role = "Unknown"
        if role_counts[role] < role_quotas[role] and len(selected) < 11:
            selected.append(player)
            role_counts[role] += 1

    selected_names = {str(p.get("player_name", "")) for p in selected}
    for _, player in players.iterrows():
        if len(selected) >= 11:
            break
        if str(player.get("player_name", "")) not in selected_names:
            selected.append(player)

    xi_df = pd.DataFrame(selected[:11]).reset_index(drop=True)
    xi_df.index += 1
    xi_df["xi_rank"] = xi_df.index

    required_cols = [
        "xi_rank",
        "player_name",
        "country",
        "role",
        "runs",
        "batting_avg",
        "strike_rate",
        "wickets",
        "bowling_avg",
        "economy",
        "perf_score",
    ]
    available_cols = [c for c in required_cols if c in xi_df.columns]
    result = xi_df[available_cols].copy()

    print(f"\n[OK] Optimal XI selected for {country or 'All Teams'}:")
    if all(c in result.columns for c in ["xi_rank", "player_name", "role", "perf_score"]):
        print(result[["xi_rank", "player_name", "role", "perf_score"]].to_string(index=False))
    return result


# -- OPTIMIZER 2: BATTING ORDER ---------------------------------------
def optimize_batting_order(country: Optional[str] = None) -> pd.DataFrame:
    """
    Optimize batting order with simple cricketing heuristics.
    """
    xi = select_optimal_xi(country)

    batters = xi.copy()
    batters["sr"] = batters["strike_rate"].apply(_safe_float)
    batters["avg"] = batters["batting_avg"].apply(_safe_float)

    order: list[int] = []

    openers = batters.nlargest(2, "sr")
    order.extend(openers.index.tolist())

    remaining = batters.drop(index=order)

    anchors = remaining.nlargest(3, "avg")
    order.extend(anchors.index.tolist())
    remaining = remaining.drop(index=anchors.index)

    finishers = remaining.nlargest(2, "sr")
    order.extend(finishers.index.tolist())
    remaining = remaining.drop(index=finishers.index)

    order.extend(remaining.index.tolist())

    result = batters.loc[order].reset_index(drop=True)
    result.index += 1
    result["batting_position"] = result.index
    result["role_in_order"] = result["batting_position"].map(
        {
            1: "Opener",
            2: "Opener",
            3: "No.3",
            4: "Middle Order",
            5: "Middle Order",
            6: "Finisher",
            7: "Finisher",
            8: "All-Rounder",
            9: "All-Rounder",
            10: "Tail",
            11: "Tail",
        }
    )

    print("\n[OK] Optimized batting order:")
    print(result[["batting_position", "player_name", "role_in_order", "sr", "avg"]].to_string(index=False))
    return result


# -- OPTIMIZER 3: SHAP FEATURE IMPORTANCE -----------------------------
def compute_shap_importance() -> pd.DataFrame:
    """
    Compute SHAP values for the match outcome XGBoost model.
    """
    import sys

    import shap

    sys.path.append(os.path.dirname(__file__))
    from features import build_match_features  # pylint: disable=import-outside-toplevel

    model_path = os.path.join(MODELS_DIR, "match_outcome_xgb.pkl")

    if not os.path.exists(model_path):
        print("[ERROR] Model not found. Run train_models.py first.")
        return pd.DataFrame()

    with open(model_path, "rb") as f:
        artifact = pickle.load(f)

    model = artifact["model"]
    feat_cols = artifact["features"]

    df = build_match_features()
    if df.empty:
        print("[ERROR] Feature matrix is empty.")
        return pd.DataFrame()

    X = df[feat_cols].fillna(0)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    if isinstance(shap_values, list):
        shap_arr = np.abs(shap_values[1]).mean(axis=0)
    else:
        shap_arr = np.abs(shap_values).mean(axis=0)

    shap_df = pd.DataFrame({"Feature": feat_cols, "SHAP_Value": shap_arr}).sort_values(
        "SHAP_Value", ascending=False
    )

    print("\n[OK] SHAP feature importance:")
    print(shap_df.to_string(index=False))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "shap_importance.csv")
    shap_df.to_csv(out_path, index=False)
    print(f"[SAVE] {out_path}")
    return shap_df


if __name__ == "__main__":
    print("=" * 55)
    print("OPTIMIZATION SUITE - RUNNING")
    print("=" * 55)
    select_optimal_xi("India")
    optimize_batting_order("India")
    compute_shap_importance()
