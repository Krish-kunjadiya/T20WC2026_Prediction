import os
from functools import lru_cache

import pandas as pd
import xgboost as xgb
from sqlalchemy import text

from db import engine


MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "outcome_model.json")


def _prepare_training_data():
    base = os.path.dirname(__file__)
    default_path = os.path.join(base, "..", "10", "matches.csv")
    matches_path = os.getenv("MATCHES_DATA_PATH", default_path)
    df = pd.read_csv(matches_path)

    # Simple feature set: encode teams and venue as categorical indices
    teams = pd.unique(df[["team1", "team2"]].values.ravel("K"))
    team_to_idx = {t: i for i, t in enumerate(teams)}
    venues = df["venue"].unique()
    venue_to_idx = {v: i for i, v in enumerate(venues)}

    def encode_row(row):
        return [
            team_to_idx.get(row["team1"], -1),
            team_to_idx.get(row["team2"], -1),
            venue_to_idx.get(row["venue"], -1),
            1 if row.get("toss_decision", "") == "bat" else 0,
        ]

    X = df.apply(encode_row, axis=1, result_type="expand")
    # Label: did team1 win?
    y = (df["winner"] == df["team1"]).astype(int)
    return xgb.DMatrix(X, label=y), team_to_idx, venue_to_idx


def train_and_save():
    dtrain, team_to_idx, venue_to_idx = _prepare_training_data()
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "eta": 0.1,
    }
    bst = xgb.train(params, dtrain, num_boost_round=60)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    bst.save_model(MODEL_PATH)

    mapping_path = os.path.join(os.path.dirname(MODEL_PATH), "mappings.parquet")
    pd.DataFrame(
        {
            "team": list(team_to_idx.keys()),
            "team_idx": list(team_to_idx.values()),
        }
    ).to_parquet(mapping_path.replace(".parquet", "_teams.parquet"))
    pd.DataFrame(
        {
            "venue": list(venue_to_idx.keys()),
            "venue_idx": list(venue_to_idx.values()),
        }
    ).to_parquet(mapping_path.replace(".parquet", "_venues.parquet"))


@lru_cache()
def load_model_and_mappings():
    if not os.path.exists(MODEL_PATH):
        train_and_save()

    bst = xgb.Booster()
    bst.load_model(MODEL_PATH)

    teams_df = pd.read_parquet(
        os.path.join(os.path.dirname(MODEL_PATH), "mappings_teams.parquet")
    )
    venues_df = pd.read_parquet(
        os.path.join(os.path.dirname(MODEL_PATH), "mappings_venues.parquet")
    )
    team_to_idx = dict(zip(teams_df["team"], teams_df["team_idx"]))
    venue_to_idx = dict(zip(venues_df["venue"], venues_df["venue_idx"]))
    return bst, team_to_idx, venue_to_idx


def predict_outcome(team_a: str, team_b: str, venue: str, toss_winner: str, toss_decision: str):
    bst, team_to_idx, venue_to_idx = load_model_and_mappings()

    team1 = team_a
    team2 = team_b

    from_team_idx = team_to_idx.get(team1, -1)
    to_team_idx = team_to_idx.get(team2, -1)
    venue_idx = venue_to_idx.get(venue, -1)
    toss_bat_flag = 1 if toss_decision.lower() == "bat" else 0

    X = pd.DataFrame(
        [[from_team_idx, to_team_idx, venue_idx, toss_bat_flag]]
    )
    dmatrix = xgb.DMatrix(X)
    prob_team1 = float(bst.predict(dmatrix)[0])
    return prob_team1


if __name__ == "__main__":
    train_and_save()

