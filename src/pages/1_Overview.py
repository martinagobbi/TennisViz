import streamlit as st

# ==========================================
# 2. HERO HEADER
# ==========================================
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>Roland Garros 2025 Overview</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D; font-size:18px;'>Jannik Sinner vs Carlos Alcaraz</p>", unsafe_allow_html=True)
st.markdown("---")

st.markdown("""
<style>
div.stPageLink a {
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: white ;
    color: #2C3E50 ;
    text-align: center;
    padding: 14px;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 700;
    font-size: 17px;
    margin-top: 10px;
    border: 2px solid #D5DBDB;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: all 0.25s ease;
}

div.stPageLink a:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.12);
    border-color: #2C3E50;
}

/* Box attorno alle metriche */
.metrics-box {
    border: 2px solid #2C3E50;
    border-radius: 15px;
    padding: 20px 10px;
    margin-bottom: 25px;
}

/* Centra testo metric */
[data-testid="stMetric"] {
    text-align: center;
}

/* Centra label e value */
[data-testid="stMetricLabel"] {
    justify-content: center;
}

[data-testid="stMetricValue"] {
    justify-content: center;
}

/* Custom metric cards */
.metric-card {
    border: 2px solid #D5DBDB;
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    height: 130px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.metric-label {
    color: #7F8C8D;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
}

.metric-value {
    color: #2C3E50;
    font-size: 24px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. QUICK MATCH STATS (KPI BOXES)
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Match Date</div>
        <div class="metric-value">June 8, 2025</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Champion</div>
        <div class="metric-value">Carlos Alcaraz 🇪🇸</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Final Score</div>
        <div class="metric-value">4-6, 6-7, 6-4, 7-6, 7-6</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown("### Match Context")
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
st.markdown("### Explore the Dashboard Visualizations")
st.write("This platform is divided into three analytical layers. Read the briefs below to choose your starting point:")

# FIRST ROW: Just the Text descriptions (forces equal spacing)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Momentum Progression")
    st.write(
        """
        A timeline view of how the match evolved point by point. It tracks momentum shifts and score changes, 
        showing who had control at different stages of the match.
        """
    )

with col2:
    st.markdown("#### Playing Style Comparison")
    st.write(
        """
        A comparison of Sinner and Alcaraz across seven key performance areas (serve, return, baseline play, 
        and groundstrokes). Values are shown on a 0–100 scale to highlight differences in playing style and strengths.
        """
    )

with col3:
    st.markdown("####  Serve Placement")
    st.write(
        """
        A spatial view of shot locations on court. It focuses on serve placement and landing 
        patterns in both the Deuce and Ad courts, helping reveal where points are won or lost.
        """
    )

btn1, btn2, btn3 = st.columns(3)

with btn1:
    st.page_link("pages/2_Line_Chart.py", label="Explore the Line Chart", use_container_width=True)

with btn2:
    st.page_link("pages/3_Radar_Chart.py", label="Explore the Radar Chart", use_container_width=True)

with btn3:
    st.page_link("pages/4_Court_Chart.py", label="Explore the Court Chart", use_container_width=True)