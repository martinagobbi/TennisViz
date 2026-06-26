import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
# st.set_page_config(page_title="RG25 - Match Overview", layout="wide")

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

st.markdown("### 📝 Match Context")
st.write(
    """
    Welcome to the interactive dashboard for analyzing the 2025 Roland Garros Men's Singles Final.

    On June 8, 2025, Carlos Alcaraz and Jannik Sinner played a tight five-set match that ended with a hard-fought 
    win for the Spaniard. With an almost even split in total points won, this match offers a clear case to explore 
    high-level tennis.

    This dashboard goes beyond standard match statistics. Using shot-by-shot data from the Match Charting Project, 
    it lets you explore key phases of the match, tactical changes, and the patterns that helped shape the final result.
    """
)

st.markdown("---")

# ==========================================
# 4. THE VISUALIZATIONS (3-COLUMN TEASER GRID)
# ==========================================
st.markdown("### 📊 Explore the Dashboard Visualizations")
st.write("This platform is divided into three analytical layers. Read the briefs below to choose your starting point:")

col1, col2, col3 = st.columns(3)

# --- COLUMN 1: LINE CHART ---
with col1:
    st.markdown("#### 1. Win Probability & Momentum")
    st.write(
        """
        A timeline view of how the match evolved point by point. It tracks momentum shifts and score changes, 
        showing who had control at different stages of the match.
        """
    )
    st.page_link("pages/2_Line_Chart.py", label="Explore Momentum Progression 📈",
                 use_container_width=True)

# --- COLUMN 2: RADAR CHART ---
with col2:
    st.markdown("#### 2. Tactical Profiles & Style")
    st.write(
        """
        A comparison of Sinner and Alcaraz across seven key performance areas (serve, return, baseline play, 
        and groundstrokes). Values are shown on a 0–100 scale to highlight differences in playing style and strengths..
        """
    )
    st.page_link("pages/3_Radar_Chart.py", label="Compare Playing Styles 🕸️",
                 use_container_width=True)

# --- COLUMN 3: COURT CHART TEASER ---
with col3:
    st.markdown("#### 3. Spatial Patterns & Placement")
    st.write(
        """
        A spatial view of shot locations on court. It focuses on serve placement and landing 
        patterns in both the Deuce and Ad courts, helping reveal where points are won or lost.
        """
    )
    st.page_link("pages/4_Court_Chart.py", label="Analyze Shot Placement 🎯",
                 use_container_width=True)