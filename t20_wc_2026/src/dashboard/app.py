"""
T20 WC 2026 Analytics Platform - Main Streamlit App
Multi-page dashboard with sidebar navigation.
"""

import streamlit as st

st.set_page_config(
    page_title="T20 WC 2026 Analytics",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/en/thumb/2/2a/ICC_T20_World_Cup_2024_logo.svg/200px-ICC_T20_World_Cup_2024_logo.svg.png",
    width=180,
)
st.sidebar.title("🏏 T20 WC 2026")
st.sidebar.markdown("---")

PAGES = {
    "📊 Data Quality & EDA": "pages/1_data_quality.py",
    "🧑‍💼 Coach Dashboard": "pages/2_coach.py",
    "📈 Team Analyst": "pages/3_analyst.py",
    "🎙️ Commentator / Media": "pages/4_commentator.py",
    "🏆 Tournament Strategist": "pages/5_strategist.py",
    "🤖 ML Predictions": "pages/6_ml.py",
    "💬 AI Chatbot": "pages/7_chatbot.py",
}

st.sidebar.markdown("### Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
st.sidebar.markdown("---")
st.sidebar.caption("Kenexai Hackathon 2k26 | KD&A-10")

# Optional page switch for already-built pages.
if selection == "📊 Data Quality & EDA":
    st.switch_page(PAGES[selection])

# Home page content when no sub-page selected
st.title("🏏 ICC T20 World Cup 2026 - Prediction Platform")
st.markdown(
    """
> **AI-powered cricket analytics platform** built for Kenexai Hackathon 2k26 @ CHARUSAT

Use the sidebar to navigate between dashboards.
"""
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Matches", "110")
col2.metric("Players Tracked", "299")
col3.metric("Deliveries", "45,656")
col4.metric("Teams", "20")
