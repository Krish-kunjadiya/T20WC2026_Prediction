"""
PAGE 4: Commentator / Media Dashboard
Persona: TV Commentator / Sports Journalist
KPIs: Records, milestones, H2H stats, top performers
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Commentator", page_icon="🎙️", layout="wide")
st.title("🎙️ Commentator & Media Dashboard")
st.caption("Persona: Commentator / Media | Focus: Records, Stories, Live Stats")

engine = get_engine()
deliveries = query(engine, "SELECT * FROM silver.clean_deliveries LIMIT 50000")
matches = query(engine, "SELECT * FROM silver.clean_matches")

# -- LIVE STAT TICKER ---------------------------------------------
st.markdown("### 🔴 Live Match Feed")
try:
    live = query(engine, "SELECT * FROM public.live_ball_events ORDER BY event_id DESC LIMIT 6")
    if not live.empty:
        ticker_cols = st.columns(6)
        for i, (_, row) in enumerate(live.iterrows()):
            with ticker_cols[i % 6]:
                color = (
                    "🔴"
                    if row.get("is_wicket")
                    else "💥"
                    if row.get("runs_scored", 0) == 6
                    else "🟢"
                    if row.get("runs_scored", 0) == 4
                    else "⚪"
                )
                st.metric(
                    f"Over {row.get('over_num',0)}.{row.get('ball_num',0)}",
                    f"{color} {row.get('runs_scored',0)} runs",
                )
except Exception:
    st.info("Simulator not running - start simulator.py for live feed")

st.divider()

col1, col2 = st.columns(2)

# -- TOP RUN SCORERS ----------------------------------------------
with col1:
    st.markdown("### 🏆 All-Time Top Run Scorers")
    try:
        top_runs = (
            deliveries.groupby("batsman")["batsman_runs"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_runs.columns = ["Player", "Total Runs"]
        fig = px.bar(
            top_runs,
            x="Player",
            y="Total Runs",
            color="Total Runs",
            color_continuous_scale="Reds",
            text="Total Runs",
            title="Top 10 Run Scorers",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# -- TOP WICKET TAKERS --------------------------------------------
with col2:
    st.markdown("### 🎯 All-Time Top Wicket Takers")
    try:
        top_wkts = (
            deliveries[deliveries["is_wicket"] == True]
            .groupby("bowler")["is_wicket"]
            .count()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_wkts.columns = ["Bowler", "Wickets"]
        fig = px.bar(
            top_wkts,
            x="Bowler",
            y="Wickets",
            color="Wickets",
            color_continuous_scale="Purples",
            text="Wickets",
            title="Top 10 Wicket Takers",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

# -- RECORD HIGHLIGHTS --------------------------------------------
st.markdown("### ⚡ Record Highlights")
try:
    rc1, rc2, rc3, rc4 = st.columns(4)
    highest_score = deliveries.groupby(["match_id", "batsman"])["batsman_runs"].sum().max()
    most_sixes = int((deliveries["batsman_runs"] == 6).sum())
    most_fours = int((deliveries["batsman_runs"] == 4).sum())
    highest_total = deliveries.groupby(["match_id", "batting_team"])["total_runs"].sum().max()

    rc1.metric("🏏 Highest Individual Score", f"{int(highest_score)} runs")
    rc2.metric("💥 Total Sixes in Tournament", f"{most_sixes:,}")
    rc3.metric("🟢 Total Fours in Tournament", f"{most_fours:,}")
    rc4.metric("📊 Highest Team Total", f"{int(highest_total)} runs")
except Exception as exc:
    st.warning(f"Records: {exc}")

st.divider()

# -- SIXES AND TEAM TOTALS ----------------------------------------
col3, col4 = st.columns(2)
with col3:
    st.markdown("### 💥 Most Sixes by Player")
    try:
        sixes = (
            deliveries[deliveries["batsman_runs"] == 6]
            .groupby("batsman")
            .size()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        sixes.columns = ["Player", "Sixes"]
        fig = px.bar(
            sixes,
            x="Player",
            y="Sixes",
            color="Sixes",
            color_continuous_scale="Oranges",
            text="Sixes",
            title="Most Sixes Hit",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

with col4:
    st.markdown("### 📊 Team Total Runs Comparison")
    try:
        team_totals = (
            deliveries.groupby("batting_team")["batsman_runs"]
            .sum()
            .sort_values(ascending=False)
            .head(12)
            .reset_index()
        )
        team_totals.columns = ["Team", "Total Runs"]
        fig = px.bar(
            team_totals,
            x="Team",
            y="Total Runs",
            color="Total Runs",
            color_continuous_scale="Teal",
            text="Total Runs",
            title="Total Runs Scored by Team",
        )
        fig.update_layout(height=380, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))
