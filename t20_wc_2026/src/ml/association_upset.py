"""
ML Model 4: Association Rules (Winning Conditions - Apriori)
ML Model 5: Upset Detection (Logistic Regression)
"""

import json
import os
import pickle
import sys

import pandas as pd
from dotenv import load_dotenv
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(__file__))
from features import build_match_features, load_matches_and_deliveries, normalize_gender_value  # noqa: E402

load_dotenv()

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def _resolve_scope(gender: str | None) -> tuple[str, str]:
    scope = normalize_gender_value(gender, default="all")
    suffix = f"_{scope}" if scope in {"male", "female"} else ""
    return scope, suffix


# -- MODEL 4: ASSOCIATION RULES ---------------------------------------
def train_association_rules(gender: str | None = None):
    scope, suffix = _resolve_scope(gender)
    print("\n" + "=" * 55)
    print(f"🔗 MODEL 4: Association Rules (Winning Conditions) [{scope.upper()}]")
    print("=" * 55)

    matches, _ = load_matches_and_deliveries(
        gender=scope if scope != "all" else None,
        strict_gender=scope in {"male", "female"},
    )
    if matches.empty:
        raise ValueError(f"No matches available for association rules in scope '{scope}'")

    transactions = []
    for _, m in matches.iterrows():
        items = []
        toss_won = m.get("toss_winner") == m.get("winner")
        items.append("toss_won" if toss_won else "toss_lost")
        items.append("chose_bat" if m.get("toss_decision") == "bat" else "chose_bowl")

        phase = m.get("tournament_phase", "Group Stage")
        items.append("knockout_match" if phase in ["Semi Final", "Final"] else "group_match")

        items.append("day_night" if m.get("is_day_night", False) else "day_match")

        won = m.get("winner") == m.get("team1")
        items.append("team1_won" if won else "team2_won")
        transactions.append(items)

    if not transactions:
        raise ValueError(f"No transactions generated for association rules in scope '{scope}'")

    te = TransactionEncoder()
    te_array = te.fit_transform(transactions)
    df_enc = pd.DataFrame(te_array, columns=te.columns_)

    freq_items = apriori(df_enc, min_support=0.2, use_colnames=True)
    if freq_items.empty:
        rules = pd.DataFrame(
            columns=["antecedents", "consequents", "support", "confidence", "lift"]
        )
    else:
        rules = association_rules(freq_items, metric="confidence", min_threshold=0.5)
        rules = rules.sort_values("lift", ascending=False)

    win_rules = (
        rules[rules["consequents"].astype(str).str.contains("won")].head(10)
        if not rules.empty
        else pd.DataFrame()
    )

    print(f"\n  📊 Total Rules Found: {len(rules)}")
    print(f"  🏆 Top Winning Condition Rules:")
    for _, r in win_rules.head(5).iterrows():
        ant = ", ".join(list(r["antecedents"]))
        con = ", ".join(list(r["consequents"]))
        print(f"     {ant} → {con} (conf={r['confidence']:.2f}, lift={r['lift']:.2f})")

    model_filename = f"association_rules{suffix}.pkl"
    result_filename = f"association_rules{suffix}.csv"

    with open(os.path.join(MODELS_DIR, model_filename), "wb") as f:
        pickle.dump({"rules": rules, "te": te}, f)

    rules.to_csv(os.path.join(RESULTS_DIR, result_filename), index=False)
    print(f"  ✅ Saved → models/{model_filename}")
    print(f"  ✅ Saved → results/{result_filename}")


# -- MODEL 5: UPSET DETECTION -----------------------------------------
def train_upset_model(gender: str | None = None):
    scope, suffix = _resolve_scope(gender)
    print("\n" + "=" * 55)
    print(f"⚠️  MODEL 5: Upset Detection (Logistic Regression) [{scope.upper()}]")
    print("=" * 55)

    df = build_match_features(gender=scope if scope != "all" else None, strict_gender=scope in {"male", "female"})
    if df.empty:
        raise ValueError(f"No feature rows available for upset model in scope '{scope}'")

    df["is_upset"] = ((df["win_rate_diff"] > 0.05) & (df["target"] == 0)).astype(int)

    print(
        f"  Upsets in dataset: {df['is_upset'].sum()} / {len(df)} matches "
        f"({df['is_upset'].mean()*100:.1f}%)"
    )

    FEATURES = [
        "win_rate_diff", "run_rate_diff", "toss_team1",
        "toss_bat_first", "pp_run_rate_diff",
        "death_wkt_rate_diff", "is_knockout",
    ]
    X = df[FEATURES].fillna(0)
    y = df["is_upset"]

    if y.nunique() < 2:
        raise ValueError(f"Not enough class diversity to train upset model for scope '{scope}'")

    stratify_y = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify_y)

    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    try:
        roc = round(roc_auc_score(y_test, y_proba) * 100, 2)
    except Exception:
        roc = "N/A (single class in test)"

    print(f"\n  📊 TEST METRICS:")
    print(f"     ROC-AUC: {roc}")
    print(f"\n{classification_report(y_test, y_pred, zero_division=0)}")

    model_filename = f"upset_detector_lr{suffix}.pkl"
    with open(os.path.join(MODELS_DIR, model_filename), "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)

    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    try:
        with open(metrics_path) as f:
            m = json.load(f)
    except Exception:
        m = {}
    metric_key = "upset_detection" if scope == "all" else f"upset_detection_{scope}"
    m[metric_key] = {"roc_auc": str(roc), "scope": scope}
    with open(metrics_path, "w") as f:
        json.dump(m, f, indent=2)

    print(f"  ✅ Saved → models/{model_filename}")


if __name__ == "__main__":
    for model_scope in ["male", "female", None]:
        train_association_rules(model_scope)
        train_upset_model(model_scope)
