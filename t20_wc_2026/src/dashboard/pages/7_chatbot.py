"""
PAGE 7: AI Chatbot & Match Preview
- CricAI RAG chatbot (Gemini + ChromaDB)
- Match preview generator
- Document insights cards
"""

import os
import sys

import pandas as pd
import streamlit as st

_PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_PAGE_DIR, "..", ".."))
if _SRC_DIR not in sys.path:
    # Put workspace src first so `genai` resolves to local package, not site-packages.
    sys.path.insert(0, _SRC_DIR)
from db import get_engine, query, gw, aw, render_sidebar_filters

st.set_page_config(page_title="AI Chatbot", page_icon="💬", layout="wide")
st.title("💬 CricAI — Powered by Gemini")
st.caption("RAG Chatbot | Match Preview Generator | Gemini 1.5 Flash + ChromaDB")

try:
    from genai.rag_engine import ask_cricai, generate_match_preview

    RAG_AVAILABLE = True
except Exception as exc:
    RAG_AVAILABLE = False
    st.error(f"RAG engine not available: {exc}")

engine = get_engine()
render_sidebar_filters()
_gw = gw()
_aw = aw()


def load_venue_options() -> list[str]:
    """Load venue options while handling column-name drift in clean_venues."""
    cols_df = query(
        engine,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'silver' AND table_name = 'clean_venues'
        """,
    )
    cols = set(cols_df["column_name"].astype(str).tolist())

    venue_col = "venue_name" if "venue_name" in cols else "stadium_name" if "stadium_name" in cols else None
    city_expr = "city" if "city" in cols else "NULL::text"

    if venue_col is None:
        return ["Neutral Venue"]

    venues_df = query(
        engine,
        f"""
        SELECT {venue_col} AS venue_name, {city_expr} AS city
        FROM silver.clean_venues
        ORDER BY 1
        """,
    )
    venues_df["venue_name"] = venues_df["venue_name"].fillna("Unknown Venue")
    venues_df["city"] = venues_df["city"].fillna("Unknown")
    options = [f"{r['venue_name']}, {r['city']}" for _, r in venues_df.iterrows()]
    return options + ["Neutral Venue"]

tabs = st.tabs(["🤖 CricAI Chatbot", "📋 Match Preview Generator", "💡 Quick Insights"])

with tabs[0]:
    st.markdown("### 🤖 Ask CricAI Anything About T20 Cricket")

    st.markdown("**💡 Try asking:**")
    sample_cols = st.columns(3)
    samples = [
        "Who are the top wicket takers?",
        "What is India's win rate?",
        "Which team scores most in powerplay?",
        "Who is the best death over bowler?",
        "Compare India and Australia stats",
        "Which venue has highest average score?",
    ]
    for i, s in enumerate(samples):
        if sample_cols[i % 3].button(s, key=f"sample_{i}"):
            st.session_state["chat_input"] = s

    st.divider()

    gender_disp = st.session_state.get("gender", "male").title()
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    f"Hi! I'm CricAI, your **{gender_disp} T20 World Cup 2026** analyst. "
                    "I have access to match results, player stats, "
                    "team records, and venue data from this tournament. "
                    "Ask me anything about the cricket."
                ),
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask CricAI anything about T20 WC 2026...", key="chat_main")

    if "chat_input" in st.session_state and st.session_state.chat_input:
        user_input = st.session_state.chat_input
        st.session_state.chat_input = ""

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("CricAI is analyzing..."):
                if RAG_AVAILABLE:
                    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                    response = ask_cricai(user_input, history)
                else:
                    response = "RAG engine not available. Please check GEMINI_API_KEY in .env"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    if st.button("Clear Chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat cleared. Ask me anything about T20 WC 2026.",
            }
        ]
        st.rerun()

with tabs[1]:
    st.markdown("### 📋 AI Match Preview Generator")
    st.caption("Generate professional pre-match analysis using Gemini AI")

    matches = query(engine, f"SELECT * FROM silver.clean_matches WHERE TRUE {_gw}")
    teams = sorted(pd.concat([matches["team1"], matches["team2"]]).unique().tolist())
    venue_list = load_venue_options()

    c1, c2, c3 = st.columns(3)
    team_a = c1.selectbox("Team A", teams, key="prev_a")
    team_b = c2.selectbox("Team B", [t for t in teams if t != team_a], key="prev_b")
    venue_sel = c3.selectbox("Venue", venue_list, key="prev_v")

    if st.button("Generate Match Preview", type="primary"):
        if RAG_AVAILABLE:
            with st.spinner(f"Generating preview for {team_a} vs {team_b}..."):
                preview = generate_match_preview(team_a, team_b, venue_sel)

            st.markdown("---")
            st.markdown(f"## {team_a} vs {team_b}")
            st.markdown(f"*{venue_sel}*")
            st.markdown("---")
            st.markdown(preview)

            st.download_button(
                label="Download Preview",
                data=f"{team_a} vs {team_b} @ {venue_sel}\n\n{preview}",
                file_name=f"preview_{team_a}_vs_{team_b}.txt",
                mime="text/plain",
            )
        else:
            st.error("RAG engine unavailable. Check GEMINI_API_KEY.")

with tabs[2]:
    st.markdown("### 💡 AI-Generated Tournament Insights")
    st.caption("Click any card to get Gemini's analysis")

    insight_prompts = {
        "🏆 Tournament Summary": "Summarize the key highlights and patterns from this T20 World Cup tournament data in 3 bullet points.",
        "⚡ Best Powerplay Teams": "Which teams have the best powerplay performance? Give specific stats.",
        "💀 Best Death Over Teams": "Analyze which teams perform best in death overs (16-20) based on the data.",
        "🎯 Bowling Heroes": "Who are the most impactful bowlers in this tournament based on wickets and economy?",
        "🏏 Batting Champions": "Who are the most dominant batters in this tournament? Focus on runs and strike rate.",
        "🔮 Final Prediction": "Based on all the tournament data, which team looks most likely to win the T20 World Cup 2026 and why?",
    }

    cols = st.columns(2)
    for i, (title, prompt) in enumerate(insight_prompts.items()):
        with cols[i % 2]:
            with st.expander(title, expanded=False):
                if st.button("Generate Insight", key=f"insight_{i}"):
                    if RAG_AVAILABLE:
                        with st.spinner("Gemini is thinking..."):
                            insight = ask_cricai(prompt)
                        st.markdown(insight)
                    else:
                        st.error("Check GEMINI_API_KEY")
