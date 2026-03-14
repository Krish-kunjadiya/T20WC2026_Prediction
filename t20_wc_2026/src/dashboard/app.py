import streamlit as st

st.set_page_config(
    page_title="T20 WC 2026 Analytics",
    page_icon="🏏", layout="wide"
)

st.title("🏏 ICC T20 WC 2026 - Prediction Platform")
st.markdown("### Kenexai Hackathon 2k26 | KD&A-10 | CHARUSAT")
st.markdown("Use the **sidebar pages** to navigate dashboards.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Matches", "110")
c2.metric("Players", "299")
c3.metric("Deliveries", "45,656")
c4.metric("Teams", "20")

st.info("👈 Select a page from the sidebar to begin")
