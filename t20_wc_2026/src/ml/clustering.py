"""
ML Model 3: Player Role Clustering (K-Means, k=5)
Clusters players into cricket archetypes.
"""

import json
import os
import pickle
import sys

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(__file__))
from features import build_player_features, normalize_gender_value  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
MODELS_DIR = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

CLUSTER_LABELS = {
    0: "⚡ Aggressive Batter",
    1: "🛡️ Anchor / Accumulator",
    2: "🎳 Pure Bowler",
    3: "🔄 All-Rounder",
    4: "💀 Death Specialist",
}


def _resolve_scope(gender: str | None) -> tuple[str, str]:
    scope = normalize_gender_value(gender, default="all")
    suffix = f"_{scope}" if scope in {"male", "female"} else ""
    return scope, suffix


def train_clustering(gender: str | None = None):
    scope, suffix = _resolve_scope(gender)
    print("\n" + "=" * 55)
    print(f"👥 MODEL 3: Player Clustering (K-Means, k=5) [{scope.upper()}]")
    print("=" * 55)

    df = build_player_features(gender=scope if scope != "all" else None, strict_gender=scope in {"male", "female"})
    if df.empty:
        raise ValueError(f"No player features found for scope '{scope}'")

    FEATURE_COLS = ["total_runs", "strike_rate_live", "sixes", "wickets", "economy_live"]
    X = df[FEATURE_COLS].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Elbow method for reference
    print("  Inertias for k=2..8:")
    for k in range(2, 9):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        print(f"    k={k}: {km.inertia_:.1f}")

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10, max_iter=300)
    kmeans.fit(X_scaled)

    df["cluster"] = kmeans.labels_
    df["player_type"] = df["cluster"].map(CLUSTER_LABELS)

    sil_score = silhouette_score(X_scaled, kmeans.labels_)
    print(f"\n  📊 Silhouette Score: {sil_score:.4f}")

    summary = df.groupby("player_type")[FEATURE_COLS].mean().round(2)
    print(f"\n  🔍 Cluster Centroids:")
    print(summary.to_string())

    print(f"\n  📦 Cluster Sizes:")
    print(df["player_type"].value_counts().to_string())

    model_filename = f"player_clustering_kmeans{suffix}.pkl"
    result_filename = f"player_clusters{suffix}.csv"

    with open(os.path.join(MODELS_DIR, model_filename), "wb") as f:
        pickle.dump(
            {"model": kmeans, "scaler": scaler, "features": FEATURE_COLS, "labels": CLUSTER_LABELS},
            f,
        )

    df[["player_name", "player_type", "cluster"] + FEATURE_COLS].to_csv(
        os.path.join(RESULTS_DIR, result_filename), index=False
    )

    print(f"  ✅ Saved → models/{model_filename}")
    print(f"  ✅ Saved → results/{result_filename}")

    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    try:
        with open(metrics_path) as f:
            m = json.load(f)
    except Exception:
        m = {}
    metric_key = "player_clustering" if scope == "all" else f"player_clustering_{scope}"
    m[metric_key] = {
        "silhouette_score": round(sil_score, 4),
        "n_clusters": 5,
        "cluster_labels": list(CLUSTER_LABELS.values()),
        "scope": scope,
    }
    with open(metrics_path, "w") as f:
        json.dump(m, f, indent=2)

    return df


if __name__ == "__main__":
    for model_scope in ["male", "female", None]:
        train_clustering(model_scope)
