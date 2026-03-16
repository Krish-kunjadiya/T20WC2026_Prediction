"""
PAGE 2: Coach Dashboard
Persona: Team Coach
KPIs: Player form, strike rate trends, death over economy,
      bowling attack analysis, player availability
"""

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from db import get_engine, query, gw, aw, render_sidebar_filters  # noqa: E402


st.set_page_config(page_title="Coach Dashboard", page_icon="🧑‍💼", layout="wide")
st.title("🧑‍💼 Coach Dashboard")
st.caption("Persona: Team Coach | Focus: Player Form & Match Readiness")

engine = get_engine()
render_sidebar_filters()
_gw = gw()
_aw = aw()

# -- FILTERS ------------------------------------------------------
_teams_df = query(
    engine,
    f"""
    SELECT DISTINCT team1 AS team_name FROM silver.clean_matches WHERE TRUE {_gw}
    UNION
    SELECT DISTINCT team2 AS team_name FROM silver.clean_matches WHERE TRUE {_gw}
    ORDER BY team_name
    """,
)
selected_team = st.selectbox("🌍 Select Team", _teams_df["team_name"].tolist())

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
        WHERE (batting_team = '{selected_team}'
           OR bowling_team = '{selected_team}') {_gw}
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
        WHERE country = '{selected_team}' {_gw} {_aw}
        ORDER BY runs DESC
        LIMIT 11
    """,
    )
    if players.empty:
        players = query(engine, f"SELECT * FROM silver.clean_players WHERE TRUE {_gw} {_aw} ORDER BY runs DESC LIMIT 11")

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

st.divider()
st.markdown("### 🧠 Cricsheet-Only Advanced Insights")
st.caption(
    "Mapped to CricSheet ball-by-ball + match metadata: recent form, matchup, consistency, batting depth, phase effectiveness, weakness trends, and XI recommendation."
)

try:
    selected_team_sql = selected_team.replace("'", "''")
    coach_deliveries = query(
        engine,
        f"""
        SELECT match_id, inning, over_num, ball_num, batting_team, bowling_team,
               batsman, bowler, batsman_runs, extra_runs, total_runs,
               is_wicket, dismissal_kind, player_dismissed
        FROM silver.clean_deliveries
        WHERE (batting_team = '{selected_team_sql}'
           OR bowling_team = '{selected_team_sql}') {_gw}
        """,
    )
    coach_matches = query(
        engine,
        f"""
        SELECT match_id, match_date, team1, team2, winner, venue, toss_winner, toss_decision
        FROM silver.clean_matches
        WHERE (team1 = '{selected_team_sql}' OR team2 = '{selected_team_sql}') {_gw}
        """,
    )

    if coach_deliveries.empty or coach_matches.empty:
        st.info("No team-specific records found in CricSheet-derived tables yet.")
    else:
        coach_matches["match_date"] = pd.to_datetime(coach_matches["match_date"], errors="coerce")
        recent_match_ids = (
            coach_matches.sort_values(["match_date", "match_id"], ascending=False)["match_id"]
            .dropna()
            .astype(str)
            .head(5)
            .tolist()
        )

        recent_del = coach_deliveries[coach_deliveries["match_id"].astype(str).isin(recent_match_ids)].copy()
        recent_bat = recent_del[recent_del["batting_team"] == selected_team]
        recent_bowl = recent_del[recent_del["bowling_team"] == selected_team]

        recent_runs = (
            recent_bat.groupby(["batsman", "match_id"], dropna=False)["batsman_runs"]
            .sum()
            .groupby("batsman")
            .sum()
            .rename("recent_runs")
        )
        recent_wkts = (
            recent_bowl.groupby("bowler", dropna=False)["is_wicket"]
            .sum()
            .rename("recent_wickets")
        )

        form_df = pd.concat([recent_runs, recent_wkts], axis=1).fillna(0).reset_index()
        form_df = form_df.rename(columns={"index": "player", "batsman": "player", "bowler": "player"})
        form_df["form_score"] = form_df["recent_runs"] + (form_df["recent_wickets"] * 20)
        form_df = form_df.sort_values("form_score", ascending=False)

        # 1) Top 5 by recent form
        st.markdown("#### 1) Top 5 Players by Recent Form (Last 5 Matches)")
        st.dataframe(
            form_df[["player", "recent_runs", "recent_wickets", "form_score"]].head(5),
            use_container_width=True,
            hide_index=True,
        )

        s1, s2, s3 = st.columns(3)

        # 2) Best powerplay batter
        pp = recent_bat[recent_bat["over_num"] <= 6].groupby("batsman", dropna=False)["batsman_runs"].sum()
        if not pp.empty:
            s1.metric("2) Best Powerplay Batter", str(pp.idxmax()), f"{int(pp.max())} runs")

        # 3) Best middle-order batter (overs 7-15)
        mid = recent_bat[(recent_bat["over_num"] >= 7) & (recent_bat["over_num"] <= 15)]
        mid_avg = (
            mid.groupby(["batsman", "match_id"], dropna=False)["batsman_runs"]
            .sum()
            .groupby("batsman")
            .mean()
        )
        if not mid_avg.empty:
            s2.metric("3) Best Middle-Order Batter", str(mid_avg.idxmax()), f"Avg {mid_avg.max():.1f}")

        # 4) Best death bowler
        death = recent_bowl[recent_bowl["over_num"] >= 16]
        death_stats = (
            death.groupby("bowler", dropna=False)
            .agg(balls=("total_runs", "count"), runs=("total_runs", "sum"))
            .reset_index()
        )
        death_stats = death_stats[death_stats["balls"] >= 12]
        if not death_stats.empty:
            death_stats["economy"] = death_stats["runs"] / (death_stats["balls"] / 6)
            best_death = death_stats.sort_values("economy").iloc[0]
            s3.metric("4) Best Death Bowler", str(best_death["bowler"]), f"Eco {best_death['economy']:.2f}")

        # 5) Batter vs bowler matchup
        st.markdown("#### 5) Batter vs Bowler Matchup")
        matchup_cols = st.columns(3)
        batter_opts = sorted(recent_bat["batsman"].dropna().astype(str).unique().tolist())
        bowler_opts = sorted(recent_del[recent_del["bowling_team"] != selected_team]["bowler"].dropna().astype(str).unique().tolist())
        if batter_opts and bowler_opts:
            chosen_batter = matchup_cols[0].selectbox("Batter", batter_opts, key="coach_matchup_batter")
            chosen_bowler = matchup_cols[1].selectbox("Bowler", bowler_opts, key="coach_matchup_bowler")
            duel = recent_del[(recent_del["batsman"] == chosen_batter) & (recent_del["bowler"] == chosen_bowler)]
            duel_runs = int(duel["batsman_runs"].sum())
            duel_balls = int(len(duel))
            duel_outs = int(((duel["is_wicket"] == True) & (duel["player_dismissed"] == chosen_batter)).sum())
            duel_sr = (duel_runs / max(duel_balls, 1)) * 100
            matchup_cols[2].metric("Duel SR", f"{duel_sr:.1f}")
            st.write(f"Runs: {duel_runs} | Balls: {duel_balls} | Dismissals: {duel_outs}")

        # 6) Most consistent performer (lowest run std dev with match threshold)
        st.markdown("#### 6) Most Consistent Batter")
        consistency = (
            recent_bat.groupby(["batsman", "match_id"], dropna=False)["batsman_runs"]
            .sum()
            .reset_index()
            .groupby("batsman", dropna=False)
            .agg(matches=("match_id", "nunique"), avg_runs=("batsman_runs", "mean"), std_runs=("batsman_runs", "std"))
            .reset_index()
        )
        consistency = consistency[consistency["matches"] >= 3].fillna({"std_runs": 0.0})
        if not consistency.empty:
            consistent = consistency.sort_values(["std_runs", "avg_runs"], ascending=[True, False]).iloc[0]
            st.success(
                f"{consistent['batsman']} | Avg {consistent['avg_runs']:.1f} | Std Dev {consistent['std_runs']:.2f} (lower is better)"
            )

        # 7) Batting depth (positions 6-8) derived from first appearance order in innings
        st.markdown("#### 7) Batting Depth (Positions 6-8, Derived)")
        bat_order_src = coach_deliveries[coach_deliveries["batting_team"] == selected_team].copy()
        bat_order_src = bat_order_src.sort_values(["match_id", "inning", "over_num", "ball_num"])
        first_seen = (
            bat_order_src.groupby(["match_id", "inning", "batsman"], as_index=False)
            .agg(first_over=("over_num", "min"), first_ball=("ball_num", "min"))
            .sort_values(["match_id", "inning", "first_over", "first_ball"])
        )
        first_seen["batting_position"] = first_seen.groupby(["match_id", "inning"]).cumcount() + 1
        lower_mid = first_seen[first_seen["batting_position"].between(6, 8)]
        depth_stats = (
            lower_mid.groupby("batsman", dropna=False)
            .size()
            .sort_values(ascending=False)
            .head(8)
            .reset_index(name="innings_at_6_8")
        )
        if not depth_stats.empty:
            st.dataframe(depth_stats, use_container_width=True, hide_index=True)

        # 8) Bowling phase effectiveness
        st.markdown("#### 8) Bowling Phase Effectiveness")
        phase_df = recent_bowl.copy()
        phase_df["phase"] = phase_df["over_num"].apply(
            lambda o: "Powerplay" if o <= 6 else "Middle" if o <= 15 else "Death"
        )
        phase_eff = (
            phase_df.groupby("phase", dropna=False)
            .agg(
                balls=("total_runs", "count"),
                wickets=("is_wicket", "sum"),
                runs=("total_runs", "sum"),
            )
            .reset_index()
        )
        phase_eff["wickets_per_over"] = phase_eff["wickets"] / (phase_eff["balls"] / 6).replace(0, 1)
        phase_eff["economy"] = phase_eff["runs"] / (phase_eff["balls"] / 6).replace(0, 1)
        st.dataframe(
            phase_eff[["phase", "balls", "wickets", "wickets_per_over", "economy"]].round(2),
            use_container_width=True,
            hide_index=True,
        )

        # 9) Player weakness via dismissal kind
        st.markdown("#### 9) Player Weakness (Dismissal Pattern)")
        out_events = recent_del[(recent_del["player_dismissed"].notna()) & (recent_del["player_dismissed"].astype(str) != "")]
        dismiss_batter_opts = sorted(out_events["player_dismissed"].astype(str).unique().tolist())
        if dismiss_batter_opts:
            weakness_batter = st.selectbox("Select batter for weakness profile", dismiss_batter_opts, key="coach_weakness_batter")
            weak_df = (
                out_events[out_events["player_dismissed"] == weakness_batter]
                .groupby("dismissal_kind", dropna=False)
                .size()
                .sort_values(ascending=False)
                .reset_index(name="dismissals")
            )
            st.dataframe(weak_df, use_container_width=True, hide_index=True)

        # 10) Optimal XI recommendation using cluster labels + form score
        st.markdown("#### 10) Suggested Optimal XI (Form + Cluster Tags)")
        cluster_path = Path(__file__).resolve().parents[2] / "results" / "player_clusters.csv"
        if cluster_path.exists():
            clusters = pd.read_csv(cluster_path)
            clusters["player_name"] = clusters["player_name"].astype(str).str.strip()
            form_export = form_df.rename(columns={"player": "player_name"}).copy()
            form_export["player_name"] = form_export["player_name"].astype(str).str.strip()
            pool = query(
                engine,
                f"""
                SELECT DISTINCT player_name
                FROM silver.clean_players
                WHERE country = '{selected_team_sql}' {_gw} {_aw}
                """,
            )
            pool["player_name"] = pool["player_name"].astype(str).str.strip()

            xi = (
                pool.merge(clusters[["player_name", "player_type", "strike_rate_live", "wickets"]], on="player_name", how="left")
                .merge(form_export[["player_name", "form_score", "recent_runs", "recent_wickets"]], on="player_name", how="left")
                .fillna({"form_score": 0, "recent_runs": 0, "recent_wickets": 0, "strike_rate_live": 0, "wickets": 0})
            )
            xi["selection_score"] = (
                xi["form_score"] +
                (xi["strike_rate_live"] * 0.2) +
                (xi["wickets"] * 3)
            )
            xi = xi.sort_values("selection_score", ascending=False).head(11)
            st.dataframe(
                xi[["player_name", "player_type", "recent_runs", "recent_wickets", "selection_score"]].round(2),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("player_clusters.csv not found in results folder; skipping optimal XI tag enrichment.")
except Exception as exc:
    st.warning(f"Advanced coach insights error: {exc}")

st.divider()
st.markdown("### 🔬 Cricsheet-Exclusive Deep Insights")

# 11) Pressure Ball Performance
st.markdown("#### 11) Pressure Ball Performance (After a Wicket Falls)")
try:
    _team_sql = selected_team.replace("'", "''")
    press_del = query(
        engine,
        f"""
        SELECT match_id, inning, over_num, ball_num, batsman, batsman_runs, is_wicket
        FROM silver.clean_deliveries
        WHERE batting_team = '{_team_sql}' {_gw}
        ORDER BY match_id, inning, over_num, ball_num
        """,
    )
    if not press_del.empty:
        press_del["is_wicket"] = press_del["is_wicket"].astype(bool)
        press_del["batsman_runs"] = pd.to_numeric(press_del["batsman_runs"], errors="coerce").fillna(0)

        def _tag_pressure(grp: pd.DataFrame) -> pd.DataFrame:
            grp = grp.copy().reset_index(drop=True)
            grp["recent_wkts"] = (
                grp["is_wicket"].shift(1).fillna(False).astype(int).rolling(6, min_periods=1).sum()
            )
            grp["is_pressure"] = grp["recent_wkts"] > 0
            return grp

        tagged = press_del.groupby(["match_id", "inning"], group_keys=False).apply(_tag_pressure)
        pressure_balls = tagged[tagged["is_pressure"]]
        if not pressure_balls.empty:
            pagg = (
                pressure_balls.groupby("batsman")
                .agg(pressure_runs=("batsman_runs", "sum"), pressure_balls=("batsman_runs", "count"))
                .reset_index()
            )
            pagg["pressure_sr"] = (
                pagg["pressure_runs"] / pagg["pressure_balls"].replace(0, 1) * 100
            ).round(1)
            pagg = pagg[pagg["pressure_balls"] >= 10].sort_values("pressure_sr", ascending=False).head(10)
            if not pagg.empty:
                fig_p = px.bar(
                    pagg,
                    x="batsman",
                    y="pressure_sr",
                    text="pressure_runs",
                    title=f"Best Under Pressure (After Wicket) — {selected_team}",
                    labels={"pressure_sr": "Strike Rate", "batsman": "Batter"},
                )
                fig_p.update_traces(texttemplate="%{text}", textposition="outside")
                fig_p.update_layout(height=360, xaxis_tickangle=-30)
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.info("Not enough pressure-ball data (min 10 balls under pressure) for this team.")
        else:
            st.info("No post-wicket pressure windows found for this team.")
    else:
        st.info("No delivery data found for selected team.")
except Exception as exc:
    st.warning(f"Pressure ball performance error: {exc}")

# 12) Bowler Hat-trick Alert
st.markdown("#### 12) Bowler Hat-trick Alerts (3 Consecutive Wickets in a Match)")
try:
    wkt_del = query(
        engine,
        """
        SELECT match_id, inning, over_num, ball_num, bowler
        FROM silver.clean_deliveries
        WHERE is_wicket = TRUE {_gw}
        ORDER BY match_id, inning, over_num, ball_num
        """,
    )
    if not wkt_del.empty:
        hat_tricks = []
        for (mid, inn), grp in wkt_del.groupby(["match_id", "inning"]):
            grp = grp.reset_index(drop=True)
            for i in range(len(grp) - 2):
                if grp.loc[i, "bowler"] == grp.loc[i + 1, "bowler"] == grp.loc[i + 2, "bowler"]:
                    hat_tricks.append(
                        {
                            "match_id": mid,
                            "inning": inn,
                            "bowler": grp.loc[i, "bowler"],
                            "ball_1": f"{grp.loc[i, 'over_num']}.{grp.loc[i, 'ball_num']}",
                            "ball_2": f"{grp.loc[i+1, 'over_num']}.{grp.loc[i+1, 'ball_num']}",
                            "ball_3": f"{grp.loc[i+2, 'over_num']}.{grp.loc[i+2, 'ball_num']}",
                        }
                    )
        if hat_tricks:
            ht_df = pd.DataFrame(hat_tricks).drop_duplicates(subset=["match_id", "inning", "bowler"])
            st.success(f"🎯 {len(ht_df)} hat-trick instance(s) found in the CricSheet dataset!")
            st.dataframe(ht_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hat-trick instances found in the dataset.")
    else:
        st.info("No wicket delivery data available.")
except Exception as exc:
    st.warning(f"Hat-trick alert error: {exc}")
