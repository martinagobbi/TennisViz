"""
overview_view.py
------------------------
Standalone Streamlit View for the Project Introduction & Index
Sinner vs Alcaraz - Roland Garros 2025
"""

import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="RG25 - Match Overview", layout="wide")

# ==========================================
# 2. HERO HEADER
# ==========================================
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🏆 Roland Garros 2025 Overview</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D; font-size:18px;'>The Five-Set Masterpiece: Jannik Sinner vs Carlos Alcaraz</p>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 3. QUICK MATCH STATS (KPI BOXES)
# ==========================================
# Adding quick visual metrics to make the overview look like a professional sports dashboard
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(label="Match Date", value="June 8, 2025")
with m2:
    st.metric(label="Champion", value="Carlos Alcaraz 🇪🇸")
with m3:
    st.metric(label="Final Score", value="4-6, 6-7, 6-4, 7-6, 7-6")
with m4:
    st.metric(label="Total Points Split", value="Exactly ~50% / 50%")

st.markdown("### 📝 Match Context")
st.write(
    """
    Welcome to the interactive tactical analysis dashboard for the historic 2025 Roland Garros Men's Singles Final. 
    On June 8, 2025, Carlos Alcaraz and Jannik Sinner contested a grueling five-set masterpiece, culminating in a razor-thin 
    victory for the Spaniard. Totaling nearly an exact 50/50 split in total points won, this match provides the ultimate 
    laboratory for studying elite tennis strategy under pressure.
    
    This visualization platform moves beyond basic post-match statistics to deconstruct the micro-dynamics of the game. 
    By parsing raw, shot-by-shot data from the Match Charting Project, this dashboard allows you to analyze specific match 
    phases, tactical shifts, and uncover the hidden patterns that dictated the final outcome.
    """
)

st.markdown("---")

# ==========================================
# 4. THE VISUALIZATIONS (3-COLUMN TEASER GRID)
# ==========================================
st.markdown("### 📊 Explore the Dashboard Visualizations")
st.write("This platform is divided into three analytical layers. Read the briefs below to choose your starting point:")

col1, col2, col3 = st.columns(3)

# --- COLUMN 1: LINE CHART TEASER ---
with col1:
    st.markdown("#### 1. Win Probability & Momentum")
    st.write(
        """
        A pure timeline analysis modeling the real-time narrative of the match. 
        By converting point-by-point score variations and historical contexts into a dynamic index, 
        this chart acts as a **Tug-of-War** tracking who held the psychological edge at any given moment.
        """
    )
    # Placeholder interaction for standalone git file
    if st.button("Explore Momentum Progression 📈", use_container_width=True):
        st.toast("💡 *In the final combined application, this button will instantly activate the Momentum Line Chart tab!*")

# --- COLUMN 2: RADAR CHART TEASER ---
with col2:
    st.markdown("#### 2. Tactical Profiles & Style")
    st.write(
        """
        A radar footprint mapping the distinct technical identities of Sinner and Alcaraz across 
        **seven core performance dimensions** (Serve, Returns, Baseline rallies, and Groundstrokes). 
        Evaluated on a pure 0-100% scale to isolate strategic strengths and playstyle choices.
        """
    )
    if st.button("Compare Playing Styles 🕸️", use_container_width=True):
        st.toast("💡 *In the final combined application, this button will instantly activate the Radar Chart tab!*")

# --- COLUMN 3: COURT CHART TEASER ---
with col3:
    st.markdown("#### 3. Spatial Patterns & Placement")
    st.write(
        """
        A geographical deep-dive into shot metrics. This chart maps the raw physical coordinates 
        of the ball, focusing on **serve placement and landing distributions** across the Deuce and Ad courts, 
        revealing the hidden structural patterns behind aces and lost points.
        """
    )
    if st.button("Analyze Shot Placement 🎯", use_container_width=True):
        st.toast("💡 *In the final combined application, this button will instantly activate the Court Chart tab!*")