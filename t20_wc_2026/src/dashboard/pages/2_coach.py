"""
PAGE 2: Coach Dashboard
Persona: Team Coach
KPIs: Player form, strike rate trends, death over economy,
      bowling attack analysis, player availability
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query  # noqa: E402


st.set_page_config(page_title="Coach Dashboard", page_icon="🧑‍💼", layout="wide")
st.title("🧑‍💼 Coach Dashboard")
st.caption("Persona: Team Coach | Focus: Player Form & Match Readiness")

engine = get_engine()

# -- FILTERS ------------------------------------------------------
teams = query(engine, "SELECT DISTINCT team_name FROM gold.dim_team ORDER BY team_name")
selected_team = st.selectbox("🌍 Select Team", teams["team_name"].tolist())

st.divider()

# -- KPI ROW ------------------------------------------------------
st.markdown("### 📊 Team KPIs")
try:
    deliveries = query(
        engine,
        f"""
        SELECT batsman, bowler, batsman_runs, is_wicket,
               total_runs, over_num, batting_team, bowling_team
        FROM silver.clean_deliveries
        WHERE batting_team = '{selected_team}'
           OR bowling_team = '{selected_team}'
    """,
    )

    batting = deliveries[deliveries["batting_team"] == selected_team]
    bowling = deliveries[deliveries["bowling_team"] == selected_team]

    total_runs = int(batting["batsman_runs"].sum())
    total_wkts = int(bowling["is_wicket"].sum())
    avg_sr = round(batting["batsman_runs"].sum() / max(len(batting), 1) * 100, 1)
    death_bowl = bowling[bowling["over_num"] >= 16]
    death_econ = round(death_bowl["total_runs"].sum() / max(len(death_bowl) / 6, 1), 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏏 Total Runs Scored", f"{total_runs:,}")
    c2.metric("🎯 Wickets Taken", f"{total_wkts}")
    c3.metric("⚡ Team Strike Rate", f"{avg_sr}")
    c4.metric("💀 Death Over Economy", f"{death_econ}")
except Exception as exc:
    st.warning(f"KPI error: {exc}")

st.divider()

col1, col2 = st.columns(2)

# -- PLAYER FORM INDEX --------------------------------------------
with col1:
    st.markdown("### 🔥 Top Batters - Run Contribution")
    try:
        bat_df = deliveries[deliveries["batting_team"] == selected_team]
        top_bat = (
            bat_df.groupby("batsman")["batsman_runs"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_bat.columns = ["Player", "Runs"]
        top_bat["Strike Rate"] = (
            bat_df.groupby("batsman")["batsman_runs"]
            .agg(lambda x: round(x.sum() / len(x) * 100, 1))
            .reindex(top_bat["Player"])
            .values
        )
        fig = px.bar(
            top_bat,
            x="Player",
            y="Runs",
            color="Strike Rate",
            color_continuous_scale="RdYlGn",
            title=f"{selected_team} - Batter Performance",
            text="Runs",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# -- BOWLER ECONOMY ------------------------------------------------
with col2:
    st.markdown("### 🎳 Bowler Economy Rate")
    try:
        bowl_df = deliveries[deliveries["bowling_team"] == selected_team]
        bowl_stats = (
            bowl_df.groupby("bowler")
            .agg(
                Wickets=("is_wicket", "sum"),
                Balls=("total_runs", "count"),
                RunsConceded=("total_runs", "sum"),
            )
            .reset_index()
        )
        bowl_stats = bowl_stats[bowl_stats["Balls"] >= 12]
        bowl_stats["Economy"] = round(bowl_stats["RunsConceded"] / (bowl_stats["Balls"] / 6), 2)
        bowl_stats = bowl_stats.sort_values("Economy").head(10)
        fig = px.bar(
            bowl_stats,
            x="bowler",
            y="Economy",
            color="Wickets",
            color_continuous_scale="Blues",
            title=f"{selected_team} - Bowler Economy (lower=better)",
            text="Economy",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

col3, col4 = st.columns(2)

# -- OVER-BY-OVER RUN RATE ----------------------------------------
with col3:
    st.markdown("### 📈 Over-by-Over Run Rate")
    try:
        over_runs = (
            deliveries[deliveries["batting_team"] == selected_team]
            .groupby("over_num")["total_runs"]
            .mean()
            .reset_index()
        )
        over_runs.columns = ["Over", "Avg Runs"]
        over_runs["Phase"] = over_runs["Over"].apply(
            lambda o: "Powerplay" if o <= 6 else "Middle" if o <= 15 else "Death"
        )
        fig = px.bar(
            over_runs,
            x="Over",
            y="Avg Runs",
            color="Phase",
            color_discrete_map={"Powerplay": "#00CC96", "Middle": "#636EFA", "Death": "#EF553B"},
            title=f"{selected_team} - Average Runs per Over",
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

# -- DISMISSAL ANALYSIS -------------------------------------------
with col4:
    st.markdown("### 🚨 Wicket Loss Analysis")
    try:
        wkt_df = query(
            engine,
            f"""
            SELECT dismissal_kind, COUNT(*) as count
            FROM silver.clean_deliveries
            WHERE batting_team = '{selected_team}'
              AND is_wicket = TRUE
            GROUP BY dismissal_kind
            ORDER BY count DESC
        """,
        )
        if not wkt_df.empty:
            fig = px.pie(
                wkt_df,
                names="dismissal_kind",
                values="count",
                title=f"{selected_team} - How Wickets Are Lost",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(str(exc))

st.divider()

# -- PLAYER CARDS --------------------------------------------------
st.markdown("### 🃏 Player Profile Cards")
try:
    players = query(
        engine,
        f"""
        SELECT player_name, role, runs, batting_avg,
               strike_rate, wickets, bowling_avg, economy
        FROM silver.clean_players
        WHERE country = '{selected_team}'
        ORDER BY runs DESC
        LIMIT 11
    """,
    )
    if players.empty:
        players = query(engine, "SELECT * FROM silver.clean_players ORDER BY runs DESC LIMIT 11")

    for i in range(0, min(len(players), 11), 4):
        cols = st.columns(4)
        for j, (_, player_row) in enumerate(players.iloc[i : i + 4].iterrows()):
            with cols[j]:
                st.markdown(
                    f"""
                <div style='background:#1e1e2e;padding:12px;
                            border-radius:10px;border:1px solid #444;
                            margin-bottom:8px;'>
                  <b>🏏 {player_row['player_name']}</b><br>
                  <small>{player_row.get('role','-')}</small><br><br>
                  Runs: <b>{int(player_row.get('runs',0)):,}</b><br>
                  Avg:  <b>{round(float(player_row.get('batting_avg',0)),1)}</b><br>
                  SR:   <b>{round(float(player_row.get('strike_rate',0)),1)}</b><br>
                  Wkts: <b>{int(player_row.get('wickets',0))}</b>
                </div>
                """,
                    unsafe_allow_html=True,
                )
except Exception as exc:
    st.warning(f"Player cards: {exc}")
