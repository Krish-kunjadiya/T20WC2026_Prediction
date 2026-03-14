"""
ML Models 1 & 2:
  Model 1: Match Outcome Prediction (XGBoost Classification)
  Model 2: Score Prediction (LightGBM Regression)
"""

import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from lightgbm import LGBMRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from xgboost import XGBClassifier

sys.path.append(os.path.dirname(__file__))
from features import build_match_features, load_matches_and_deliveries, normalize_gender_value  # noqa: E402

load_dotenv()

# Resolve models/ and results/ relative to repo root (two levels above src/ml/).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

metrics_log: dict = {}


def _resolve_scope(gender: str | None) -> tuple[str, str]:
    scope = normalize_gender_value(gender, default="all")
    suffix = f"_{scope}" if scope in {"male", "female"} else ""
    return scope, suffix


def _metrics_key(base_key: str, scope: str) -> str:
    return base_key if scope == "all" else f"{base_key}_{scope}"


# -- MODEL 1: MATCH OUTCOME CLASSIFICATION ---------------------------
def train_match_outcome_model(gender: str | None = None):
    scope, suffix = _resolve_scope(gender)
    print("\n" + "=" * 55)
    print(f"🤖 MODEL 1: Match Outcome Prediction (XGBoost) [{scope.upper()}]")
    print("=" * 55)

    df = build_match_features(gender=scope if scope != "all" else None, strict_gender=scope in {"male", "female"})
    if df.empty:
        raise ValueError(f"No training rows found for scope '{scope}'")

    FEATURE_COLS = [
        "run_rate_diff", "six_rate_diff", "four_rate_diff",
        "pp_run_rate_diff", "death_run_rate_diff",
        "wicket_rate_diff", "death_wkt_rate_diff", "economy_diff",
        "win_rate_t1", "win_rate_t2", "win_rate_diff",
        "toss_team1", "toss_bat_first", "toss_advantage", "is_knockout",
    ]

    X = df[FEATURE_COLS].fillna(0)
    y = df["target"]

    print(f"  Dataset: {len(X)} matches | Class balance: {y.mean():.2f}")

    if y.nunique() < 2:
        raise ValueError(f"Not enough class diversity to train match model for scope '{scope}'")

    stratify_y = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify_y)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = round(accuracy_score(y_test, y_pred) * 100, 2)
    f1 = round(f1_score(y_test, y_pred, average="weighted") * 100, 2)
    try:
        roc_auc = round(roc_auc_score(y_test, y_proba) * 100, 2)
    except Exception:
        roc_auc = None

    cv_scores = np.array([])
    min_class_count = int(y.value_counts().min())
    cv_folds = min(5, min_class_count)
    if cv_folds >= 2:
        cv_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="accuracy")

    print(f"\n  📊 TEST METRICS:")
    print(f"     Accuracy : {acc}%")
    print(f"     F1 Score : {f1}%")
    print(f"     ROC-AUC  : {f'{roc_auc}%' if roc_auc is not None else 'N/A'}")
    if cv_scores.size:
        print(f"     CV Acc   : {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")
    else:
        print("     CV Acc   : N/A")
    print(
        f"\n{classification_report(y_test, y_pred, labels=[0, 1], target_names=['Team2 Wins', 'Team1 Wins'], zero_division=0)}"
    )

    fi = pd.DataFrame({"Feature": FEATURE_COLS, "Importance": model.feature_importances_}).sort_values(
        "Importance", ascending=False
    )
    print("  🔍 Top 5 Features:")
    print(fi.head(5).to_string(index=False))

    model_filename = f"match_outcome_xgb{suffix}.pkl"
    with open(os.path.join(MODELS_DIR, model_filename), "wb") as f:
        pickle.dump({"model": model, "features": FEATURE_COLS}, f)

    metrics_log[_metrics_key("match_outcome", scope)] = {
        "accuracy": acc,
        "f1": f1,
        "roc_auc": roc_auc,
        "cv_accuracy": round(float(cv_scores.mean()) * 100, 2) if cv_scores.size else None,
        "top_features": fi.head(5)["Feature"].tolist(),
        "scope": scope,
    }
    print(f"  ✅ Saved → models/{model_filename}")
    return model, FEATURE_COLS


# -- MODEL 2: SCORE PREDICTION (REGRESSION) -------------------------
def train_score_model(gender: str | None = None):
    scope, suffix = _resolve_scope(gender)
    print("\n" + "=" * 55)
    print(f"📈 MODEL 2: Score Prediction (LightGBM Regression) [{scope.upper()}]")
    print("=" * 55)

    matches, deliveries = load_matches_and_deliveries(
        gender=scope if scope != "all" else None,
        strict_gender=scope in {"male", "female"},
    )
    if deliveries.empty or matches.empty:
        raise ValueError(f"No deliveries available to train score model for scope '{scope}'")

    innings = (
        deliveries.groupby(["match_id", "batting_team"])
        .agg(
            total_runs=("total_runs", "sum"),
            total_balls=("total_runs", "count"),
            wickets_lost=("is_wicket", "sum"),
            sixes=("batsman_runs", lambda x: (x == 6).sum()),
            fours=("batsman_runs", lambda x: (x == 4).sum()),
            pp_runs=("total_runs", lambda x: x.iloc[: min(36, len(x))].sum()),
        )
        .reset_index()
    )

    innings["run_rate"] = (innings["total_runs"] / (innings["total_balls"] / 6).replace(0, 1)).round(2)
    innings["pp_run_rate"] = (innings["pp_runs"] / 6).round(2)
    innings["boundary_pct"] = (
        (innings["sixes"] + innings["fours"]) / innings["total_balls"].replace(0, 1)
    ).round(4)

    innings = innings[innings["total_runs"] > 50]

    FEATURES = ["total_balls", "wickets_lost", "sixes", "fours", "pp_runs", "pp_run_rate", "boundary_pct"]
    TARGET = "total_runs"

    X = innings[FEATURES].fillna(0)
    y = innings[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LGBMRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    rmse = round(np.sqrt(mean_squared_error(y_test, y_pred)), 2)
    mae = round(mean_absolute_error(y_test, y_pred), 2)
    r2 = round(r2_score(y_test, y_pred), 4)

    print(f"\n  📊 TEST METRICS:")
    print(f"     RMSE : {rmse} runs")
    print(f"     MAE  : {mae} runs")
    print(f"     R²   : {r2}")

    model_filename = f"score_predictor_lgbm{suffix}.pkl"
    with open(os.path.join(MODELS_DIR, model_filename), "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)

    metrics_log[_metrics_key("score_prediction", scope)] = {"rmse": rmse, "mae": mae, "r2": r2, "scope": scope}
    print(f"  ✅ Saved → models/{model_filename}")
    return model, FEATURES


if __name__ == "__main__":
    for model_scope in ["male", "female", None]:
        train_match_outcome_model(model_scope)
        train_score_model(model_scope)
    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics_log, f, indent=2)
    print("\n💾 All metrics saved → results/metrics.json")
