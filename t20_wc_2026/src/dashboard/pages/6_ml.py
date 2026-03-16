"""
PAGE 6: ML Predictions Dashboard
- Match outcome predictor
- Score predictor
- Player cluster viewer
- Upset probability meter
- Association rules viewer
"""

import os
import pickle
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Both the dashboard db module and the project results/ live relative to this file.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query, gw, aw, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
st.title("🤖 ML Predictions Dashboard")
st.caption("5 ML models: Match Outcome | Score | Clustering | Association | Upset")

engine = get_engine()
render_sidebar_filters()
_gw = gw()
_aw = aw()

# models/ directory is two levels up from pages/ → src/dashboard/pages → t20_wc_2026/
_PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.abspath(os.path.join(_PAGE_DIR, "..", "..", "..", "models"))
RESULTS_DIR = os.path.abspath(os.path.join(_PAGE_DIR, "..", "..", "..", "results"))


def load_model(filename: str):
    path = os.path.join(MODELS_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


tabs = st.tabs([
    "🎯 Match Predictor",
    "📊 Score Predictor",
    "👥 Player Clusters",
    "🔗 Association Rules",
    "⚠️ Upset Detector",
])

# -- TAB 1: MATCH OUTCOME PREDICTOR -----------------------------------
with tabs[0]:
    st.markdown("### 🎯 Match Outcome Predictor (XGBoost)")
    st.caption("Predict win probability for any T20 WC 2026 matchup")

    artifact = load_model("match_outcome_xgb.pkl")

    matches = query(engine, f"SELECT * FROM silver.clean_matches WHERE TRUE {_gw}")
    deliveries = query(engine, f"SELECT * FROM silver.clean_deliveries WHERE TRUE {_gw} LIMIT 50000")
    teams = sorted(pd.concat([matches["team1"], matches["team2"]]).unique())

    c1, c2, c3 = st.columns(3)
    team_a = c1.selectbox("🏏 Team A", teams, key="pred_ta")
    team_b = c2.selectbox("🏏 Team B", [t for t in teams if t != team_a], key="pred_tb")
    toss_w = c3.selectbox("🪙 Toss Winner", [team_a, team_b], key="pred_tw")
    toss_d = c3.radio("Decision", ["bat", "field"], horizontal=True)

    if st.button("🔮 Predict Match Outcome", type="primary"):
        if artifact:
            model = artifact["model"]
            feat_cols = artifact["features"]

            def team_stat(team, col, df, bowl=False):
                key = "bowling_team" if bowl else "batting_team"
                sub = df[df[key] == team]
                return float(sub[col].mean()) if len(sub) > 0 else 0.0

            wr_a = len(matches[matches["winner"] == team_a]) / max(
                len(matches[(matches["team1"] == team_a) | (matches["team2"] == team_a)]), 1
            )
            wr_b = len(matches[matches["winner"] == team_b]) / max(
                len(matches[(matches["team1"] == team_b) | (matches["team2"] == team_b)]), 1
            )

            features = {
                "run_rate_diff": team_stat(team_a, "batsman_runs", deliveries) - team_stat(team_b, "batsman_runs", deliveries),
                "six_rate_diff": (deliveries[deliveries["batting_team"] == team_a]["batsman_runs"] == 6).mean()
                    - (deliveries[deliveries["batting_team"] == team_b]["batsman_runs"] == 6).mean(),
                "four_rate_diff": (deliveries[deliveries["batting_team"] == team_a]["batsman_runs"] == 4).mean()
                    - (deliveries[deliveries["batting_team"] == team_b]["batsman_runs"] == 4).mean(),
                "pp_run_rate_diff": team_stat(team_a, "total_runs", deliveries[deliveries["over_num"] <= 6])
                    - team_stat(team_b, "total_runs", deliveries[deliveries["over_num"] <= 6]),
                "death_run_rate_diff": team_stat(team_a, "total_runs", deliveries[deliveries["over_num"] >= 16])
                    - team_stat(team_b, "total_runs", deliveries[deliveries["over_num"] >= 16]),
                "wicket_rate_diff": team_stat(team_a, "is_wicket", deliveries, bowl=True)
                    - team_stat(team_b, "is_wicket", deliveries, bowl=True),
                "death_wkt_rate_diff": team_stat(team_a, "is_wicket", deliveries[deliveries["over_num"] >= 16], bowl=True)
                    - team_stat(team_b, "is_wicket", deliveries[deliveries["over_num"] >= 16], bowl=True),
                "economy_diff": team_stat(team_a, "total_runs", deliveries, bowl=True)
                    - team_stat(team_b, "total_runs", deliveries, bowl=True),
                "win_rate_t1": wr_a,
                "win_rate_t2": wr_b,
                "win_rate_diff": wr_a - wr_b,
                "toss_team1": 1 if toss_w == team_a else 0,
                "toss_bat_first": 1 if toss_d == "bat" else 0,
                "toss_advantage": (1 if toss_w == team_a else 0) * (1 if toss_d == "bat" else 0),
                "is_knockout": 0,
            }

            X_input = pd.DataFrame([features])[feat_cols].fillna(0)
            prob = model.predict_proba(X_input)[0]
            prob_a = round(prob[1] * 100, 1)
            prob_b = round(prob[0] * 100, 1)

            st.markdown("---")
            ra, rb = st.columns(2)
            ra.metric(f"🏏 {team_a}", f"{prob_a}%", delta="Predicted Winner" if prob_a > prob_b else None)
            rb.metric(f"🏏 {team_b}", f"{prob_b}%", delta="Predicted Winner" if prob_b >= prob_a else None)

            fig = go.Figure(
                go.Bar(
                    x=[team_a, team_b],
                    y=[prob_a, prob_b],
                    marker_color=[
                        "#00CC96" if prob_a > prob_b else "#EF553B",
                        "#00CC96" if prob_b >= prob_a else "#EF553B",
                    ],
                    text=[f"{prob_a}%", f"{prob_b}%"],
                    textposition="outside",
                )
            )
            fig.update_layout(title="Win Probability", height=380, yaxis_range=[0, 115])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("❌ Model not found. Run: python src/ml/train_models.py")

# -- TAB 2: SCORE PREDICTOR -------------------------------------------
with tabs[1]:
    st.markdown("### 📊 First Innings Score Predictor (LightGBM)")
    artifact = load_model("score_predictor_lgbm.pkl")

    c1, c2, c3 = st.columns(3)
    pp_runs = c1.slider("Powerplay Runs (6 overs)", 20, 80, 50)
    wickets_sc = c2.slider("Wickets Lost so far", 0, 5, 1)
    sixes_sc = c3.slider("Sixes Hit", 0, 20, 5)
    fours_sc = c1.slider("Fours Hit", 0, 30, 10)
    balls_sc = c2.slider("Total Balls Played", 6, 120, 120)

    if st.button("📈 Predict Final Score", type="primary"):
        if artifact:
            model = artifact["model"]
            feat_cols = artifact["features"]
            br_pct = (sixes_sc + fours_sc) / max(balls_sc, 1)
            pp_rr = pp_runs / 6

            X = pd.DataFrame([{
                "total_balls": balls_sc,
                "wickets_lost": wickets_sc,
                "sixes": sixes_sc,
                "fours": fours_sc,
                "pp_runs": pp_runs,
                "pp_run_rate": pp_rr,
                "boundary_pct": br_pct,
            }])[feat_cols]

            pred_score = int(model.predict(X)[0])
            st.success(f"🏏 **Predicted Final Score: {pred_score} runs**")
            st.metric(
                "Predicted Total",
                f"{pred_score}",
                delta="Above avg" if pred_score > 160 else "Below avg",
            )
        else:
            st.error("❌ Model not found. Run: python src/ml/train_models.py")

# -- TAB 3: PLAYER CLUSTERS -------------------------------------------
with tabs[2]:
    st.markdown("### 👥 Player Role Clusters (K-Means)")
    clusters_path = os.path.join(RESULTS_DIR, "player_clusters.csv")
    if os.path.exists(clusters_path):
        df = pd.read_csv(clusters_path)

        for ptype, group in df.groupby("player_type"):
            with st.expander(f"{ptype} — {len(group)} players"):
                st.dataframe(
                    group[["player_name", "total_runs", "strike_rate_live", "wickets", "economy_live"]]
                    .sort_values("total_runs", ascending=False)
                    .head(10),
                    use_container_width=True,
                )

        fig = px.scatter(
            df,
            x="strike_rate_live",
            y="wickets",
            color="player_type",
            size="total_runs",
            hover_name="player_name",
            title="Player Cluster Map: Strike Rate vs Wickets",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Run: python src/ml/clustering.py first")

# -- TAB 4: ASSOCIATION RULES -----------------------------------------
with tabs[3]:
    st.markdown("### 🔗 Winning Condition Rules (Apriori)")
    rules_path = os.path.join(RESULTS_DIR, "association_rules.csv")
    if os.path.exists(rules_path):
        rules = pd.read_csv(rules_path)
        win_rules = (
            rules[rules["consequents"].astype(str).str.contains("won")]
            .sort_values("lift", ascending=False)
            .head(15)
        )
        win_rules = win_rules.copy()
        win_rules["antecedents"] = win_rules["antecedents"].astype(str)
        win_rules["consequents"] = win_rules["consequents"].astype(str)
        win_rules["confidence"] = (win_rules["confidence"] * 100).round(1)
        win_rules["support"] = (win_rules["support"] * 100).round(1)
        win_rules["lift"] = win_rules["lift"].round(3)

        st.dataframe(
            win_rules[["antecedents", "consequents", "support", "confidence", "lift"]],
            use_container_width=True,
        )
        fig = px.bar(
            win_rules.head(8),
            x="antecedents",
            y="confidence",
            color="lift",
            color_continuous_scale="Viridis",
            title="Top Winning Condition Rules by Confidence %",
            text="confidence",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Run: python src/ml/association_upset.py first")

# -- TAB 5: UPSET DETECTOR --------------------------------------------
with tabs[4]:
    st.markdown("### ⚠️ Upset Probability Detector")
    artifact = load_model("upset_detector_lr.pkl")

    matches_up = query(engine, f"SELECT * FROM silver.clean_matches WHERE TRUE {_gw}")
    teams_up = sorted(pd.concat([matches_up["team1"], matches_up["team2"]]).unique())

    fav = st.selectbox("🏆 Favourite Team (higher ranked)", teams_up, key="up_fav")
    under = st.selectbox("🐴 Underdog Team", [t for t in teams_up if t != fav], key="up_und")
    toss_u = st.selectbox("Toss Winner", [fav, under], key="up_toss")

    if st.button("⚠️ Calculate Upset Probability", type="primary"):
        if artifact:
            model = artifact["model"]
            feat_cols = artifact["features"]

            wr_fav = len(matches_up[matches_up["winner"] == fav]) / max(
                len(matches_up[(matches_up["team1"] == fav) | (matches_up["team2"] == fav)]), 1
            )
            wr_und = len(matches_up[matches_up["winner"] == under]) / max(
                len(matches_up[(matches_up["team1"] == under) | (matches_up["team2"] == under)]), 1
            )

            X = pd.DataFrame([{
                "win_rate_diff": wr_fav - wr_und,
                "run_rate_diff": 0.01,
                "toss_team1": 1 if toss_u == fav else 0,
                "toss_bat_first": 1,
                "pp_run_rate_diff": 0.05,
                "death_wkt_rate_diff": 0.01,
                "is_knockout": 0,
            }])[feat_cols]

            prob_upset = round(model.predict_proba(X)[0][1] * 100, 1)

            st.metric(
                "🎲 Upset Probability",
                f"{prob_upset}%",
                delta="HIGH RISK" if prob_upset > 35 else "Normal",
            )

            gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=prob_upset,
                    title={"text": f"Upset Risk: {under} beating {fav}"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#EF553B"},
                        "steps": [
                            {"range": [0, 25], "color": "#1a472a"},
                            {"range": [25, 50], "color": "#ffd700"},
                            {"range": [50, 100], "color": "#8B0000"},
                        ],
                        "threshold": {"line": {"color": "white", "width": 4}, "thickness": 0.75, "value": 50},
                    },
                )
            )
            gauge.update_layout(height=380)
            st.plotly_chart(gauge, use_container_width=True)
        else:
            st.error("❌ Model not found. Run: python src/ml/association_upset.py")
