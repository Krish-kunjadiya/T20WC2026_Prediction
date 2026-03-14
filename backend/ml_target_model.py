import os
from functools import lru_cache

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split


MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "target_model.json")


def _load_matches() -> pd.DataFrame:
    base = os.path.dirname(__file__)
    default_path = os.path.join(base, "..", "10", "matches.csv")
    data_path = os.getenv("MATCHES_DATA_PATH", default_path)
    return pd.read_csv(data_path)


def _prepare_training_data():
    df = _load_matches().copy()
    # Approximate first innings score from margin when result is by runs
    # For simplicity, use random synthetic but conditioned on venue and teams.
    df = df[df["result"].notna()]

    venues = df["venue"].unique()
    venue_to_idx = {v: i for i, v in enumerate(venues)}

    def make_score(row):
        # Use a simple heuristic: high margins -> high scores at that venue
        margin_str = str(row["margin"])
        base = 160
        if "runs" in margin_str:
            try:
                runs = int(margin_str.split()[0])
            except Exception:
                runs = 20
            return base + runs
        return base + 10

    df["first_innings_score"] = df.apply(make_score, axis=1)

    def encode_row(row):
        return [
            venue_to_idx.get(row["venue"], -1),
        ]

    X = df.apply(encode_row, axis=1, result_type="expand")
    y = df["first_innings_score"]
    return X, y, venue_to_idx


def train_and_save():
    X, y, venue_to_idx = _prepare_training_data()
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    params = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "max_depth": 4,
        "eta": 0.1,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    }
    evals = [(dtrain, "train"), (dval, "val")]
    bst = xgb.train(params, dtrain, num_boost_round=300, evals=evals, early_stopping_rounds=20)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    bst.save_model(MODEL_PATH)

    mapping_path = os.path.join(os.path.dirname(MODEL_PATH), "target_mappings_venues.parquet")
    pd.DataFrame(
        {"venue": list(venue_to_idx.keys()), "venue_idx": list(venue_to_idx.values())}
    ).to_parquet(mapping_path)


@lru_cache()
def load_target_model_and_mappings():
    if not os.path.exists(MODEL_PATH):
        train_and_save()
    bst = xgb.Booster()
    bst.load_model(MODEL_PATH)
    venues_df = pd.read_parquet(
        os.path.join(os.path.dirname(MODEL_PATH), "target_mappings_venues.parquet")
    )
    venue_to_idx = dict(zip(venues_df["venue"], venues_df["venue_idx"]))
    return bst, venue_to_idx


def predict_par_score(venue: str):
    bst, venue_to_idx = load_target_model_and_mappings()
    v = venue_to_idx.get(venue, -1)
    X = pd.DataFrame([[v]])
    dmatrix = xgb.DMatrix(X)
    score = float(bst.predict(dmatrix)[0])
    return score


if __name__ == "__main__":
    train_and_save()

