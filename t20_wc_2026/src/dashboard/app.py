"""
T20 WC 2026 Analytics Platform — Landing page.

Global sidebar filters (gender + active-players) are rendered via
render_sidebar_filters() in db.py so they appear on every page automatically.
"""

import os
import sys

import streamlit as st

sys.path.append(os.path.dirname(__file__))
from db import get_engine, query, render_sidebar_filters  # noqa: E402


st.set_page_config(
    page_title="T20 WC 2026 Analytics",
    page_icon="🏏",
    layout="wide",
)

# ── Render sidebar (same function used on every page) ───────────────────────
render_sidebar_filters()

gender = st.session_state.get("gender", "male")
active_only = st.session_state.get("active_only", True)

# ── MAIN LANDING PAGE ───────────────────────────────────────────────────────
gender_flag = "👨" if gender == "male" else "👩"
gender_label = "Male T20 WC" if gender == "male" else "Female T20 WC"
st.title(f"🏏 ICC T20 WC 2026 — {gender_flag} {gender_label} Analytics Platform")
st.markdown("### Kenexai Hackathon 2k26 | KD&A-10 | CHARUSAT")

active_label = "Active players only (last 3 yrs)" if active_only else "All players (including legends)"
st.info(
    f"**Current filter:** {gender_label}  |  {active_label}  \n"
    "👈 Select a page from the sidebar to begin."
)

st.divider()

# ── LIVE KPI ROW (from warehouse) ───────────────────────────────────────────
st.markdown("### 📊 Warehouse Snapshot")
try:
    engine = get_engine()
    kpi = query(
        engine,
        f"""
        SELECT
            (SELECT COUNT(*) FROM silver.clean_matches
             WHERE gender = '{gender}')                          AS matches,
            (SELECT COUNT(DISTINCT player_name) FROM silver.clean_players
             WHERE gender = '{gender}')                          AS players,
            (SELECT COUNT(*) FROM silver.clean_deliveries
             WHERE gender = '{gender}')                          AS deliveries,
            (SELECT COUNT(DISTINCT team_name) FROM gold.dim_team) AS teams
        """,
    )
    row = kpi.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏟️ Matches",    f"{int(row['matches']):,}")
    c2.metric("👤 Players",    f"{int(row['players']):,}")
    c3.metric("🏏 Deliveries", f"{int(row['deliveries']):,}")
    c4.metric("🌍 Teams",      f"{int(row['teams']):,}")
except Exception:
    try:
        engine = get_engine()
        kpi = query(
            engine,
            """
            SELECT
                (SELECT COUNT(*) FROM silver.clean_matches)              AS matches,
                (SELECT COUNT(DISTINCT player_name) FROM silver.clean_players) AS players,
                (SELECT COUNT(*) FROM silver.clean_deliveries)           AS deliveries,
                (SELECT COUNT(DISTINCT team_name) FROM gold.dim_team)    AS teams
            """,
        )
        row = kpi.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏟️ Matches",    f"{int(row['matches']):,}")
        c2.metric("👤 Players",    f"{int(row['players']):,}")
        c3.metric("🏏 Deliveries", f"{int(row['deliveries']):,}")
        c4.metric("🌍 Teams",      f"{int(row['teams']):,}")
    except Exception as exc:
        st.warning(f"Could not load warehouse KPIs: {exc}")

st.divider()

# ── PLATFORM GUIDE ──────────────────────────────────────────────────────────
st.markdown("### 🗂️ Dashboard Pages")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown(
        """
        **1️⃣ Data Quality**
        Overview of warehouse completeness, null rates, and row counts.

        **2️⃣ Coach**
        Player form, matchup analysis, bowling phase effectiveness,
        pressure-ball performance, hat-trick alerts & Optimal XI.
        """
    )

with col_b:
    st.markdown(
        """
        **3️⃣ Analyst**
        Venue win %, H2H dominance, upset probability,
        phase run-rates, dot-ball pressure & qualification projections.

        **4️⃣ Commentator**
        Live match feed, partnership strength, fastest scorers,
        team momentum, venue specialists & fun-fact generator.
        """
    )

with col_c:
    st.markdown(
        """
        **5️⃣ Predictions**
        ML-driven match outcome predictions and SHAP explanations.

        **6️⃣ GenAI Assistant**
        Chat with an RAG-powered cricket analyst.
        Ask questions across the full CricSheet dataset.
        """
    )

