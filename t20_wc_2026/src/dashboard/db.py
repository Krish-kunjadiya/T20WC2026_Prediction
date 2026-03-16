"""Shared database connection and global filter helpers for all dashboard pages.

Global session-state keys (widget-keyed, set by render_sidebar_filters):
    st.session_state['gender_radio']       → 'Male T20 WC' | 'Female T20 WC'
    st.session_state['active_only_toggle'] → True | False
    st.session_state['gender']             → 'male' | 'female'  (derived)
    st.session_state['active_only']        → True | False         (derived)
"""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


@st.cache_resource
def get_engine():
    database_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@"
        f"{os.getenv('POSTGRES_HOST')}:"
        f"{os.getenv('POSTGRES_PORT')}/"
        f"{os.getenv('POSTGRES_DB')}"
    )
    return create_engine(database_url)


@st.cache_data(ttl=60)
def query(_engine, sql: str) -> pd.DataFrame:
    """Execute SQL and return DataFrame. Cached for 60s."""
    return pd.read_sql(sql, _engine)


# ── Global filter helpers ────────────────────────────────────────────────────

def render_sidebar_filters() -> None:
    """Render gender + active-only widgets in the sidebar and sync session state.

    MUST be called at the TOP of every page, BEFORE gw() and aw() are called,
    so that session state is fresh before queries are built.
    """
    st.sidebar.markdown("## 🏏 T20 WC 2026")
    st.sidebar.markdown("---")

    gender_label = st.sidebar.radio(
        "Tournament",
        ["Male T20 WC", "Female T20 WC"],
        horizontal=True,
        key="gender_radio",
    )
    # Keep derived 'gender' key in sync so other code can read it directly
    st.session_state["gender"] = "male" if gender_label == "Male T20 WC" else "female"

    st.sidebar.markdown("---")

    active_only = st.sidebar.toggle(
        "👤 Active players only",
        value=st.session_state.get("active_only", True),
        key="active_only_toggle",
        help="ON = players who played in the last 3 years. OFF = include retired legends.",
    )
    st.session_state["active_only"] = active_only

    st.sidebar.markdown("---")
    st.sidebar.caption("Kenexai Hackathon 2k26 | KD&A-10 | CHARUSAT")

    # Compact filter caption shown on the page itself
    gender_icon = "👨" if st.session_state["gender"] == "male" else "👩"
    active_label = "Active players only" if active_only else "All players (incl. legends)"
    st.caption(
        f"{gender_icon} **{st.session_state['gender'].title()} T20 WC**"
        f" &nbsp;|&nbsp; 👤 {active_label}"
    )


def get_gender() -> str:
    """Return current gender ('male' or 'female') from session state."""
    return st.session_state.get("gender", "male")


def get_active_only() -> bool:
    """Return current active-only flag from session state."""
    return st.session_state.get("active_only", True)


def gw(col: str = "gender") -> str:
    """SQL AND fragment for gender filter, e.g. \"AND gender = 'male'\"."""
    g = get_gender()
    return f"AND {col} = '{g}'"


def aw(col: str = "is_active") -> str:
    """SQL AND fragment for active-players filter, or empty string when show-all."""
    return f"AND {col} = TRUE" if get_active_only() else ""


# Keep old name as alias so nothing breaks if called during transition
filter_banner = render_sidebar_filters

