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
from sqlalchemy import create_engine

sys.path.append(os.path.dirname(__file__))
from features import build_match_features  # noqa: E402

load_dotenv()

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


# -- MODEL 4: ASSOCIATION RULES ---------------------------------------
def train_association_rules():
    print("\n" + "=" * 55)
    print("🔗 MODEL 4: Association Rules (Winning Conditions)")
    print("=" * 55)

    DATABASE_URL = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    engine = create_engine(DATABASE_URL)
    matches = pd.read_sql("SELECT * FROM silver.clean_matches", engine)

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

    with open(os.path.join(MODELS_DIR, "association_rules.pkl"), "wb") as f:
        pickle.dump({"rules": rules, "te": te}, f)

    rules.to_csv(os.path.join(RESULTS_DIR, "association_rules.csv"), index=False)
    print("  ✅ Saved → models/association_rules.pkl")


# -- MODEL 5: UPSET DETECTION -----------------------------------------
def train_upset_model():
    print("\n" + "=" * 55)
    print("⚠️  MODEL 5: Upset Detection (Logistic Regression)")
    print("=" * 55)

    df = build_match_features()

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

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

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

    with open(os.path.join(MODELS_DIR, "upset_detector_lr.pkl"), "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)

    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    try:
        with open(metrics_path) as f:
            m = json.load(f)
    except Exception:
        m = {}
    m["upset_detection"] = {"roc_auc": str(roc)}
    with open(metrics_path, "w") as f:
        json.dump(m, f, indent=2)

    print("  ✅ Saved → models/upset_detector_lr.pkl")


if __name__ == "__main__":
    train_association_rules()
    train_upset_model()
