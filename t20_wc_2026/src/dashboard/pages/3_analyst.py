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
from db import get_engine, query, gw, aw, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Team Analyst", page_icon="📈", layout="wide")
st.title("📈 Team Analyst Dashboard")
st.caption("Persona: Team Analyst | Focus: Strategy & Win Probability")

engine = get_engine()
render_sidebar_filters()
_gw = gw()
_aw = aw()
matches = query(engine, f"SELECT * FROM silver.clean_matches WHERE TRUE {_gw}")
deliveries = query(
    engine,
    f"""SELECT match_id, inning, over_num, ball_num, batting_team, bowling_team,
        batsman, bowler, batsman_runs, extra_runs, total_runs,
        is_wicket, dismissal_kind
    FROM silver.clean_deliveries WHERE TRUE {_gw}""",
)

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

st.divider()
st.markdown("### 🧠 Additional Cricsheet-Driven Analyst Insights")
st.caption(
    "Mapped to CricSheet availability: expected first-innings score, venue win %, H2H dominance, toss impact, batting-vs-bowling matchup, upset proxy, dot-ball pressure, and qualification approximation."
)

try:
    all_teams = sorted(pd.concat([matches["team1"], matches["team2"]]).dropna().astype(str).unique().tolist())
    all_venues = sorted(matches["venue"].dropna().astype(str).unique().tolist())

    a1, a2, a3 = st.columns(3)
    ana_team = a1.selectbox("Team", all_teams, key="ana_team")
    ana_opp = a2.selectbox("Opponent", [t for t in all_teams if t != ana_team], key="ana_opp")
    ana_venue = a3.selectbox("Venue", all_venues, key="ana_venue")

    first_innings = deliveries[deliveries["inning"] == 1]
    inn_totals = (
        first_innings.groupby(["match_id", "batting_team"], dropna=False)["total_runs"]
        .sum()
        .reset_index(name="innings_total")
    )
    inn_totals = inn_totals.merge(matches[["match_id", "venue"]], on="match_id", how="left")
    venue_avg = inn_totals[inn_totals["venue"] == ana_venue]["innings_total"].mean()
    team_avg = inn_totals[inn_totals["batting_team"] == ana_team]["innings_total"].mean()
    expected_score = round(((venue_avg if pd.notna(venue_avg) else 160) + (team_avg if pd.notna(team_avg) else 160)) / 2, 1)

    venue_matches = matches[(matches["venue"] == ana_venue) & ((matches["team1"] == ana_team) | (matches["team2"] == ana_team))]
    venue_win_pct = 0.0
    if len(venue_matches) > 0:
        venue_win_pct = round((venue_matches["winner"] == ana_team).mean() * 100, 1)

    h2h = matches[
        ((matches["team1"] == ana_team) & (matches["team2"] == ana_opp))
        | ((matches["team1"] == ana_opp) & (matches["team2"] == ana_team))
    ]
    h2h_team_wins = int((h2h["winner"] == ana_team).sum())
    h2h_opp_wins = int((h2h["winner"] == ana_opp).sum())

    toss_team = matches[(matches["toss_winner"] == ana_team)]
    toss_impact = round((toss_team["winner"] == ana_team).mean() * 100, 1) if len(toss_team) else 0.0

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Expected 1st Innings Score", f"{expected_score}")
    b2.metric(f"{ana_team} Venue Win %", f"{venue_win_pct}%")
    b3.metric("H2H Record", f"{h2h_team_wins}-{h2h_opp_wins}")
    b4.metric("Win % After Toss Won", f"{toss_impact}%")

    team_bat = deliveries[deliveries["batting_team"] == ana_team]
    opp_bowl = deliveries[deliveries["bowling_team"] == ana_opp]
    team_rr = round(team_bat["total_runs"].sum() / max(len(team_bat) / 6, 1), 2)
    opp_econ = round(opp_bowl["total_runs"].sum() / max(len(opp_bowl) / 6, 1), 2)

    team_matches = matches[(matches["team1"] == ana_team) | (matches["team2"] == ana_team)]
    opp_matches = matches[(matches["team1"] == ana_opp) | (matches["team2"] == ana_opp)]
    team_wr = (team_matches["winner"] == ana_team).mean() if len(team_matches) else 0.5
    opp_wr = (opp_matches["winner"] == ana_opp).mean() if len(opp_matches) else 0.5
    strength_gap = team_wr - opp_wr
    upset_prob = round((0.5 - strength_gap) * 100, 1)
    upset_prob = min(max(upset_prob, 0), 100)

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{ana_team} Run Rate", f"{team_rr}")
    c2.metric(f"{ana_opp} Economy", f"{opp_econ}")
    c3.metric("Upset Probability (Proxy)", f"{upset_prob}%")

    team_phase = team_bat.copy()
    team_phase["phase"] = team_phase["over_num"].apply(
        lambda o: "Powerplay" if o <= 6 else "Middle" if o <= 15 else "Death"
    )
    phase_rr = (
        team_phase.groupby("phase", dropna=False)
        .agg(runs=("total_runs", "sum"), balls=("total_runs", "count"))
        .reset_index()
    )
    phase_rr["run_rate"] = phase_rr["runs"] / (phase_rr["balls"] / 6).replace(0, 1)

    bowl_pressure = deliveries[deliveries["bowling_team"] == ana_team].copy()
    bowl_pressure["dot"] = ((bowl_pressure["batsman_runs"] == 0) & (bowl_pressure["extra_runs"] == 0)).astype(int)
    dot_rate = round(bowl_pressure["dot"].mean() * 100, 1) if len(bowl_pressure) else 0.0

    current_points = int((team_matches["winner"] == ana_team).sum()) * 2
    current_played = len(team_matches)
    projected_total_games = max(current_played, 14)
    remaining_games = max(projected_total_games - current_played, 0)
    projected_wins = round((team_wr if pd.notna(team_wr) else 0.5) * remaining_games, 1)
    points_needed_to_qualify = 16
    qual_prob = round(min((current_points + projected_wins * 2) / points_needed_to_qualify, 1.0) * 100, 1)

    d1, d2 = st.columns(2)
    d1.metric("Dot Ball Pressure Rate", f"{dot_rate}%")
    d2.metric("Qualification Probability (Approx)", f"{qual_prob}%")

    vis1, vis2 = st.columns(2)
    with vis1:
        fig_phase = px.bar(
            phase_rr,
            x="phase",
            y="run_rate",
            color="phase",
            color_discrete_map={"Powerplay": "#00CC96", "Middle": "#636EFA", "Death": "#EF553B"},
            title=f"{ana_team} Phase-wise Run Rate",
            text="run_rate",
        )
        fig_phase.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_phase.update_layout(height=360)
        st.plotly_chart(fig_phase, use_container_width=True)

    with vis2:
        h2h_df = pd.DataFrame(
            {
                "Team": [ana_team, ana_opp],
                "Wins": [h2h_team_wins, h2h_opp_wins],
            }
        )
        fig_h2h = px.bar(
            h2h_df,
            x="Team",
            y="Wins",
            color="Team",
            title=f"H2H Dominance: {ana_team} vs {ana_opp}",
            text="Wins",
        )
        fig_h2h.update_traces(textposition="outside")
        fig_h2h.update_layout(height=360)
        st.plotly_chart(fig_h2h, use_container_width=True)
except Exception as exc:
    st.warning(f"Additional analyst insights error: {exc}")
