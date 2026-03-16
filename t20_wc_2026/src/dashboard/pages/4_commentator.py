"""
PAGE 4: Commentator / Media Dashboard
Persona: TV Commentator / Sports Journalist
KPIs: Records, milestones, H2H stats, top performers
"""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query, gw, aw, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Commentator", page_icon="🎙️", layout="wide")
st.title("🎙️ Commentator & Media Dashboard")
st.caption("Persona: Commentator / Media | Focus: Records, Stories, Live Stats")

engine = get_engine()
render_sidebar_filters()
_gw = gw()
_aw = aw()
deliveries = query(
    engine,
    f"""SELECT match_id, inning, over_num, ball_num, batting_team, bowling_team,
        batsman, bowler, batsman_runs, total_runs, is_wicket
    FROM silver.clean_deliveries WHERE TRUE {_gw}""",
)
matches = query(engine, f"SELECT * FROM silver.clean_matches WHERE TRUE {_gw}")

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

st.divider()
st.markdown("### 🧠 Additional Cricsheet-Driven Commentator Insights")
st.caption(
    "Live trendline, milestone alerts, venue specialists, fastest scorers, momentum, current RR vs venue average, matchup specialist bowlers, and dynamic fun facts."
)

try:
    live_all = query(engine, "SELECT * FROM public.live_ball_events ORDER BY event_id ASC")

    if not live_all.empty:
        live_match = str(live_all["match_id"].iloc[-1])
        live_match_df = live_all[live_all["match_id"].astype(str) == live_match].copy()
        live_match_df["over_ball"] = live_match_df["over_num"].astype(float) + (live_match_df["ball_num"].astype(float) / 10)
        live_match_df["cum_runs"] = (live_match_df["runs_scored"] + live_match_df.get("extras", 0)).cumsum()
        balls_bowled = len(live_match_df)
        overs_bowled = max(balls_bowled / 6, 0.1)
        current_rr = live_match_df["cum_runs"].iloc[-1] / overs_bowled
        projected_total = round(current_rr * 20, 1)

        hist_first = deliveries[deliveries["inning"] == 1].groupby("match_id")["total_runs"].sum()
        venue_avg_rr = round((hist_first.mean() / 20), 2) if len(hist_first) else 8.0

        win_prob = round(min(max((projected_total / max(venue_avg_rr * 20, 1)) * 50 + 25, 5), 95), 1)

        m1, m2, m3 = st.columns(3)
        m1.metric("Live Match", live_match)
        m2.metric("Current RR vs Venue Avg RR", f"{current_rr:.2f} vs {venue_avg_rr:.2f}")
        m3.metric("Live Win Probability (Proxy)", f"{win_prob}%")

        fig_live = go.Figure()
        fig_live.add_trace(
            go.Scatter(
                x=live_match_df["over_ball"],
                y=live_match_df["cum_runs"],
                mode="lines+markers",
                name="Live Score",
                line={"color": "#EF553B", "width": 3},
            )
        )
        fig_live.update_layout(
            title="Live Win-Context Graph (Runs Progression)",
            xaxis_title="Over.Ball",
            yaxis_title="Cumulative Runs",
            height=360,
        )
        st.plotly_chart(fig_live, use_container_width=True)

        # Milestone alerts from live feed
        batter_live = (
            live_match_df.groupby("batsman", dropna=False)["runs_scored"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        alerts = []
        for _, row in batter_live.iterrows():
            if row["runs_scored"] >= 100:
                alerts.append(f"{row['batsman']} has crossed 100")
            elif row["runs_scored"] >= 50:
                alerts.append(f"{row['batsman']} has crossed 50")
        if alerts:
            st.info("Milestone Alerts: " + " | ".join(alerts[:4]))

    v1, v2 = st.columns(2)

    with v1:
        venue_options = sorted(matches["venue"].dropna().astype(str).unique().tolist())
        selected_venue = st.selectbox("Venue Specialist Lookup", venue_options, key="comm_venue")
        venue_match_ids = matches[matches["venue"] == selected_venue]["match_id"].astype(str).tolist()
        venue_del = deliveries[deliveries["match_id"].astype(str).isin(venue_match_ids)]

        venue_bat = venue_del.groupby("batsman", dropna=False)["batsman_runs"].sum().sort_values(ascending=False).head(5)
        venue_bowl = venue_del.groupby("bowler", dropna=False)["is_wicket"].sum().sort_values(ascending=False).head(5)

        st.markdown("#### Best Performers at Venue")
        st.write("Top Batters:")
        st.dataframe(venue_bat.reset_index(name="runs"), use_container_width=True, hide_index=True)
        st.write("Top Bowlers:")
        st.dataframe(venue_bowl.reset_index(name="wickets"), use_container_width=True, hide_index=True)

    with v2:
        # Fastest scorers (minimum balls threshold)
        bat_agg = (
            deliveries.groupby("batsman", dropna=False)
            .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"), sixes=("batsman_runs", lambda x: int((x == 6).sum())))
            .reset_index()
        )
        bat_agg = bat_agg[bat_agg["balls"] >= 60]
        bat_agg["strike_rate"] = (bat_agg["runs"] / bat_agg["balls"]) * 100
        fastest = bat_agg.sort_values("strike_rate", ascending=False).head(10)

        fig_fast = px.bar(
            fastest,
            x="batsman",
            y="strike_rate",
            color="sixes",
            title="Fastest Scorers (Min 60 Balls)",
            text="strike_rate",
        )
        fig_fast.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_fast.update_layout(height=360, xaxis_tickangle=-30)
        st.plotly_chart(fig_fast, use_container_width=True)

    # Team momentum in last 3 overs (historical average)
    momentum = deliveries[deliveries["over_num"] >= 18].groupby("batting_team", dropna=False)["total_runs"].mean().sort_values(ascending=False).head(8)
    st.markdown("#### Team Momentum (Last 3 Overs Average)")
    st.dataframe(momentum.reset_index(name="avg_runs_per_ball_last3overs").round(2), use_container_width=True, hide_index=True)

    # Best bowler vs opponent
    t1, t2 = st.columns(2)
    teams = sorted(pd.concat([matches["team1"], matches["team2"]]).dropna().astype(str).unique().tolist())
    bowling_team = t1.selectbox("Bowling Team", teams, key="comm_bowl_team")
    batting_team = t2.selectbox("Opponent Batting Team", [t for t in teams if t != bowling_team], key="comm_bat_team")
    matchup_bowl = deliveries[(deliveries["bowling_team"] == bowling_team) & (deliveries["batting_team"] == batting_team)]
    bowl_vs = matchup_bowl.groupby("bowler", dropna=False)["is_wicket"].sum().sort_values(ascending=False).head(10).reset_index(name="wickets")
    st.markdown("#### Best Bowlers vs Selected Opponent")
    st.dataframe(bowl_vs, use_container_width=True, hide_index=True)

    # Fun fact generator from computed stats
    if st.button("Generate Fun Fact"):
        top_run_player = deliveries.groupby("batsman", dropna=False)["batsman_runs"].sum().idxmax()
        top_six_player = deliveries[deliveries["batsman_runs"] == 6].groupby("batsman", dropna=False).size().idxmax()
        top_wicket_player = deliveries.groupby("bowler", dropna=False)["is_wicket"].sum().idxmax()
        st.success(
            f"Fun Fact: {top_run_player} leads aggregate runs, {top_six_player} leads sixes, and {top_wicket_player} leads wickets in this CricSheet-driven dataset."
        )
except Exception as exc:
    st.warning(f"Additional commentator insights error: {exc}")

st.divider()
st.markdown("### 🤝 Partnership Strength (Cricsheet Ball-by-Ball Exclusive)")
try:
    part_teams = sorted(
        pd.concat([matches["team1"], matches["team2"]]).dropna().astype(str).unique().tolist()
    )
    part_team = st.selectbox(
        "Select batting team for partnership analysis", part_teams, key="comm_partnership_team"
    )
    _pt_sql = part_team.replace("'", "''")
    part_df = query(
        engine,
        f"""
        SELECT striker, non_striker,
               SUM(CAST(NULLIF(TRIM(runs_off_bat), '') AS INTEGER)) AS runs,
               COUNT(*) AS balls
        FROM bronze.raw_deliveries
        WHERE batting_team = '{_pt_sql}'
          AND striker IS NOT NULL AND TRIM(striker) != ''
          AND non_striker IS NOT NULL AND TRIM(non_striker) != ''
        GROUP BY striker, non_striker
        HAVING COUNT(*) >= 12
        ORDER BY runs DESC
        LIMIT 15
        """,
    )
    if not part_df.empty:
        part_df["runs"] = pd.to_numeric(part_df["runs"], errors="coerce").fillna(0).astype(int)
        part_df["balls"] = pd.to_numeric(part_df["balls"], errors="coerce").fillna(0).astype(int)
        part_df["partnership_sr"] = (
            part_df["runs"] / part_df["balls"].replace(0, 1) * 100
        ).round(1)
        part_df["pair"] = part_df["striker"] + " & " + part_df["non_striker"]
        fig_part = px.bar(
            part_df.head(10),
            x="pair",
            y="runs",
            color="partnership_sr",
            text="runs",
            title=f"Top Batting Partnerships — {part_team}",
            labels={"pair": "Partnership", "runs": "Runs Together", "partnership_sr": "SR"},
            color_continuous_scale="Viridis",
        )
        fig_part.update_traces(texttemplate="%{text}", textposition="outside")
        fig_part.update_layout(height=400, xaxis_tickangle=-30)
        st.plotly_chart(fig_part, use_container_width=True)
        st.dataframe(
            part_df[["pair", "runs", "balls", "partnership_sr"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No partnership data found for this team (need at least 12 balls together).")
except Exception as exc:
    st.warning(f"Partnership strength error: {exc}")
