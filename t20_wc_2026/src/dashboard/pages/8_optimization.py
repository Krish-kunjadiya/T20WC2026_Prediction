"""PAGE 8: Optimization Dashboard."""

from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
_PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_PAGE_DIR, "..", "..", ".."))
sys.path.append(_PROJECT_ROOT)

from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Optimization", page_icon="⚙️", layout="wide")
st.title("⚙️ Optimization Dashboard")
st.caption("Playing XI Optimizer | Batting Order | SHAP Explainability")

engine = get_engine()

try:
    from src.ml.optimizer import compute_shap_importance, optimize_batting_order, select_optimal_xi

    OPT_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    OPT_AVAILABLE = False
    st.error(f"Optimizer not available: {exc}")

SHAP_PATH = os.path.join(_PROJECT_ROOT, "results", "shap_importance.csv")

tabs = st.tabs(["🏏 Optimal XI Selector", "📊 Batting Order Optimizer", "🔍 SHAP Feature Importance"])

# -- TAB 1: OPTIMAL XI --------------------------------------------------
with tabs[0]:
    st.markdown("### 🏏 Optimal Playing XI Selector")
    st.caption("Selects best 11 players using composite performance scoring")

    teams = query(engine, "SELECT DISTINCT country FROM silver.clean_players ORDER BY country")
    team_list = ["All Teams"] + teams["country"].dropna().tolist()
    selected = st.selectbox("🌍 Select Country / Team", team_list)

    if st.button("🔮 Select Optimal XI", type="primary"):
        if OPT_AVAILABLE:
            with st.spinner("Computing optimal XI..."):
                xi = select_optimal_xi(None if selected == "All Teams" else selected)
            st.success(f"Optimal XI selected for {selected}")

            st.dataframe(
                xi.style.background_gradient(subset=["perf_score"], cmap="Greens").format(
                    {
                        "batting_avg": "{:.1f}",
                        "strike_rate": "{:.1f}",
                        "bowling_avg": "{:.1f}",
                        "economy": "{:.1f}",
                        "perf_score": "{:.2f}",
                    }
                ),
                use_container_width=True,
                height=460,
            )

            role_dist = xi["role"].value_counts().reset_index()
            role_dist.columns = ["Role", "Count"]
            fig = px.pie(
                role_dist,
                names="Role",
                values="Count",
                title="XI Composition by Role",
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig.update_traces(textinfo="label+percent")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

            fig2 = px.bar(
                xi.sort_values("perf_score", ascending=True),
                x="perf_score",
                y="player_name",
                orientation="h",
                color="perf_score",
                color_continuous_scale="Viridis",
                title="Player Performance Scores",
                text="perf_score",
            )
            fig2.update_layout(height=420)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.error("Optimizer not available")

# -- TAB 2: BATTING ORDER -----------------------------------------------
with tabs[1]:
    st.markdown("### 📊 Batting Order Optimizer")
    st.caption("Arranges XI for maximum scoring potential")

    teams2 = query(engine, "SELECT DISTINCT country FROM silver.clean_players ORDER BY country")
    team_list2 = ["All Teams"] + teams2["country"].dropna().tolist()
    selected2 = st.selectbox("🌍 Select Team", team_list2, key="bo_team")

    if st.button("📊 Optimize Batting Order", type="primary"):
        if OPT_AVAILABLE:
            with st.spinner("Optimizing batting order..."):
                order_df = optimize_batting_order(None if selected2 == "All Teams" else selected2)

            st.success("Batting order optimized")

            for _, row in order_df.iterrows():
                pos = int(row["batting_position"])
                col_color = "#1a472a" if pos <= 2 else "#1a3a5c" if pos <= 5 else "#4a1a1a" if pos <= 7 else "#2a2a2a"
                border_color = "#00CC96" if pos <= 2 else "#636EFA" if pos <= 5 else "#EF553B" if pos <= 7 else "#888"
                st.markdown(
                    f"""
                    <div style='background:{col_color};padding:8px 16px;
                                border-radius:8px;margin:4px 0;
                                display:flex;justify-content:space-between;
                                border-left:4px solid {border_color};'>
                      <span><b>#{pos}</b> &nbsp; {row['player_name']}</span>
                      <span style='color:#aaa'>
                            {row['role_in_order']} |
                            SR: {float(row['sr']):.0f} |
                            Avg: {float(row['avg']):.1f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.divider()

            fig = px.scatter(
                order_df,
                x="sr",
                y="avg",
                text="player_name",
                color="role_in_order",
                size="batting_position",
                title="Batting Position: Strike Rate vs Average",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Optimizer not available")

# -- TAB 3: SHAP IMPORTANCE ---------------------------------------------
with tabs[2]:
    st.markdown("### 🔍 SHAP Feature Importance - Match Outcome Model")
    st.caption("Which features most influence the XGBoost win prediction?")

    if not os.path.exists(SHAP_PATH):
        if st.button("🔬 Compute SHAP Values", type="primary"):
            if OPT_AVAILABLE:
                with st.spinner("Computing SHAP values (may take ~30s)..."):
                    shap_df = compute_shap_importance()
                if shap_df.empty:
                    st.error("SHAP computation did not return data")
                else:
                    st.success("SHAP values computed")
                    st.rerun()
    else:
        shap_df = pd.read_csv(SHAP_PATH)

        fig = px.bar(
            shap_df.sort_values("SHAP_Value"),
            x="SHAP_Value",
            y="Feature",
            orientation="h",
            color="SHAP_Value",
            color_continuous_scale="RdYlGn",
            title="SHAP Feature Importance - Match Outcome Prediction",
            text=shap_df["SHAP_Value"].round(4).astype(str),
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 Feature Importance Table")
        st.dataframe(
            shap_df.style.background_gradient(subset=["SHAP_Value"], cmap="Greens").format({"SHAP_Value": "{:.6f}"}),
            use_container_width=True,
        )

        st.info(
            """
            How to read SHAP values:
            - Higher value means more influence on prediction
            - win_rate_diff near the top means historical win rate is a strong predictor
            - toss_team1 indicates toss impact
            - death_wkt_rate_diff indicates death bowling importance
            """
        )
