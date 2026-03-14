import os
import random
from functools import lru_cache

import numpy as np
import pandas as pd
import xgboost as xgb


LIVE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "live_model.json")


def _prepare_synthetic_states():
    base = os.path.dirname(__file__)
    default_path = os.path.join(base, "..", "10", "matches.csv")
    matches_path = os.getenv("MATCHES_DATA_PATH", default_path)
    df = pd.read_csv(matches_path)

    rows = []
    for _, row in df.iterrows():
        winner = row["winner"]
        team1 = row["team1"]
        team2 = row["team2"]

        # Synthetic target and progression
        target = random.randint(140, 210)
        for over in range(1, 21):
            balls = over * 6
            frac = balls / 120
            base_runs = target * frac
            noise = random.uniform(-10, 10)
            runs = max(0, base_runs + noise)
            wickets = min(9, int(random.random() * over))

            chasing_team = team2
            chasing_won = winner == chasing_team

            rows.append(
                {
                    "over": over,
                    "runs": runs,
                    "wickets": wickets,
                    "target": target,
                    "label": 1 if chasing_won else 0,
                }
            )

    states = pd.DataFrame(rows)
    states["rrr"] = (states["target"] - states["runs"]).clip(lower=0) / (
        (20 - states["over"]).clip(lower=1)
    )
    states["crr"] = states["runs"] / states["over"].replace(0, 1)

    features = states[["over", "runs", "wickets", "target", "rrr", "crr"]]
    labels = states["label"]
    return xgb.DMatrix(features, label=labels)


def train_and_save_live():
    dtrain = _prepare_synthetic_states()
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "eta": 0.1,
    }
    bst = xgb.train(params, dtrain, num_boost_round=80)
    os.makedirs(os.path.dirname(LIVE_MODEL_PATH), exist_ok=True)
    bst.save_model(LIVE_MODEL_PATH)


@lru_cache()
def load_live_model():
    if not os.path.exists(LIVE_MODEL_PATH):
        train_and_save_live()
    bst = xgb.Booster()
    bst.load_model(LIVE_MODEL_PATH)
    return bst


def predict_live_win_probability(
    runs: float,
    wickets: int,
    overs: float,
    target: float,
) -> float:
    bst = load_live_model()
    rrr = (target - runs) / max(20 - overs, 1)
    crr = runs / max(overs, 1)
    features = pd.DataFrame(
        [[overs, runs, wickets, target, rrr, crr]],
        columns=["over", "runs", "wickets", "target", "rrr", "crr"],
    )
    dmatrix = xgb.DMatrix(features)
    prob = float(bst.predict(dmatrix)[0])
    return prob


if __name__ == "__main__":
    train_and_save_live()

