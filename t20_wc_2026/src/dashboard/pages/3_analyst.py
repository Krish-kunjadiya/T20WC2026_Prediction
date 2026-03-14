"""
PAGE 3: Team Analyst Dashboard
Persona: Data Analyst / Strategist
KPIs: Win probability, batting depth, bowling variety,
      toss advantage, venue performance
"""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Team Analyst", page_icon="📈", layout="wide")
st.title("📈 Team Analyst Dashboard")
st.caption("Persona: Team Analyst | Focus: Strategy & Win Probability")

engine = get_engine()
matches = query(engine, "SELECT * FROM silver.clean_matches")
deliveries = query(engine, "SELECT * FROM silver.clean_deliveries LIMIT 50000")

# -- WIN PROBABILITY SIMULATOR ------------------------------------
st.markdown("### 🎯 Match Win Probability Simulator")
teams = sorted(pd.concat([matches["team1"], matches["team2"]]).unique())

c1, c2, c3 = st.columns(3)
team_a = c1.selectbox("Team A", teams, index=0)
team_b = c2.selectbox("Team B", teams, index=1)
toss_win = c3.selectbox("Toss Winner", [team_a, team_b])

if st.button("🔮 Calculate Win Probability"):
    h2h = matches[
        ((matches["team1"] == team_a) & (matches["team2"] == team_b))
        | ((matches["team1"] == team_b) & (matches["team2"] == team_a))
    ]
    total = len(h2h)
    a_wins = len(h2h[h2h["winner"] == team_a])
    toss_boost = 5 if toss_win == team_a else -5

    if total > 0:
        prob_a = round((a_wins / total * 100) + toss_boost, 1)
        prob_a = min(max(prob_a, 0), 100)
        prob_b = round(100 - prob_a, 1)
    else:
        prob_a, prob_b = 50 + toss_boost, 50 - toss_boost

    st.markdown(f"#### Based on {total} H2H matches + toss advantage:")
    ga, gb = st.columns(2)
    ga.metric(
        f"🏏 {team_a} Win Probability",
        f"{prob_a}%",
        delta=f"+{toss_boost}% toss boost" if toss_win == team_a else None,
    )
    gb.metric(
        f"🏏 {team_b} Win Probability",
        f"{prob_b}%",
        delta=f"+{abs(toss_boost)}% toss boost" if toss_win == team_b else None,
    )

    fig = go.Figure(
        go.Bar(
            x=[team_a, team_b],
            y=[prob_a, prob_b],
            marker_color=["#00CC96", "#EF553B"],
            text=[f"{prob_a}%", f"{prob_b}%"],
            textposition="outside",
        )
    )
    fig.update_layout(title="Win Probability", height=350, yaxis_range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)

st.divider()

col1, col2 = st.columns(2)

# -- BATTING DEPTH SCORE ------------------------------------------
with col1:
    st.markdown("### 🏏 Batting Depth Score by Team")
    try:
        bat_depth = deliveries.groupby(["batting_team", "batsman"])["batsman_runs"].sum().reset_index()
        team_depth = (
            bat_depth.groupby("batting_team")
            .agg(Total_Runs=("batsman_runs", "sum"), Unique_Batters=("batsman", "nunique"))
            .reset_index()
        )
        team_depth["Depth_Score"] = round(team_depth["Total_Runs"] / team_depth["Unique_Batters"], 1)
        team_depth = team_depth.sort_values("Depth_Score", ascending=False).head(12)
        fig = px.bar(
            team_depth,
            x="batting_team",
            y="Depth_Score",
            color="Depth_Score",
            color_continuous_scale="Greens",
            title="Batting Depth Score (Runs per Batter Used)",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# -- BOWLING VARIETY INDEX ----------------------------------------
with col2:
    st.markdown("### 🎳 Bowling Variety Index by Team")
    try:
        bowl_var = deliveries.groupby(["bowling_team", "bowler"])["is_wicket"].sum().reset_index()
        variety = (
            bowl_var.groupby("bowling_team")
            .agg(Total_Wickets=("is_wicket", "sum"), Unique_Bowlers=("bowler", "nunique"))
            .reset_index()
        )
        variety["Variety_Index"] = round(variety["Total_Wickets"] / variety["Unique_Bowlers"], 2)
        variety = variety.sort_values("Variety_Index", ascending=False).head(12)
        fig = px.bar(
            variety,
            x="bowling_team",
            y="Variety_Index",
            color="Variety_Index",
            color_continuous_scale="Blues",
            title="Bowling Variety Index (Wickets per Bowler Used)",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

col3, col4 = st.columns(2)

# -- TOSS ADVANTAGE ANALYSIS --------------------------------------
with col3:
    st.markdown("### 🪙 Toss Win -> Match Win Rate per Team")
    try:
        toss_df = matches.copy()
        toss_df["toss_helped"] = toss_df["toss_winner"] == toss_df["winner"]
        toss_rate = toss_df.groupby("toss_winner")["toss_helped"].agg(["mean", "count"]).reset_index()
        toss_rate.columns = ["Team", "Win Rate", "Matches"]
        toss_rate = toss_rate[toss_rate["Matches"] >= 3]
        toss_rate["Win Rate"] = (toss_rate["Win Rate"] * 100).round(1)
        toss_rate = toss_rate.sort_values("Win Rate", ascending=False)
        fig = px.bar(
            toss_rate,
            x="Team",
            y="Win Rate",
            color="Win Rate",
            color_continuous_scale="RdYlGn",
            title="Win Rate When Toss is Won (%)",
            text="Win Rate",
        )
        fig.add_hline(y=50, line_dash="dash", line_color="white", annotation_text="50% baseline")
        fig.update_layout(height=380, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# -- PHASE-WISE RUN RATE ------------------------------------------
with col4:
    st.markdown("### ⚡ Phase-wise Run Rate - Top 8 Teams")
    try:
        del_phase = deliveries.copy()
        del_phase["phase"] = del_phase["over_num"].apply(
            lambda o: "Powerplay" if o <= 6 else "Middle" if o <= 15 else "Death"
        )
        top_teams = deliveries.groupby("batting_team")["batsman_runs"].sum().nlargest(8).index.tolist()
        phase_runs = (
            del_phase[del_phase["batting_team"].isin(top_teams)]
            .groupby(["batting_team", "phase"])["total_runs"]
            .mean()
            .reset_index()
        )
        phase_runs.columns = ["Team", "Phase", "Avg Runs/Over"]
        phase_runs["Avg Runs/Over"] = phase_runs["Avg Runs/Over"].round(2)
        fig = px.bar(
            phase_runs,
            x="Team",
            y="Avg Runs/Over",
            color="Phase",
            barmode="group",
            color_discrete_map={"Powerplay": "#00CC96", "Middle": "#636EFA", "Death": "#EF553B"},
            title="Phase-wise Avg Runs per Over",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))
