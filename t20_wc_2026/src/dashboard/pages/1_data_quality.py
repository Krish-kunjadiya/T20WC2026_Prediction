"""
PAGE 1: Data Quality & EDA Dashboard
- Quality scorecard
- Null %, duplicate %, row counts
- EDA charts: top scorers, win %, venue scores, H2H heatmap
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Data Quality & EDA", page_icon="📊", layout="wide")
st.title("📊 Data Quality & Exploratory Data Analysis")

engine = get_engine()

# -- SECTION 1: DATA QUALITY SCORECARD ---------------------------------
st.markdown("## 🔍 Data Quality Scorecard")

tables = {
    "silver.clean_matches": "Matches",
    "silver.clean_deliveries": "Deliveries",
    "silver.clean_players": "Players",
    "silver.clean_venues": "Venues",
}

cols = st.columns(len(tables))
for i, (tbl, label) in enumerate(tables.items()):
    try:
        df = query(engine, f"SELECT * FROM {tbl} LIMIT 5000")
        null_pct = round(df.isnull().mean().mean() * 100, 1)
        dup_count = int(df.duplicated().sum())
        row_count = int(query(engine, f"SELECT COUNT(*) AS c FROM {tbl}").iloc[0, 0])
        health = "🟢 Healthy" if null_pct < 5 and dup_count == 0 else "🟡 Warning"
        with cols[i]:
            st.metric(f"{label} Rows", f"{row_count:,}")
            st.metric("Null %", f"{null_pct}%")
            st.metric("Duplicates", f"{dup_count}")
            st.caption(health)
    except Exception as exc:
        cols[i].error(f"{label}: {exc}")

st.divider()

# -- SECTION 2: NULL HEATMAP -------------------------------------------
st.markdown("## 🟥 Null Value Heatmap - Silver Layer")
try:
    matches = query(engine, "SELECT * FROM silver.clean_matches")
    null_df = pd.DataFrame(
        {
            "Column": matches.columns,
            "Null %": (matches.isnull().mean() * 100).round(2).values,
        }
    ).sort_values("Null %", ascending=False)
    fig = px.bar(
        null_df,
        x="Column",
        y="Null %",
        color="Null %",
        color_continuous_scale="RdYlGn_r",
        title="Null % per Column - clean_matches",
    )
    fig.update_layout(height=350, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)
except Exception as exc:
    st.warning(f"Null heatmap: {exc}")

st.divider()

# -- SECTION 3: EDA CHARTS ---------------------------------------------
st.markdown("## 📈 Exploratory Data Analysis")

matches = query(engine, "SELECT * FROM silver.clean_matches")
players = query(engine, "SELECT * FROM silver.clean_players")
deliveries = query(
    engine,
    "SELECT batsman, batsman_runs, bowling_team FROM silver.clean_deliveries LIMIT 50000",
)

col1, col2 = st.columns(2)

# Top Run Scorers
with col1:
    st.markdown("### 🏏 Top 10 Run Scorers")
    try:
        top_bat = (
            deliveries.groupby("batsman")["batsman_runs"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_bat.columns = ["Player", "Runs"]
        fig = px.bar(
            top_bat,
            x="Runs",
            y="Player",
            orientation="h",
            color="Runs",
            color_continuous_scale="Blues",
            title="Top 10 Run Scorers",
        )
        fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# Win % by Toss Decision
with col2:
    st.markdown("### 🎯 Win % by Toss Decision")
    try:
        toss = matches.copy()
        toss["toss_won"] = toss["toss_winner"] == toss["winner"]
        toss_summary = toss.groupby("toss_decision")["toss_won"].mean().reset_index()
        toss_summary.columns = ["Toss Decision", "Win %"]
        toss_summary["Win %"] = (toss_summary["Win %"] * 100).round(1)
        fig = px.pie(
            toss_summary,
            names="Toss Decision",
            values="Win %",
            title="Toss Decision vs Win %",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

col3, col4 = st.columns(2)

# Matches per team
with col3:
    st.markdown("### 🌍 Matches Played per Team")
    try:
        team_counts = pd.concat([matches["team1"], matches["team2"]]).value_counts().head(15).reset_index()
        team_counts.columns = ["Team", "Matches"]
        fig = px.bar(
            team_counts,
            x="Team",
            y="Matches",
            color="Matches",
            color_continuous_scale="Viridis",
            title="Matches Played per Team",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# Score Distribution
with col4:
    st.markdown("### 📦 Runs per Ball Distribution")
    try:
        runs_dist = deliveries["batsman_runs"].value_counts().reset_index()
        runs_dist.columns = ["Runs", "Count"]
        runs_dist = runs_dist.sort_values("Runs")
        fig = px.bar(
            runs_dist,
            x="Runs",
            y="Count",
            color="Count",
            color_continuous_scale="Oranges",
            title="Frequency of Each Run Value per Ball",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

# -- SECTION 4: TEAM H2H WIN MATRIX ------------------------------------
st.markdown("## 🔥 Team Head-to-Head Win Matrix")
try:
    h2h = matches[matches["winner"].notna()].copy()
    teams_list = sorted(pd.concat([h2h["team1"], h2h["team2"]]).unique())[:12]
    matrix = pd.DataFrame(0, index=teams_list, columns=teams_list)

    for _, row in h2h.iterrows():
        t1, t2, winner = row.get("team1"), row.get("team2"), row.get("winner")
        if t1 in teams_list and t2 in teams_list and winner in teams_list:
            matrix.loc[winner, t2 if winner == t1 else t1] += 1

    fig = px.imshow(
        matrix,
        color_continuous_scale="Blues",
        title="H2H Wins (Row Team beat Column Team)",
        aspect="auto",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
except Exception as exc:
    st.warning(f"H2H Matrix: {exc}")

st.divider()

# -- SECTION 5: LIVE SIMULATOR FEED ------------------------------------
st.markdown("## 🔴 Live Ball Events (Simulator Feed)")
try:
    live = query(engine, "SELECT * FROM public.live_ball_events ORDER BY event_id DESC LIMIT 12")
    st.dataframe(live, use_container_width=True)
    if st.button("🔄 Refresh Live Feed"):
        st.cache_data.clear()
        st.rerun()
except Exception as exc:
    st.warning(f"Live feed: {exc}")
