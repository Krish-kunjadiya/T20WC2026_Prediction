"""
PAGE 5: Tournament Strategist Dashboard
Persona: Tournament Director / Team Management
KPIs: Points table, NRR, qualification probability,
      knockout bracket, group stage standings
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Strategist", page_icon="🏆", layout="wide")
st.title("🏆 Tournament Strategist Dashboard")
st.caption("Persona: Tournament Strategist | Focus: Standings, NRR, Qualification")

engine = get_engine()
matches = query(engine, "SELECT * FROM silver.clean_matches")

# -- BUILD POINTS TABLE -------------------------------------------
st.markdown("### 📋 Current Points Table")

try:
    teams_all = pd.concat([matches["team1"], matches["team2"]]).unique()
    records = []

    for team in teams_all:
        team_matches = matches[(matches["team1"] == team) | (matches["team2"] == team)]
        played = len(team_matches)
        won = len(team_matches[team_matches["winner"] == team])
        lost = played - won
        pts = won * 2

        # NRR approximation from win margins.
        runs_for = team_matches.apply(lambda r: r["win_by_runs"] if r["winner"] == team else 0, axis=1).sum()
        runs_against = team_matches.apply(lambda r: r["win_by_runs"] if r["winner"] != team else 0, axis=1).sum()
        nrr = round((runs_for - runs_against) / max(played, 1) * 0.1, 3)

        records.append({"Team": team, "P": played, "W": won, "L": lost, "Pts": pts, "NRR": nrr})

    pt = pd.DataFrame(records).sort_values(["Pts", "NRR"], ascending=False).reset_index(drop=True)
    pt.index += 1

    def highlight_top4(row):
        if row.name <= 4:
            return ["background-color: #1a472a"] * len(row)
        return [""] * len(row)

    st.dataframe(
        pt.style.apply(highlight_top4, axis=1).format({"NRR": "{:.3f}"}),
        use_container_width=True,
        height=500,
    )
    st.caption("🟢 Green rows = Top 4 (qualify for knockouts)")
except Exception as exc:
    st.warning(f"Points table: {exc}")

st.divider()

col1, col2 = st.columns(2)

# -- NRR SIMULATOR -------------------------------------------------
with col1:
    st.markdown("### 🧮 NRR Impact Simulator")
    st.caption("How does winning margin affect qualification?")

    sel_team = st.selectbox("Select Team", pt["Team"].tolist())
    margin_runs = st.slider("Win by X runs (hypothetical)", 1, 100, 20)

    if st.button("📊 Simulate NRR Impact"):
        current_nrr = float(pt[pt["Team"] == sel_team]["NRR"].values[0])
        new_nrr = round(current_nrr + margin_runs * 0.005, 3)
        new_rank = int((pt["NRR"] > new_nrr).sum()) + 1

        st.metric("Current NRR", f"{current_nrr:+.3f}")
        st.metric("Projected NRR", f"{new_nrr:+.3f}", delta=f"+{margin_runs*0.005:.3f}")
        st.metric(
            "Projected Rank",
            f"#{new_rank}",
            delta=f"{'↑' if new_rank < int(pt[pt['Team']==sel_team].index[0]) else '↓'}",
        )

# -- QUALIFICATION PROBABILITY ------------------------------------
with col2:
    st.markdown("### 🎯 Qualification Probability")
    try:
        top_n = pt.head(8).copy()
        max_pts = top_n["Pts"].max()
        top_n["Qual %"] = ((top_n["Pts"] / max_pts * 70) + (top_n["NRR"].rank(pct=True) * 30)).clip(0, 100).round(1)

        fig = px.bar(
            top_n,
            x="Team",
            y="Qual %",
            color="Qual %",
            color_continuous_scale="RdYlGn",
            text="Qual %",
            title="Knockout Qualification Probability (%)",
        )
        fig.add_hline(y=50, line_dash="dash", line_color="white", annotation_text="50% threshold")
        fig.update_layout(height=400, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

# -- WIN MARGIN DISTRIBUTION --------------------------------------
st.markdown("### 📊 Win Margin Analysis")
col3, col4 = st.columns(2)

with col3:
    try:
        runs_wins = matches[matches["win_by_runs"] > 0]
        fig = px.histogram(
            runs_wins,
            x="win_by_runs",
            nbins=20,
            color_discrete_sequence=["#636EFA"],
            title="Distribution of Win by Runs",
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

with col4:
    try:
        wkt_wins = matches[matches["win_by_wickets"] > 0]
        fig = px.histogram(
            wkt_wins,
            x="win_by_wickets",
            nbins=10,
            color_discrete_sequence=["#00CC96"],
            title="Distribution of Win by Wickets",
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))
