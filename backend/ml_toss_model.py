import os
from functools import lru_cache

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split


MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "toss_model.json")


def _load_matches() -> pd.DataFrame:
    base = os.path.dirname(__file__)
    default_path = os.path.join(base, "..", "10", "matches.csv")
    data_path = os.getenv("MATCHES_DATA_PATH", default_path)
    return pd.read_csv(data_path)


def _prepare_training_data():
    df = _load_matches().copy()
    # Only matches where toss decision is known and not abandoned
    df = df[df["toss_decision"].isin(["bat", "field"])]
    df = df[df["winner"].notna()]

    # Encode teams and venue
    teams = pd.unique(df[["team1", "team2"]].values.ravel("K"))
    team_to_idx = {t: i for i, t in enumerate(teams)}
    venues = df["venue"].unique()
    venue_to_idx = {v: i for i, v in enumerate(venues)}

    def encode_row(row):
        return [
            team_to_idx.get(row["team1"], -1),
            team_to_idx.get(row["team2"], -1),
            venue_to_idx.get(row["venue"], -1),
        ]

    X = df.apply(encode_row, axis=1, result_type="expand")

    # Label: was batting first the better decision?
    # If team winning the toss batted first and won, or bowled and lost -> 1 (bat first good)
    # Otherwise 0 (bowl first better)
    def label_row(row):
        toss_bat = row["toss_decision"] == "bat"
        toss_team_won = row["toss_winner"] == row["winner"]
        if toss_bat and toss_team_won:
            return 1
        if (not toss_bat) and (not toss_team_won) and row["winner"] != "No Result":
            return 1
        return 0

    y = df.apply(label_row, axis=1)
    return X, y, team_to_idx, venue_to_idx


def train_and_save():
    X, y, team_to_idx, venue_to_idx = _prepare_training_data()
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "eta": 0.1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "lambda": 1.0,
        "alpha": 0.0,
    }
    evals = [(dtrain, "train"), (dval, "val")]
    bst = xgb.train(params, dtrain, num_boost_round=300, evals=evals, early_stopping_rounds=20)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    bst.save_model(MODEL_PATH)

    mapping_base = os.path.join(os.path.dirname(MODEL_PATH), "toss_mappings")
    pd.DataFrame(
        {"team": list(team_to_idx.keys()), "team_idx": list(team_to_idx.values())}
    ).to_parquet(mapping_base + "_teams.parquet")
    pd.DataFrame(
        {"venue": list(venue_to_idx.keys()), "venue_idx": list(venue_to_idx.values())}
    ).to_parquet(mapping_base + "_venues.parquet")


@lru_cache()
def load_toss_model_and_mappings():
    if not os.path.exists(MODEL_PATH):
        train_and_save()
    bst = xgb.Booster()
    bst.load_model(MODEL_PATH)
    mapping_base = os.path.join(os.path.dirname(MODEL_PATH), "toss_mappings")
    teams_df = pd.read_parquet(mapping_base + "_teams.parquet")
    venues_df = pd.read_parquet(mapping_base + "_venues.parquet")
    team_to_idx = dict(zip(teams_df["team"], teams_df["team_idx"]))
    venue_to_idx = dict(zip(venues_df["venue"], venues_df["venue_idx"]))
    return bst, team_to_idx, venue_to_idx


def recommend_toss_decision(team: str, opponent: str, venue: str):
    bst, team_to_idx, venue_to_idx = load_toss_model_and_mappings()
    t1 = team_to_idx.get(team, -1)
    t2 = team_to_idx.get(opponent, -1)
    v = venue_to_idx.get(venue, -1)
    X = pd.DataFrame([[t1, t2, v]]) # Fix XGBoost feature mismatch
    dmatrix = xgb.DMatrix(X)
    prob_bat_first_good = float(bst.predict(dmatrix)[0])
    decision = "bat" if prob_bat_first_good >= 0.5 else "bowl"
    return decision, prob_bat_first_good


if __name__ == "__main__":
    train_and_save()

